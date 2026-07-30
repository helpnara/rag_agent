"""검증용 목(mock) LLM 서버 — Ollama / OpenAI 호환 API를 흉내낸다.

실제 Ollama나 외부 API 없이 chat_engine의 두 경로(로컬/외부)를
HTTP 스트리밍까지 포함해 그대로 검증하기 위한 테스트 더블.

실행: python mock_llm_servers.py            (두 서버 동시 기동)
  - Ollama 목      : http://127.0.0.1:18434
  - OpenAI 호환 목 : http://127.0.0.1:18000/v1
"""
import json
import threading
import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

OLLAMA_PORT = 18434
OPENAI_PORT = 18000

# 마지막으로 수신한 요청을 보관 → 테스트에서 "무엇이 전송됐는지" 검증
LAST = {"ollama": None, "openai": None}


# ---------------------------------------------------------------- Ollama 목
ollama_app = FastAPI()


@ollama_app.get("/api/tags")
def tags():
    return {"models": [
        {"name": "qwen2.5:7b", "model": "qwen2.5:7b", "size": 4700000000},
        {"name": "llama3.1:8b", "model": "llama3.1:8b", "size": 4900000000},
    ]}


@ollama_app.post("/api/chat")
async def ollama_chat(request: Request):
    body = await request.json()
    LAST["ollama"] = body
    pieces = ["로컬", " 모델", " 응답", "입니다."]

    def gen():
        for p in pieces:
            yield json.dumps({
                "model": body.get("model", "qwen2.5:7b"),
                "created_at": "2026-07-18T00:00:00Z",
                "message": {"role": "assistant", "content": p},
                "done": False,
            }) + "\n"
            time.sleep(0.01)
        yield json.dumps({
            "model": body.get("model", "qwen2.5:7b"),
            "created_at": "2026-07-18T00:00:00Z",
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "stop",
            "total_duration": 1000,
            "eval_count": 4,
        }) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


# --------------------------------------------------------- OpenAI 호환 목
openai_app = FastAPI()


def _auth_error(request: Request):
    """키가 없거나 'sk-bad'면 401 — 외부 모드 오류 처리 검증용."""
    auth = request.headers.get("authorization", "")
    key = auth.replace("Bearer ", "").strip()
    if not key or key == "not-needed":
        return JSONResponse({"error": {"message": "Missing API key"}}, status_code=401)
    if key == "sk-bad":
        return JSONResponse({"error": {"message": "Incorrect API key provided"}}, status_code=401)
    return None


@openai_app.get("/v1/models")
def models(request: Request):
    err = _auth_error(request)
    if err:
        return err
    return {"object": "list", "data": [
        {"id": "gpt-4o-mini", "object": "model"},
        {"id": "gpt-4o", "object": "model"},
        {"id": "gpt-4.1-mini", "object": "model"},
    ]}


@openai_app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    err = _auth_error(request)
    if err:
        return err
    body = await request.json()
    LAST["openai"] = body
    model = body.get("model", "gpt-4o-mini")
    pieces = ["외부", " API", " 응답", "입니다."]

    def sse():
        head = {"id": "chatcmpl-1", "object": "chat.completion.chunk", "created": 1,
                "model": model,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]}
        yield f"data: {json.dumps(head)}\n\n"
        for p in pieces:
            chunk = {"id": "chatcmpl-1", "object": "chat.completion.chunk", "created": 1,
                     "model": model,
                     "choices": [{"index": 0, "delta": {"content": p}, "finish_reason": None}]}
            yield f"data: {json.dumps(chunk)}\n\n"
            time.sleep(0.01)
        tail = {"id": "chatcmpl-1", "object": "chat.completion.chunk", "created": 1,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        yield f"data: {json.dumps(tail)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@openai_app.get("/_debug/last")
def debug_last():
    return LAST


# ------------------------------------------------------------------- 기동
def serve(app, port):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def start_background():
    """데몬 스레드로 두 목 서버를 띄우고, 준비될 때까지 대기."""
    for app, port in ((ollama_app, OLLAMA_PORT), (openai_app, OPENAI_PORT)):
        threading.Thread(target=serve, args=(app, port), daemon=True).start()

    import urllib.request
    for port, path in ((OLLAMA_PORT, "/api/tags"), (OPENAI_PORT, "/v1/models")):
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=1)
                break
            except Exception as e:
                # 401(키 없음)도 서버가 살아있다는 뜻
                if getattr(e, "code", None) == 401:
                    break
                time.sleep(0.1)
    return LAST


if __name__ == "__main__":
    start_background()
    print(f"Ollama 목      : http://127.0.0.1:{OLLAMA_PORT}")
    print(f"OpenAI 호환 목 : http://127.0.0.1:{OPENAI_PORT}/v1")
    while True:
        time.sleep(1)
