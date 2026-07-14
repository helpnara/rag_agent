"""Ollama에 설치된 모델 목록 조회, 업로드 파일 저장 유틸."""
import json
import os
import urllib.request

from app import config


def list_ollama_models() -> list:
    """Ollama에 pull 되어 있는 모델 이름 목록을 반환.
    실패하면 config 기본 모델 하나만 반환."""
    try:
        url = f"{config.OLLAMA_BASE_URL}/api/tags"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode())
        names = [m["name"] for m in data.get("models", [])]
        return names or [config.OLLAMA_MODEL]
    except Exception:
        return [config.OLLAMA_MODEL]


# 업로드 허용 확장자 (loaders와 일치)
ALLOWED_UPLOAD = {".pdf", ".xlsx", ".xls", ".pptx", ".txt", ".md"}


def save_upload(filename: str, content: bytes) -> dict:
    """업로드된 파일을 docs 폴더에 저장. 결과 dict 반환."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_UPLOAD:
        return {"ok": False, "reason": f"지원하지 않는 형식입니다: {ext}"}

    os.makedirs(config.DOCS_DIR, exist_ok=True)
    # 경로 조작 방지: 파일명만 사용
    safe = os.path.basename(filename)
    dest = os.path.join(config.DOCS_DIR, safe)
    with open(dest, "wb") as f:
        f.write(content)
    return {"ok": True, "name": safe}
