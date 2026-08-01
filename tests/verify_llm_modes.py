"""LLM 이중 모드(로컬/외부) 실동작 검증 — FR-LLM-01~06, FR-UI-07~08, NFR-SEC-01/06.

Ollama·외부 API·Qdrant 없이도 돌아간다.
  - 목(mock) Ollama / OpenAI 호환 서버를 띄워 HTTP 스트리밍 경로를 그대로 태운다.
  - 임베딩·벡터DB는 모드 분기와 무관하므로 retrieval을 스텁으로 대체한다.

실행:
    python -m tests.verify_llm_modes      (또는) python tests/verify_llm_modes.py
"""
import importlib
import json
import os
import sys
import types

# Windows 콘솔 기본 인코딩(cp949)에서는 ✅ 같은 문자를 출력할 수 없어
# UnicodeEncodeError가 난다. 출력 스트림을 UTF-8로 맞춘다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 프록시가 로컬 목 서버 호출을 가로채지 않도록
os.environ["no_proxy"] = "127.0.0.1,localhost"
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import mock_llm_servers as mocks  # noqa: E402

OLLAMA_URL = f"http://127.0.0.1:{mocks.OLLAMA_PORT}"
OPENAI_URL = f"http://127.0.0.1:{mocks.OPENAI_PORT}/v1"

# 앱 임포트 전에 환경변수 확정 (config가 임포트 시점에 읽는다)
os.environ["OLLAMA_BASE_URL"] = OLLAMA_URL
os.environ["OLLAMA_MODEL"] = "qwen2.5:7b"
os.environ["EXTERNAL_BASE_URL"] = OPENAI_URL
os.environ["EXTERNAL_API_KEY"] = "sk-test-valid"
os.environ["EXTERNAL_MODEL"] = "gpt-4o-mini"
os.environ["LLM_MODE"] = "local"

# retrieval 스텁 (벡터DB/임베딩 없이 모드 경로만 검증)
CONTEXT = "[출처 1] 사내 연차 규정: 연차는 입사일 기준 15일이다."
_stub = types.ModuleType("app.retrieval")
_stub.retrieve = lambda q, k=4: (
    CONTEXT,
    [{"index": 1, "source": "규정.pdf", "location": "p.3", "snippet": "연차 15일"}],
)
sys.modules["app.retrieval"] = _stub

from fastapi.testclient import TestClient  # noqa: E402
from app import config, models_util  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'✅' if cond else '❌'} {name}" + (f"\n       → {detail}" if detail else ""))


def sse_events(mode=None, message="연차가 며칠인가요?", model=None, session="t1"):
    """/api/chat/stream 을 호출해 SSE 이벤트를 순서대로 수집."""
    payload = {"message": message, "session_id": session}
    if mode:
        payload["mode"] = mode
    if model:
        payload["model"] = model
    evs = []
    with client.stream("POST", "/api/chat/stream", json=payload) as r:
        for line in r.iter_lines():
            line = line.strip()
            if line.startswith("data: "):
                evs.append(json.loads(line[6:]))
    return evs


print("\n▶ 목 서버 기동")
mocks.start_background()
print(f"  Ollama 목      : {OLLAMA_URL}")
print(f"  OpenAI 호환 목 : {OPENAI_URL}")

# ───────────────────────────── 1. 모델 목록 · 상태
print("\n▶ [1] 모드별 모델 목록 · 상태 (FR-LLM-05)")
d = client.get("/api/models").json()
check("외부 설정됨 → external_configured=True", d["external_configured"] is True)
check("기본 모드 = local (안전 기본값)", d["default_mode"] == "local", f"default_mode={d['default_mode']}")
check("로컬 모델 목록 = Ollama /api/tags 조회 결과",
      d["local"]["models"] == ["qwen2.5:7b", "llama3.1:8b"], str(d["local"]["models"]))
check("외부 모델 목록 = OpenAI 호환 /models 조회 결과",
      d["external"]["models"] == ["gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"], str(d["external"]["models"]))
check("하위호환 필드(models/default) 유지", "models" in d and "default" in d)

s = client.get("/api/status").json()
check("/api/status 에 mode·external_configured 노출",
      s["mode"] == "local" and s["external_configured"] is True, str(s))

# ───────────────────────────── 2. 로컬 모드
print("\n▶ [2] 로컬 모드 스트리밍 (회귀 없음 확인)")
mocks.LAST["ollama"] = mocks.LAST["openai"] = None
evs = sse_events(mode="local")
types_ = [e["type"] for e in evs]
tokens = "".join(e["text"] for e in evs if e["type"] == "token")
check("sources 이벤트가 가장 먼저", types_[0] == "sources", str(types_[:3]))
check("token 스트리밍 수신", tokens == "로컬 모델 응답입니다.", repr(tokens))
check("done 이벤트로 종료", types_[-1] == "done", str(types_[-2:]))
check("done.answer == 누적 답변", evs[-1]["answer"] == tokens)
check("로컬 모드 → Ollama 호출됨", mocks.LAST["ollama"] is not None)
check("★ 로컬 모드 → 외부 API 호출 전혀 없음 (NFR-SEC-01)", mocks.LAST["openai"] is None)

# ───────────────────────────── 3. 외부 모드
print("\n▶ [3] 외부 모드 스트리밍 (FR-LLM-01)")
mocks.LAST["ollama"] = mocks.LAST["openai"] = None
evs = sse_events(mode="external")
tokens = "".join(e["text"] for e in evs if e["type"] == "token")
check("외부 API 토큰 스트리밍 수신", tokens == "외부 API 응답입니다.", repr(tokens))
check("외부 모드 → 외부 API 호출됨", mocks.LAST["openai"] is not None)
check("외부 모드 → Ollama 호출 안 함", mocks.LAST["ollama"] is None)
sent = json.dumps(mocks.LAST["openai"], ensure_ascii=False)
check("외부 요청에 기본 모델(gpt-4o-mini) 사용", mocks.LAST["openai"]["model"] == "gpt-4o-mini")
check("★ 외부 전송 내용에 질문 포함 (UI 경고가 사실임을 확인)", "연차가 며칠인가요?" in sent)
check("★ 외부 전송 내용에 문서 컨텍스트 포함 (UI 경고가 사실임을 확인)", "연차는 입사일 기준 15일" in sent)
check("stream=True 로 요청", mocks.LAST["openai"].get("stream") is True)

# ───────────────────────────── 4. 모델 지정 · 기본 모드
print("\n▶ [4] 모델 지정 · 서버 기본 모드 (FR-LLM-02)")
mocks.LAST["openai"] = None
sse_events(mode="external", model="gpt-4o")
check("요청한 모델명이 외부 API로 전달됨", mocks.LAST["openai"]["model"] == "gpt-4o")

mocks.LAST["ollama"] = mocks.LAST["openai"] = None
sse_events(mode=None)  # mode 미지정 → 서버 기본값(local)
check("mode 미지정 → 서버 기본값(local) 사용",
      mocks.LAST["ollama"] is not None and mocks.LAST["openai"] is None)

# ───────────────────────────── 5. 오류 처리
print("\n▶ [5] 외부 모드 오류 처리")
os.environ["EXTERNAL_API_KEY"] = "sk-bad"
importlib.reload(config)
err = [e for e in sse_events(mode="external") if e["type"] == "error"]
check("잘못된 키 → error 이벤트 반환(서버 크래시 없음)", len(err) == 1, str(err[:1])[:160])

os.environ["EXTERNAL_BASE_URL"] = "http://127.0.0.1:9/v1"  # 연결 실패
os.environ["EXTERNAL_API_KEY"] = "sk-test-valid"
importlib.reload(config)
err = [e for e in sse_events(mode="external") if e["type"] == "error"]
check("잘못된 base_url(연결실패) → error 이벤트 반환", len(err) == 1, str(err[:1])[:160])
check("연결 실패 시에도 모델목록은 기본값 폴백",
      models_util.list_external_models() == ["gpt-4o-mini"])

os.environ["EXTERNAL_API_KEY"] = ""  # 미설정
os.environ["EXTERNAL_BASE_URL"] = OPENAI_URL
importlib.reload(config)
mocks.LAST["openai"] = None
check("키 미설정 → external_configured=False", config.external_configured() is False)
d = client.get("/api/models").json()
check("키 미설정 → /api/models 의 외부 목록 비어있음 (UI 비활성화 근거)",
      d["external"]["models"] == [] and d["external_configured"] is False)
err = [e for e in sse_events(mode="external") if e["type"] == "error"]
check("키 미설정 상태로 외부 요청 → 안내 오류 반환",
      len(err) == 1 and "설정" in err[0]["message"], str(err[:1])[:160])
check("★ 키 미설정 시 외부로 아무것도 전송되지 않음", mocks.LAST["openai"] is None)

# ───────────────────────────── 6. OpenAI 호환 서버
print("\n▶ [6] OpenAI 외 호환 서버 호환성 (FR-LLM-04)")
os.environ["EXTERNAL_API_KEY"] = "sk-test-valid"
os.environ["EXTERNAL_BASE_URL"] = OPENAI_URL + "/"  # 끝 슬래시 처리 확인
os.environ["EXTERNAL_MODEL"] = "gpt-4.1-mini"
importlib.reload(config)
check("base_url 끝 슬래시여도 모델목록 조회 성공",
      models_util.list_external_models() == ["gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"])
mocks.LAST["openai"] = None
tokens = "".join(e["text"] for e in sse_events(mode="external") if e["type"] == "token")
check("★ 자체 호스팅 OpenAI 호환 엔드포인트로 정상 스트리밍 (vLLM 등 대체 가능)",
      tokens == "외부 API 응답입니다.", repr(tokens))
check("변경한 기본 모델(gpt-4.1-mini) 적용", mocks.LAST["openai"]["model"] == "gpt-4.1-mini")

# ───────────────────────────── 7. 대화기억
print("\n▶ [7] 대화기억 · 세션")
client.post("/api/chat/reset", json={"session_id": "t2"})
mocks.LAST["openai"] = None
sse_events(mode="external", message="첫 질문", session="t2")
sse_events(mode="external", message="두번째 질문", session="t2")
sent = json.dumps(mocks.LAST["openai"], ensure_ascii=False)
check("이전 턴이 다음 요청에 포함됨 (FR-CHAT-06 회귀 없음)", "첫 질문" in sent)

# ───────────────────────────── 결과
print("\n" + "=" * 62)
print(f"  통과 {len(PASS)} / 실패 {len(FAIL)}")
for f in FAIL:
    print(f"   - {f}")
print("=" * 62)
sys.exit(1 if FAIL else 0)
