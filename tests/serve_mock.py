"""브라우저로 직접 확인하기 위한 목(mock) 기동 스크립트.

Ollama·Qdrant·외부 API 없이 웹 UI를 띄워 모드 전환·경고 배너·모델 목록을
눈으로 확인할 수 있다. (임베딩/검색은 스텁 — UI 동작 확인 전용)

실행:
    python tests/serve_mock.py              # 외부 API 정상 설정 상태
    python tests/serve_mock.py --no-key     # 외부 미설정 (외부 옵션 비활성화 확인)
    python tests/serve_mock.py --bad-key    # 잘못된 키 (오류 표시 확인)
→ http://127.0.0.1:18080
"""
import os
import sys
import types

os.environ["no_proxy"] = "127.0.0.1,localhost"
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import mock_llm_servers as mocks  # noqa: E402

NO_KEY = "--no-key" in sys.argv
BAD_KEY = "--bad-key" in sys.argv

os.environ["OLLAMA_BASE_URL"] = f"http://127.0.0.1:{mocks.OLLAMA_PORT}"
os.environ["OLLAMA_MODEL"] = "qwen2.5:7b"
os.environ["EXTERNAL_BASE_URL"] = f"http://127.0.0.1:{mocks.OPENAI_PORT}/v1"
os.environ["EXTERNAL_API_KEY"] = "" if NO_KEY else ("sk-bad" if BAD_KEY else "sk-test-valid")
os.environ["EXTERNAL_MODEL"] = "gpt-4o-mini"
os.environ["LLM_MODE"] = "local"

_stub = types.ModuleType("app.retrieval")
_stub.retrieve = lambda q, k=4: (
    "[출처 1] 사내 연차 규정: 연차는 입사일 기준 15일이다.",
    [{"index": 1, "source": "연차규정.pdf", "location": "p.3", "snippet": "연차는 입사일 기준 15일"}],
)
sys.modules["app.retrieval"] = _stub

mocks.start_background()

import uvicorn  # noqa: E402
from app.main import app  # noqa: E402

state = "미설정" if NO_KEY else ("잘못된 키" if BAD_KEY else "정상 설정")
print(f"\n외부 API 상태: {state}")
print("웹 UI: http://127.0.0.1:18080\n")
uvicorn.run(app, host="127.0.0.1", port=18080, log_level="warning")
