"""데모(Streamlit) 구성 검증 — fastembed 임베딩 + 메모리 Qdrant + 외부 LLM.

Docker·Ollama·외부 API 없이 데모 경로 전체(문서로드 → 청킹 → 임베딩 → 색인 →
검색 → 외부 LLM 스트리밍)를 검증한다.

임베딩은 실제 fastembed를 우선 시도하고, 모델을 내려받을 수 없는 환경
(폐쇄망·CI)에서는 **결정적 스텁 임베딩**으로 자동 대체한다. 스텁으로 돌더라도
색인·검색·스트리밍 배선은 동일하게 검증되지만, 임베딩 품질은 검증 대상이 아니다.

실행: python tests/verify_demo_rag.py
"""
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

os.environ["no_proxy"] = "127.0.0.1,localhost"
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import mock_llm_servers as mocks  # noqa: E402

# ── 데모 환경 (앱 임포트 전에 확정)
os.environ["EMBEDDING_BACKEND"] = "fastembed"
os.environ["QDRANT_MODE"] = "memory"
os.environ["QDRANT_COLLECTION"] = "demo_documents"
os.environ["LLM_MODE"] = "external"
os.environ["EXTERNAL_BASE_URL"] = f"http://127.0.0.1:{mocks.OPENAI_PORT}/v1"
os.environ["EXTERNAL_API_KEY"] = "sk-test-valid"
os.environ["EXTERNAL_MODEL"] = "gpt-4o-mini"

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'✅' if cond else '❌'} {name}" + (f"\n       → {detail}" if detail else ""))


# ─────────────────────────── 임베딩: 실제 fastembed 우선, 실패 시 스텁
def install_stub_fastembed():
    """모델 다운로드가 불가능한 환경용 결정적 해싱 임베딩.

    문자 3-gram을 해싱해 고정 차원 벡터로 만든다. 같은 단어를 공유하는
    질문/문서가 가까워지므로 검색 배선을 검증하기에 충분하다.
    """
    import numpy as np

    dim = int(os.environ.get("FASTEMBED_DIM", "384"))

    def vec(text):
        v = np.zeros(dim, dtype=np.float32)
        t = text.lower()
        for i in range(max(len(t) - 2, 1)):
            g = t[i:i + 3]
            v[hash(g) % dim] += 1.0
        n = np.linalg.norm(v)
        return v / n if n else v

    class StubTextEmbedding:
        def __init__(self, model_name=None, cache_dir=None):
            self.model_name = model_name

        def embed(self, texts):
            for t in texts:
                yield vec(t)

    mod = types.ModuleType("fastembed")
    mod.TextEmbedding = StubTextEmbedding
    sys.modules["fastembed"] = mod


def embedding_mode():
    os.environ.setdefault("PYTHONHASHSEED", "0")
    try:
        from fastembed import TextEmbedding
        TextEmbedding(model_name=os.environ.get(
            "FASTEMBED_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"))
        return "real"
    except Exception as e:
        install_stub_fastembed()
        return f"stub ({type(e).__name__})"


print("\n▶ 준비")
mocks.start_background()
print(f"  OpenAI 호환 목 : http://127.0.0.1:{mocks.OPENAI_PORT}/v1")
mode = embedding_mode()
print(f"  임베딩 백엔드  : {mode}")
if mode.startswith("stub"):
    print("  ⚠ fastembed 모델을 내려받을 수 없어 스텁으로 검증합니다"
          " (배선 검증만, 임베딩 품질은 검증 대상 아님)")

from app import config  # noqa: E402
from app.chat_engine import clear_history, stream_answer  # noqa: E402
from app.embeddings import embedding_dim  # noqa: E402
from app.ingest import _splitter  # noqa: E402
from app.loaders import load_directory  # noqa: E402
from app.retrieval import retrieve  # noqa: E402
from app.vectorstore import get_client, get_vectorstore  # noqa: E402

# ─────────────────────────── 1. 설정
print("\n▶ [1] 데모 설정")
check("임베딩 백엔드 = fastembed", config.EMBEDDING_BACKEND == "fastembed")
check("벡터 차원 = 384 (bge-m3의 1024와 다름)", embedding_dim() == 384, str(embedding_dim()))
check("Qdrant = 메모리 모드 (Docker 불필요)", config.QDRANT_MODE == "memory")
check("LLM = 외부 모드", config.LLM_MODE == "external")

# ─────────────────────────── 2. 색인
print("\n▶ [2] 샘플 문서 색인")
docs = load_directory(config.DEMO_DOCS_DIR)
names = sorted({d.metadata.get("source") for d in docs})
check("샘플 문서 로드됨", len(docs) > 0, f"{len(names)}개 파일: {names}")
chunks = _splitter().split_documents(docs)
check("청킹 완료", len(chunks) > 0, f"{len(chunks)}개 청크")
get_vectorstore().add_documents(chunks)
cnt = get_client().count(collection_name=config.QDRANT_COLLECTION).count
check("메모리 Qdrant에 적재됨", cnt == len(chunks), f"{cnt}개 포인트")

# ─────────────────────────── 3. 검색
print("\n▶ [3] 검색 (출처 메타데이터)")
ctx, srcs = retrieve("연차 휴가는 며칠인가요?")
check("검색 결과 반환", len(srcs) > 0, f"{len(srcs)}건")
check("출처에 파일명 포함", all(s.get("source") for s in srcs),
      ", ".join(s["source"] for s in srcs))
check("컨텍스트 문자열 생성", "[출처 1" in ctx)
if mode == "real":
    check("연차 질문 → 인사규정 문서가 검색됨",
          any("연차" in s["source"] for s in srcs),
          ", ".join(s["source"] for s in srcs))

# ─────────────────────────── 4. 외부 LLM 스트리밍
print("\n▶ [4] 외부 LLM 스트리밍 (데모 경로)")
mocks.LAST["openai"] = None
clear_history("demo")
evs = list(stream_answer("demo", "연차는 며칠인가요?", "gpt-4o-mini", "external"))
tokens = "".join(e["text"] for e in evs if e["type"] == "token")
kinds = [e["type"] for e in evs]
check("sources 이벤트 먼저", kinds[0] == "sources")
check("토큰 스트리밍 수신", tokens == "외부 API 응답입니다.", repr(tokens))
check("done 이벤트로 종료", kinds[-1] == "done")
check("외부 API 실제 호출됨", mocks.LAST["openai"] is not None)
import json  # noqa: E402
sent = json.dumps(mocks.LAST["openai"], ensure_ascii=False)
check("전송 내용에 질문 포함", "연차는 며칠인가요?" in sent)
check("전송 내용에 검색된 문서 컨텍스트 포함", "출처" in sent)

# ─────────────────────────── 5. 온프레미스 설정 무영향
print("\n▶ [5] 코드 기본값 회귀 확인 (설정이 없으면 온프레미스 구성)")
import importlib  # noqa: E402

import dotenv  # noqa: E402

# config는 임포트 시 load_dotenv()로 .env를 읽는다. 여기서 확인하려는 것은
# "사용자의 로컬 설정"이 아니라 "코드에 박힌 기본값"이므로, .env 로딩을 잠시 끄고
# 관련 환경변수를 비운 상태로 재적재한다. (이 격리가 없으면 .env를 둔 개발자
#  PC에서만 실패하는 검사가 된다)
_real_load_dotenv = dotenv.load_dotenv
dotenv.load_dotenv = lambda *a, **k: False
_saved = {k: os.environ.pop(k, None)
          for k in ("EMBEDDING_BACKEND", "QDRANT_MODE", "LLM_MODE")}
try:
    importlib.reload(config)
    check("설정 없으면 임베딩 = bge-m3 (온프레미스 기본)",
          config.EMBEDDING_BACKEND == "bge-m3", config.EMBEDDING_BACKEND)
    check("설정 없으면 Qdrant = server (Docker)",
          config.QDRANT_MODE == "server", config.QDRANT_MODE)
    check("설정 없으면 LLM = local", config.LLM_MODE == "local", config.LLM_MODE)
    check("온프레미스 벡터 차원 = 1024 (bge-m3)", config.EMBEDDING_DIM == 1024)
finally:
    dotenv.load_dotenv = _real_load_dotenv
    for _k, _v in _saved.items():
        if _v is not None:
            os.environ[_k] = _v

# ─────────────────────────── 결과
print("\n" + "=" * 62)
print(f"  통과 {len(PASS)} / 실패 {len(FAIL)}   (임베딩: {mode})")
for f in FAIL:
    print(f"   - {f}")
print("=" * 62)
sys.exit(1 if FAIL else 0)
