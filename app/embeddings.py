"""임베딩 백엔드 추상화 — 온프레미스(bge-m3) / 데모(fastembed) 전환.

두 백엔드 모두 **로컬 실행**이다. 외부 임베딩 API는 어떤 모드에서도 쓰지 않는다.
(CLAUDE.md 절대원칙: 임베딩은 항상 로컬)

  - bge-m3   : 온프레미스 기본. 반입한 로컬 폴더에서만 로드, 허브 접속 차단. 1024차원.
  - fastembed: 데모(Streamlit Cloud)용. ONNX 기반이라 torch가 필요 없어
               설치 용량·메모리가 작다. 최초 1회 모델을 내려받으므로 폐쇄망에서는 쓰지 않는다.

백엔드에 따라 벡터 차원이 다르므로, 컬렉션을 새로 만들거나 재색인해야 한다.
"""
from typing import List

from langchain_core.embeddings import Embeddings

from app import config


def embedding_dim() -> int:
    """현재 백엔드의 벡터 차원."""
    if config.EMBEDDING_BACKEND == "fastembed":
        return config.FASTEMBED_DIM
    return config.EMBEDDING_DIM


class FastEmbedEmbeddings(Embeddings):
    """fastembed(ONNX)를 LangChain Embeddings 인터페이스에 맞춘 얇은 어댑터.

    langchain-community 의존성을 늘리지 않기 위해 직접 구현한다.
    langchain-qdrant가 Embeddings 인스턴스인지 검사하므로 반드시 상속해야 한다.
    """

    def __init__(self, model_name: str, cache_dir: str = None):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [v.tolist() for v in self._model.embed(list(texts))]

    def embed_query(self, text: str) -> List[float]:
        return next(iter(self._model.embed([text]))).tolist()


_embeddings = None


def get_embeddings():
    """설정된 백엔드의 임베딩 객체를 반환(프로세스 내 1회 생성)."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    if config.EMBEDDING_BACKEND == "fastembed":
        _embeddings = FastEmbedEmbeddings(
            model_name=config.FASTEMBED_MODEL,
            cache_dir=config.FASTEMBED_CACHE_DIR or None,
        )
        return _embeddings

    # --- 기본: 온프레미스 bge-m3 (로컬 폴더에서만 로드) ---
    import os

    from langchain_huggingface import HuggingFaceEmbeddings

    if not os.path.isdir(config.EMBEDDING_MODEL_PATH):
        raise FileNotFoundError(
            f"임베딩 모델 폴더가 없습니다: {config.EMBEDDING_MODEL_PATH}\n"
            "반입 절차에 따라 bge-m3 파일을 이 폴더에 넣으세요."
        )
    _embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL_PATH,   # 이름이 아니라 경로
        model_kwargs={"device": config.DEVICE},
        encode_kwargs={"normalize_embeddings": True},
    )
    return _embeddings


def reset() -> None:
    """설정 변경 후 임베딩 객체를 다시 만들게 한다(테스트용)."""
    global _embeddings
    _embeddings = None
