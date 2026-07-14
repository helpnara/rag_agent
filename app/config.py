import os
from dotenv import load_dotenv

load_dotenv()

# --- 완전 로컬 + 폐쇄망(오프라인) 구성 ---

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "documents")

DOCS_DIR = os.getenv("DOCS_DIR", "./docs")

# 임베딩 모델을 "이름"이 아니라 프로젝트 안 로컬 폴더에서 읽는다.
# (반입 절차에서 이 폴더에 bge-m3 파일을 넣어둠)
EMBEDDING_MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "./models/bge-m3")
EMBEDDING_DIM = 1024  # bge-m3 차원

# 로컬 LLM (Ollama)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# GPU 사용 여부 ("cuda" 또는 "cpu")
DEVICE = os.getenv("DEVICE", "cuda")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 4
