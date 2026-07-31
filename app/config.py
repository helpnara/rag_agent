import os
from dotenv import load_dotenv

load_dotenv()

# --- 완전 로컬 + 폐쇄망(오프라인) 구성 ---

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "documents")

# Qdrant 접속 방식
#   server : 로컬 Docker Qdrant (온프레미스 기본, QDRANT_URL 사용)
#   memory : 프로세스 메모리 (Docker 불필요 — Streamlit Cloud 데모용, 재시작 시 소실)
#   path   : 로컬 파일 (Docker 불필요, QDRANT_PATH에 저장)
QDRANT_MODE = os.getenv("QDRANT_MODE", "server")
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_local")

DOCS_DIR = os.getenv("DOCS_DIR", "./docs")

# --- 임베딩 백엔드 (둘 다 로컬 실행. 외부 임베딩 API는 쓰지 않는다) ---
#   bge-m3    : 온프레미스 기본. 반입한 로컬 폴더에서만 로드, 허브 접속 차단.
#   fastembed : 데모용 경량(ONNX, torch 불필요). 최초 1회 모델 다운로드가 필요하므로
#               폐쇄망에서는 사용하지 않는다.
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "bge-m3")

# 임베딩 모델을 "이름"이 아니라 프로젝트 안 로컬 폴더에서 읽는다.
# (반입 절차에서 이 폴더에 bge-m3 파일을 넣어둠)
EMBEDDING_MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "./models/bge-m3")
EMBEDDING_DIM = 1024  # bge-m3 차원

# fastembed 백엔드 설정 (데모 전용)
FASTEMBED_MODEL = os.getenv(
    "FASTEMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
FASTEMBED_DIM = int(os.getenv("FASTEMBED_DIM", "384"))
FASTEMBED_CACHE_DIR = os.getenv("FASTEMBED_CACHE_DIR", "")

# 로컬 LLM (Ollama)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# --- LLM 동작 모드 ---
# "local"    : 완전 로컬(Ollama). 기본값이자 폐쇄망 권장 모드.
# "external" : 외부 생성형 LLM API(OpenAI 호환) 사용.
#              ⚠️ 이 모드에서는 질문 + 검색된 사내 문서 컨텍스트가 외부로 전송된다.
#              폐쇄망 보안 정책상 반드시 명시적으로 켠 경우에만 사용한다.
# 사용자는 요청마다 모드를 지정할 수 있으며, 이 값은 UI 기본값으로 쓰인다.
LLM_MODE = os.getenv("LLM_MODE", "local")

# --- 외부 LLM (OpenAI 호환 엔드포인트) ---
# base_url + api_key + model 만 맞추면 OpenAI 공식 API,
# vLLM / Together / OpenRouter 등 OpenAI 호환 서버를 모두 사용할 수 있다.
EXTERNAL_BASE_URL = os.getenv("EXTERNAL_BASE_URL", "https://api.openai.com/v1")
EXTERNAL_API_KEY = os.getenv("EXTERNAL_API_KEY", "")
EXTERNAL_MODEL = os.getenv("EXTERNAL_MODEL", "gpt-4o-mini")


def external_configured() -> bool:
    """외부 API 모드를 사용할 수 있는 최소 설정(API 키)이 갖춰졌는지."""
    return bool(EXTERNAL_API_KEY.strip())


# --- 데모(Streamlit Cloud) 설정 ---
# 공개 데모에서 운영자 키로 무제한 사용되는 것을 막기 위한 세션당 질문 수 제한.
# 방문자가 자기 API 키를 입력하면 이 제한은 적용되지 않는다.
DEMO_QUESTION_LIMIT = int(os.getenv("DEMO_QUESTION_LIMIT", "5"))
DEMO_DOCS_DIR = os.getenv("DEMO_DOCS_DIR", "./demo_docs")


# GPU 사용 여부 ("cuda" 또는 "cpu")
DEVICE = os.getenv("DEVICE", "cuda")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 4
