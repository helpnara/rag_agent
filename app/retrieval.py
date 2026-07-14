"""문서 검색(retrieval)을 담당. 출처 메타데이터를 함께 반환한다."""
from typing import List, Dict, Tuple

from app import config
from app.vectorstore import get_vectorstore


def _location(meta: dict) -> str:
    if meta.get("page"):
        return f"{meta['page']}페이지"
    if meta.get("slide"):
        return f"슬라이드 {meta['slide']}"
    if meta.get("sheet"):
        return f"시트 {meta['sheet']}"
    return ""


def retrieve(query: str) -> Tuple[str, List[Dict]]:
    """질문으로 문서를 검색해 (컨텍스트 문자열, 출처 목록)을 반환."""
    vs = get_vectorstore()
    results = vs.similarity_search(query, k=config.TOP_K)
    if not results:
        return "", []

    context_blocks = []
    sources: List[Dict] = []
    for i, d in enumerate(results, 1):
        src = d.metadata.get("source", "?")
        loc = _location(d.metadata)
        label = f"{src} {loc}".strip()
        context_blocks.append(f"[출처 {i}: {label}]\n{d.page_content}")
        sources.append({
            "index": i,
            "source": src,
            "location": loc,
            "snippet": d.page_content[:400],
        })
    return "\n\n---\n\n".join(context_blocks), sources
