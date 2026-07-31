"""사내 문서 RAG 에이전트 — 공개 데모 (Streamlit Cloud).

이 파일은 **데모/포트폴리오 전용 진입점**이다. 실제 사내 운영은 FastAPI 버전
(`app/main.py`)을 폐쇄망에서 구동한다.

데모가 온프레미스와 다른 점 (Streamlit Cloud 리소스 제약 때문):
  - 임베딩 : bge-m3(2GB) → fastembed 경량 모델(ONNX, torch 불필요). 둘 다 로컬 실행.
  - 벡터DB : Qdrant Docker → qdrant-client 메모리 모드 (앱 재시작 시 재색인)
  - LLM    : Ollama 로컬 → 외부 OpenAI 호환 API (Cloud에서 로컬 LLM 구동 불가)

⚠️ 데모는 외부 LLM API를 쓰므로 입력한 질문과 문서 내용이 외부로 전송된다.
   공개된 샘플 문서로만 시연하며, 실제 사내 문서를 올리지 않는다.
"""
import os
import re
import uuid

import streamlit as st

# ── 앱 모듈 임포트 전에 데모용 환경 확정 (config가 임포트 시점에 읽는다)
os.environ.setdefault("EMBEDDING_BACKEND", "fastembed")
os.environ.setdefault("QDRANT_MODE", "memory")
os.environ.setdefault("QDRANT_COLLECTION", "demo_documents")
os.environ.setdefault("LLM_MODE", "external")

from app import config  # noqa: E402
from app.chat_engine import clear_history, stream_answer  # noqa: E402

st.set_page_config(page_title="사내 문서 RAG 에이전트 데모", page_icon="📄", layout="wide")

SAMPLE_QUESTIONS = [
    "연차는 며칠이고 언제까지 써야 해?",
    "대외비 문서를 생성형 AI에 넣어도 되나요?",
    "야근 식대 한도가 얼마인가요?",
]


# ────────────────────────────────────────────────── 색인 (앱당 1회)
@st.cache_resource(show_spinner=False)
def build_index():
    """샘플 문서를 메모리 벡터DB에 색인한다. 실패해도 앱은 계속 뜨게 한다."""
    from app.ingest import _splitter
    from app.loaders import load_directory
    from app.vectorstore import get_vectorstore

    docs = load_directory(config.DEMO_DOCS_DIR)
    chunks = _splitter().split_documents(docs)
    if not chunks:
        return {"ok": False, "files": 0, "chunks": 0, "reason": "샘플 문서를 찾지 못했습니다."}
    get_vectorstore().add_documents(chunks)
    names = sorted({d.metadata.get("source", "?") for d in docs})
    return {"ok": True, "files": len(names), "chunks": len(chunks), "names": names}


def operator_key() -> str:
    """운영자 키(있으면 체험용으로 제한 사용).

    secrets 파일이 없을 때 st.secrets에 접근하면 Streamlit이 화면에 오류를
    표시하므로, 파일이 있을 때만 조회하고 없으면 환경변수로 폴백한다.
    """
    from pathlib import Path

    candidates = [
        Path.home() / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / "secrets.toml",
    ]
    if any(p.exists() for p in candidates):
        try:
            return st.secrets.get("EXTERNAL_API_KEY", "") or ""
        except Exception:
            pass
    return os.getenv("EXTERNAL_API_KEY", "")


def render_sources(sources) -> None:
    """출처 카드. 스니펫의 마크다운이 본문처럼 렌더링되지 않도록 한 줄로 접는다."""
    with st.expander(f"참고한 문서 {len(sources)}건"):
        for s in sources:
            loc = f" · {s['location']}" if s.get("location") else ""
            st.markdown(f"**[{s['index']}] {s['source']}**{loc}")
            # 줄바꿈을 없애 표·제목이 블록으로 렌더링되지 않게 하고,
            # 맨 앞에 남은 마크다운 기호(#, >, - 등)도 제거한다.
            snippet = re.sub(r"^[#>*\-\s]+", "", " ".join((s.get("snippet") or "").split()))
            st.caption(snippet[:300] + ("…" if len(snippet) > 300 else ""))


# ────────────────────────────────────────────────── 세션 상태
if "sid" not in st.session_state:
    st.session_state.sid = "st_" + uuid.uuid4().hex[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "demo_used" not in st.session_state:
    st.session_state.demo_used = 0

# ────────────────────────────────────────────────── 사이드바
with st.sidebar:
    st.title("📄 문서 RAG 데모")
    st.caption("사내 문서 기반 질의응답 에이전트의 공개 데모입니다.")

    st.warning(
        "**외부 API 데모** — 질문과 검색된 문서 내용이 외부 LLM 서버로 전송됩니다. "
        "공개용 샘플 문서로만 시연하세요.",
        icon="⚠️",
    )

    st.subheader("API 키")
    user_key = st.text_input(
        "OpenAI 호환 API 키",
        type="password",
        placeholder="sk-...",
        help="입력한 키는 브라우저 세션에만 유지되며 저장되지 않습니다.",
    )
    op_key = operator_key()
    remaining = max(0, config.DEMO_QUESTION_LIMIT - st.session_state.demo_used)

    if user_key:
        active_key, using_own = user_key, True
        st.success("입력한 키를 사용합니다. (제한 없음)")
    elif op_key:
        active_key, using_own = op_key, False
        st.info(f"체험 모드 — 남은 질문 **{remaining}회**\n\n계속 쓰려면 본인 키를 입력하세요.")
    else:
        active_key, using_own = "", False
        st.error("사용 가능한 키가 없습니다. 본인의 API 키를 입력하세요.")

    base_url = st.text_input(
        "API base URL", value=config.EXTERNAL_BASE_URL,
        help="OpenAI 외 vLLM·OpenRouter 등 OpenAI 호환 서버도 사용할 수 있습니다.")
    model = st.text_input("모델", value=config.EXTERNAL_MODEL)

    st.divider()
    st.subheader("샘플 문서")
    info = build_index()
    if info.get("ok"):
        for n in info["names"]:
            st.markdown(f"- {n}")
        st.caption(f"{info['files']}개 문서 · {info['chunks']}개 청크 색인됨")
    else:
        st.error(info.get("reason", "색인 실패"))

    st.divider()
    if st.button("새 대화", use_container_width=True):
        clear_history(st.session_state.sid)
        st.session_state.messages = []
        st.rerun()

    st.caption(
        "온프레미스 버전은 임베딩·LLM·벡터DB를 모두 사내에서 구동해 "
        "문서가 외부로 나가지 않습니다."
    )

# ────────────────────────────────────────────────── 본문
st.markdown("### 무엇을 찾아드릴까요?")
st.caption("샘플 사내 문서(인사규정·정보보안·경비처리)를 근거로 답변하고 출처를 표시합니다.")

if not st.session_state.messages:
    cols = st.columns(len(SAMPLE_QUESTIONS))
    for c, q in zip(cols, SAMPLE_QUESTIONS):
        if c.button(q, use_container_width=True):
            st.session_state.pending = q
            st.rerun()

# 지난 대화 렌더링
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            render_sources(m["sources"])

prompt = st.chat_input("문서에 대해 질문하기…") or st.session_state.pop("pending", None)

if prompt:
    if not active_key:
        st.error("API 키를 입력해야 질문할 수 있습니다.")
        st.stop()
    if not using_own and remaining <= 0:
        st.error(
            f"체험용 질문 {config.DEMO_QUESTION_LIMIT}회를 모두 사용했습니다. "
            "사이드바에 본인의 API 키를 입력하면 계속 사용할 수 있습니다."
        )
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 이번 요청에만 적용할 외부 API 설정
    config.EXTERNAL_API_KEY = active_key
    config.EXTERNAL_BASE_URL = base_url

    collected = {"sources": [], "error": None}

    def token_stream():
        for ev in stream_answer(st.session_state.sid, prompt, model, "external"):
            if ev["type"] == "sources":
                collected["sources"] = ev["sources"]
            elif ev["type"] == "token":
                yield ev["text"]
            elif ev["type"] == "error":
                collected["error"] = ev["message"]

    with st.chat_message("assistant"):
        answer = st.write_stream(token_stream())
        if collected["error"]:
            st.error(f"오류: {collected['error']}")
            answer = answer or ""
        elif collected["sources"]:
            render_sources(collected["sources"])

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": collected["sources"]})
    if not using_own:
        st.session_state.demo_used += 1
        st.rerun()
