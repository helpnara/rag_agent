"""검증용 목(mock) LLM 서버 — Ollama / OpenAI 호환 API를 흉내낸다.

실제 Ollama나 외부 API 없이 chat_engine의 두 경로(로컬/외부)를
HTTP 스트리밍까지 포함해 그대로 검증하기 위한 테스트 더블.

표준 라이브러리만 사용한다. 온프레미스 환경(FastAPI)과 데모 환경(Streamlit)
어느 쪽에서도 추가 의존성 없이 동작해야 하기 때문이다.

실행: python tests/mock_llm_servers.py     (두 서버 동시 기동)
  - Ollama 목      : http://127.0.0.1:18434
  - OpenAI 호환 목 : http://127.0.0.1:18000/v1
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OLLAMA_PORT = 18434
OPENAI_PORT = 18000

# 마지막으로 수신한 요청을 보관 → 테스트에서 "무엇이 전송됐는지" 검증
LAST = {"ollama": None, "openai": None}

OLLAMA_PIECES = ["로컬", " 모델", " 응답", "입니다."]
OPENAI_PIECES = ["외부", " API", " 응답", "입니다."]


class _Base(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # 테스트 출력 조용히
        pass

    # ── 응답 헬퍼
    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _start_stream(self, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

    def _chunk(self, text):
        data = text.encode()
        self.wfile.write(f"{len(data):X}\r\n".encode())
        self.wfile.write(data)
        self.wfile.write(b"\r\n")
        self.wfile.flush()

    def _end_stream(self):
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")


class OllamaHandler(_Base):
    def do_GET(self):
        if self.path.startswith("/api/tags"):
            return self._json({"models": [
                {"name": "qwen2.5:7b", "model": "qwen2.5:7b", "size": 4700000000},
                {"name": "llama3.1:8b", "model": "llama3.1:8b", "size": 4900000000},
            ]})
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self.path.startswith("/api/chat"):
            return self._json({"error": "not found"}, 404)
        body = self._body()
        LAST["ollama"] = body
        model = body.get("model", "qwen2.5:7b")
        self._start_stream("application/x-ndjson")
        for p in OLLAMA_PIECES:
            self._chunk(json.dumps({
                "model": model, "created_at": "2026-07-18T00:00:00Z",
                "message": {"role": "assistant", "content": p}, "done": False,
            }) + "\n")
            time.sleep(0.01)
        self._chunk(json.dumps({
            "model": model, "created_at": "2026-07-18T00:00:00Z",
            "message": {"role": "assistant", "content": ""},
            "done": True, "done_reason": "stop", "total_duration": 1000, "eval_count": 4,
        }) + "\n")
        self._end_stream()


class OpenAIHandler(_Base):
    def _auth_failed(self):
        """키가 없거나 'sk-bad'면 401 — 외부 모드 오류 처리 검증용."""
        key = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
        if not key or key == "not-needed":
            self._json({"error": {"message": "Missing API key"}}, 401)
            return True
        if key == "sk-bad":
            self._json({"error": {"message": "Incorrect API key provided"}}, 401)
            return True
        return False

    def do_GET(self):
        if self.path.startswith("/_debug/last"):
            return self._json(LAST)
        if self.path.startswith("/v1/models"):
            if self._auth_failed():
                return
            return self._json({"object": "list", "data": [
                {"id": "gpt-4o-mini", "object": "model"},
                {"id": "gpt-4o", "object": "model"},
                {"id": "gpt-4.1-mini", "object": "model"},
            ]})
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self.path.startswith("/v1/chat/completions"):
            return self._json({"error": "not found"}, 404)
        if self._auth_failed():
            return
        body = self._body()
        LAST["openai"] = body
        model = body.get("model", "gpt-4o-mini")

        def frame(delta, finish=None):
            return "data: " + json.dumps({
                "id": "chatcmpl-1", "object": "chat.completion.chunk", "created": 1,
                "model": model,
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }) + "\n\n"

        self._start_stream("text/event-stream")
        self._chunk(frame({"role": "assistant"}))
        for p in OPENAI_PIECES:
            self._chunk(frame({"content": p}))
            time.sleep(0.01)
        self._chunk(frame({}, "stop"))
        self._chunk("data: [DONE]\n\n")
        self._end_stream()


def start_background():
    """데몬 스레드로 두 목 서버를 띄우고, 준비될 때까지 대기."""
    for handler, port in ((OllamaHandler, OLLAMA_PORT), (OpenAIHandler, OPENAI_PORT)):
        srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()

    import urllib.request
    for port, path in ((OLLAMA_PORT, "/api/tags"), (OPENAI_PORT, "/v1/models")):
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=1)
                break
            except Exception as e:
                if getattr(e, "code", None) == 401:  # 서버는 살아있음
                    break
                time.sleep(0.1)
    return LAST


if __name__ == "__main__":
    start_background()
    print(f"Ollama 목      : http://127.0.0.1:{OLLAMA_PORT}")
    print(f"OpenAI 호환 목 : http://127.0.0.1:{OPENAI_PORT}/v1")
    while True:
        time.sleep(1)
