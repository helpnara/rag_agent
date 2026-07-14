"""docs 폴더의 파일 목록과 메타데이터를 조회한다.
좌측 파일 패널이 이 정보를 사용한다.
"""
import os
from datetime import datetime
from typing import List, Dict

from app import config

# 지원 확장자 (loaders.LOADERS와 동일하게 유지). 무거운 라이브러리
# 임포트 없이 목록 조회가 가능하도록 여기에 상수로 둔다.
SUPPORTED_EXTS = {".pdf", ".xlsx", ".xls", ".pptx", ".txt", ".md"}


def _human_size(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024:
            return f"{num:.0f}{unit}" if unit == "B" else f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}TB"


def list_files() -> List[Dict]:
    """docs 폴더를 순회하며 지원 파일 목록을 반환."""
    docs_dir = config.DOCS_DIR
    items: List[Dict] = []
    if not os.path.isdir(docs_dir):
        return items
    for root, _, files in os.walk(docs_dir):
        for name in sorted(files):
            ext = os.path.splitext(name)[1].lower()
            supported = ext in SUPPORTED_EXTS
            path = os.path.join(root, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            rel = os.path.relpath(path, docs_dir)
            items.append({
                "name": name,
                "path": rel,
                "ext": ext.lstrip("."),
                "size": _human_size(st.st_size),
                "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "supported": supported,
            })
    return items
