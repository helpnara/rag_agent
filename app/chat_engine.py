"""스트리밍 채팅 엔진.

구조:
  1) 사용자 질문으로 문서 검색 (retrieval) → 컨텍스트 + 출처 확보
  2) 질문에 수치 예측이 필요하면 커스텀 AI 모델을 호출 (간이 tool calling)
  3) 컨텍스트 + 대화기록을 넣어 LLM에 스트리밍 요청 → 토큰을 그대로 흘려보냄

대화 기억: 세션ID별로 (질문, 답변) 쌍을 메모리에 보관한다.
"""
from typing import Dict, Generator, List

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app import config
from app.retrieval import retrieve
from app.my_model import predict


# 세션별 대화 기록 (프로세스 메모리). 규모가 커지면 Redis 등으로 교체.
_HISTORY: Dict[str, List[Dict]] = {}
MAX_TURNS = 8  # 기억할 최근 대화 턴 수


SYSTEM_PROMPT = """당신은 사내 문서 기반 어시스턴트입니다.
아래 제공된 문서 컨텍스트를 근거로 한국어로 답하세요.
- 답변에 사용한 근거는 [출처 N] 형식으로 표시하세요.
- 컨텍스트에 없는 내용은 지어내지 말고 모른다고 답하세요.
- 필요하면 마크다운(굵게, 목록, 표)으로 읽기 쉽게 구성하세요."""


def _llm(model: str = None) -> ChatOllama:
    return ChatOllama(
        model=model or config.OLLAMA_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=0,
    )


def _build_messages(session_id: str, question: str, context: str):
    """시스템 + 문서컨텍스트 + 최근 대화기록 + 현재 질문으로 메시지 구성."""
    msgs = [SystemMessage(content=SYSTEM_PROMPT)]

    # 최근 대화 기록 주입 (기억)
    history = _HISTORY.get(session_id, [])[-MAX_TURNS:]
    for turn in history:
        msgs.append(HumanMessage(content=turn["q"]))
        msgs.append(AIMessage(content=turn["a"]))

    # 현재 질문 + 검색된 문서 컨텍스트
    if context:
        user_content = f"[문서 컨텍스트]\n{context}\n\n[질문]\n{question}"
    else:
        user_content = f"(관련 문서를 찾지 못했습니다.)\n\n[질문]\n{question}"
    msgs.append(HumanMessage(content=user_content))
    return msgs


def save_turn(session_id: str, question: str, answer: str) -> None:
    _HISTORY.setdefault(session_id, []).append({"q": question, "a": answer})


def clear_history(session_id: str) -> None:
    _HISTORY.pop(session_id, None)


def stream_answer(session_id: str, question: str, model: str = None) -> Generator[dict, None, None]:
    """SSE로 흘려보낼 이벤트를 생성한다.

    yield 되는 dict의 형태:
      {"type": "sources", "sources": [...]}   # 먼저 출처를 보냄
      {"type": "token", "text": "..."}         # 답변 토큰들
      {"type": "done", "answer": "전체답변"}   # 종료 + 전체 답변
    """
    # 1) 문서 검색
    context, sources = retrieve(question)
    yield {"type": "sources", "sources": sources}

    # 2) 커스텀 모델이 필요한 질문인지 간이 판단
    #    (예: "예측" "계산" 등 키워드 + 숫자가 있으면 모델 호출)
    model_note = ""
    import re
    if any(k in question for k in ["예측", "계산", "추정"]):
        nums = re.findall(r"-?\d+\.?\d*", question)
        if nums:
            r = predict(float(nums[0]))
            model_note = f"\n\n[모델 예측 결과] 입력 {r['input']} → 예측값 {r['prediction']}"

    # 3) LLM 스트리밍
    msgs = _build_messages(session_id, question, context)
    full = []
    for chunk in _llm(model).stream(msgs):
        token = chunk.content or ""
        if token:
            full.append(token)
            yield {"type": "token", "text": token}

    answer = "".join(full) + model_note
    if model_note:
        yield {"type": "token", "text": model_note}

    save_turn(session_id, question, answer)
    yield {"type": "done", "answer": answer}
