"""RAG + Tool Calling 에이전트 (완전 로컬 LLM: Ollama).

두 개의 도구를 로컬 LLM에게 등록:
  1) search_documents : Qdrant에서 관련 문서를 검색 (RAG)
  2) run_my_model     : 사용자의 커스텀 AI 모델에 입력값을 넣어 결과를 받음
어떤 텍스트도 외부로 나가지 않는다 (임베딩·LLM 모두 로컬).
"""
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app import config
from app.vectorstore import get_vectorstore
from app.my_model import predict


# ---- 도구 1: 문서 검색 (RAG) ----
@tool
def search_documents(query: str) -> str:
    """폴더에 적재된 사내 문서(PDF, 엑셀, PPT, 텍스트)에서
    질문과 관련된 내용을 검색한다. 문서 근거가 필요할 때 사용한다."""
    vs = get_vectorstore()
    results = vs.similarity_search(query, k=config.TOP_K)
    if not results:
        return "관련 문서를 찾지 못했습니다."
    blocks = []
    for d in results:
        src = d.metadata.get("source", "?")
        loc = d.metadata.get("page") or d.metadata.get("slide") or d.metadata.get("sheet") or ""
        header = f"[{src} {loc}]".strip()
        blocks.append(f"{header}\n{d.page_content}")
    return "\n\n---\n\n".join(blocks)


# ---- 도구 2: 커스텀 AI 모델 ----
@tool
def run_my_model(input_value: float) -> dict:
    """사용자가 만든 예측 모델에 숫자 입력값을 전달하고
    예측 결과를 반환한다. 수치 예측이 필요할 때 사용한다."""
    return predict(input_value)


TOOLS = [search_documents, run_my_model]


SYSTEM = """당신은 사내 문서 기반 어시스턴트입니다.
- 문서 내용이 필요하면 search_documents 도구를 사용하세요.
- 예측/계산이 필요하면 run_my_model 도구를 사용하세요.
- 답변은 한국어로, 사용한 문서의 출처([파일명 위치])를 함께 밝히세요.
- 근거가 없으면 모른다고 솔직히 답하세요."""


def build_agent() -> AgentExecutor:
    # 로컬 LLM. tool calling을 지원하는 모델을 써야 함 (qwen2.5, llama3.1 등)
    llm = ChatOllama(
        model=config.OLLAMA_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=True,
        handle_parsing_errors=True,   # 로컬 모델 출력 흔들림 대비
        max_iterations=5,
    )
