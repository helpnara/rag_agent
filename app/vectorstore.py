"""Qdrant 벡터스토어 + 로컬 임베딩.

온프레미스 기본값(EMBEDDING_BACKEND=bge-m3)에서는 이 파일 최상단에서
HuggingFace의 인터넷 접속을 끄고, 모델은 반드시 로컬 폴더에서만 로드된다.

데모용 fastembed 백엔드는 최초 1회 모델 다운로드가 필요하므로 이때만
오프라인 강제를 적용하지 않는다. (폐쇄망에서는 fastembed를 쓰지 않는다)
"""
import os

from app import config

# --- 오프라인 강제: 폐쇄망 기본 백엔드에서는 어떤 경우에도 허브에 접속하지 않음 ---
if config.EMBEDDING_BACKEND != "fastembed":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.embeddings import embedding_dim, get_embeddings  # noqa: F401  (재노출)

_client = None


def get_client() -> QdrantClient:
    """QDRANT_MODE에 따라 서버/메모리/파일 클라이언트를 만든다.

    memory·path 모드는 로컬 클라이언트라 프로세스마다 별도 인스턴스가 되므로
    한 번 만든 클라이언트를 재사용한다(파일 모드의 잠금 충돌도 방지).
    """
    global _client
    if _client is not None:
        return _client

    if config.QDRANT_MODE == "memory":
        _client = QdrantClient(location=":memory:")
    elif config.QDRANT_MODE == "path":
        os.makedirs(config.QDRANT_PATH, exist_ok=True)
        _client = QdrantClient(path=config.QDRANT_PATH)
    else:
        _client = QdrantClient(url=config.QDRANT_URL)
    return _client


def ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if config.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=config.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=embedding_dim(),
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
