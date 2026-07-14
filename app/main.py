"""FastAPI 웹 서버 - 파일패널 + 채팅(스트리밍/기억/출처) + 업로드/모델선택.

엔드포인트:
  GET  /                 : 웹 UI
  GET  /api/files        : docs 폴더 파일 목록
  GET  /api/models       : Ollama에 설치된 모델 목록
  POST /api/upload       : 문서 업로드 (docs 폴더에 저장)
  POST /api/chat/stream  : 질문 → SSE 스트리밍 답변
  POST /api/chat/reset   : 세션 대화기록 초기화
  POST /api/ingest       : 폴더 재적재
  GET  /api/status       : 백엔드 상태
"""
import json
import os

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import config
from app.files import list_files
from app.models_util import list_ollama_models, save_upload

app = FastAPI(title="사내 문서 RAG 에이전트")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    model: str = None


class ResetRequest(BaseModel):
    session_id: str = "default"


@app.get("/api/files")
def api_files():
    files = list_files()
    return {"files": files, "count": len(files)}


@app.get("/api/models")
def api_models():
    return {"models": list_ollama_models(), "default": config.OLLAMA_MODEL}


@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    content = await file.read()
    result = save_upload(file.filename, content)
    if not result.get("ok"):
        return result

    # 자동 색인: 저장된 파일을 바로 벡터DB에 적재
    import os
    from app.vectorstore import delete_by_source
    from app.ingest import ingest_file

    name = result["name"]
    dest = os.path.join(config.DOCS_DIR, name)
    # 같은 파일명의 기존 벡터를 지우고 새로 적재 (중복 방지)
    delete_by_source(name)
    idx = ingest_file(dest)
    result["indexed"] = idx.get("ok", False)
    result["chunks"] = idx.get("chunks", 0)
    if not idx.get("ok"):
        result["index_reason"] = idx.get("reason", "")
    return result


@app.post("/api/chat/stream")
def api_chat_stream(req: ChatRequest):
    from app.chat_engine import stream_answer

    def event_gen():
        try:
            for ev in stream_answer(req.session_id, req.message, req.model):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except GeneratorExit:
            # 클라이언트가 중단(연결 종료)한 경우: 조용히 종료
            return
        except Exception as e:
            err = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/api/chat/reset")
def api_chat_reset(req: ResetRequest):
    from app.chat_engine import clear_history
    clear_history(req.session_id)
    return {"status": "ok"}


@app.post("/api/ingest")
def api_ingest():
    from app.ingest import run as ingest_run
    ingest_run()
    return {"status": "ok"}


@app.get("/api/status")
def api_status():
    return {"docs_dir": config.DOCS_DIR, "model": config.OLLAMA_MODEL, "device": config.DEVICE}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
