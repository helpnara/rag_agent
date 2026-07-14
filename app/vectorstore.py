"""Qdrant 벡터스토어 + 로컬 임베딩 (폐쇄망/오프라인 강제).

이 파일 최상단에서 HuggingFace의 인터넷 접속을 끈다.
모델은 반드시 로컬 폴더(config.EMBEDDING_MODEL_PATH)에서만 로드된다.
"""
import os

# --- 오프라인 강제: 어떤 경우에도 허브에 접속 시도하지 않음 ---
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app import config

_embeddings = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """로컬 폴더의 bge-m3 임베딩. 폴더가 없으면 명확한 안내와 함께 종료."""
    global _embeddings
    if _embeddings is None:
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


def get_client() -> QdrantClient:
    return QdrantClient(url=config.QDRANT_URL)


def ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if config.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=config.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=config.EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )


def get_vectorstore() -> QdrantVectorStore:
    client = get_client()
    ensure_collection(client)
    return QdrantVectorStore(
        client=client,
        collection_name=config.QDRANT_COLLECTION,
        embedding=get_embeddings(),
    )


def delete_by_source(source: str) -> None:
    """특정 파일명(source)으로 적재된 기존 벡터를 삭제한다.
    같은 파일을 다시 업로드할 때 중복 적재를 막는다."""
    from qdrant_client import models as qm
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if config.QDRANT_COLLECTION not in existing:
        return
    try:
        client.delete(
            collection_name=config.QDRANT_COLLECTION,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(must=[
                    qm.FieldCondition(
                        key="metadata.source",
                        match=qm.MatchValue(value=source),
                    )
                ])
            ),
        )
    except Exception as e:
        print(f"[delete_by_source] {source}: {e}")
