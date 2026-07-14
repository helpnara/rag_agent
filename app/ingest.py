"""문서를 로드 → 청킹 → 임베딩 → Qdrant 적재.

- run(): docs 폴더 전체를 적재 (초기 구축/재색인)
- ingest_file(path): 단일 파일만 적재 (업로드 시 자동 색인)

실행: python -m app.ingest
"""
import os
from typing import Dict

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app import config
from app.loaders import load_directory, LOADERS
from app.vectorstore import get_vectorstore


def _splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def run():
    """docs 폴더 전체 적재."""
    print(f"[1/3] '{config.DOCS_DIR}' 폴더에서 문서 로딩...")
    raw_docs = load_directory(config.DOCS_DIR)
    print(f"  → {len(raw_docs)}개 문서 단위 로드 완료")

    print("[2/3] 청킹...")
    chunks = _splitter().split_documents(raw_docs)
    print(f"  → {len(chunks)}개 청크 생성")

    if not chunks:
        print("적재할 청크가 없습니다. DOCS_DIR을 확인하세요.")
        return

    print("[3/3] 임베딩 + Qdrant 적재...")
    get_vectorstore().add_documents(chunks)
    print(f"  → 컬렉션 '{config.QDRANT_COLLECTION}'에 적재 완료")


def ingest_file(path: str) -> Dict:
    """단일 파일만 적재한다. 업로드 직후 자동 색인용.
    반환: {"ok": bool, "chunks": int, "reason": str}
    """
    ext = os.path.splitext(path)[1].lower()
    loader = LOADERS.get(ext)
    if not loader:
        return {"ok": False, "chunks": 0, "reason": f"지원하지 않는 형식: {ext}"}
    if not os.path.exists(path):
        return {"ok": False, "chunks": 0, "reason": "파일을 찾을 수 없습니다."}

    try:
        raw_docs = loader(path)
        chunks = _splitter().split_documents(raw_docs)
        if not chunks:
            return {"ok": False, "chunks": 0, "reason": "추출된 텍스트가 없습니다."}
        get_vectorstore().add_documents(chunks)
        return {"ok": True, "chunks": len(chunks), "reason": ""}
    except Exception as e:
        return {"ok": False, "chunks": 0, "reason": str(e)}


if __name__ == "__main__":
    run()
