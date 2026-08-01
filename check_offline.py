"""[운영용 폐쇄망 PC에서 실행] 오프라인 구동 준비가 됐는지 점검한다.
실행: python check_offline.py
"""
import os
import sys
import urllib.request

from app import config

ok = True

def check(label, cond, hint=""):
    global ok
    mark = "OK " if cond else "실패"
    print(f"[{mark}] {label}")
    if not cond and hint:
        print(f"       → {hint}")
    if not cond:
        ok = False

print(f"구성: 임베딩={config.EMBEDDING_BACKEND} · Qdrant={config.QDRANT_MODE} "
      f"· LLM={config.LLM_MODE} · device={config.DEVICE}\n")

# 1) 임베딩 모델
if config.EMBEDDING_BACKEND == "fastembed":
    # 데모용 경량 백엔드: 최초 1회 다운로드가 필요하므로 폐쇄망 대상이 아니다.
    check(f"임베딩 백엔드: fastembed ({config.FASTEMBED_MODEL})", True,
          "폐쇄망 운영에는 bge-m3(EMBEDDING_BACKEND=bge-m3)를 사용하세요.")
else:
    mp = config.EMBEDDING_MODEL_PATH
    check(f"임베딩 모델 폴더 존재: {mp}", os.path.isdir(mp),
          "download_models.py로 받은 models/bge-m3 폴더를 넣으세요.")
    if os.path.isdir(mp):
        has_weight = any(f.endswith((".safetensors", ".bin")) for f in os.listdir(mp))
        check("임베딩 가중치 파일 존재", has_weight, "폴더가 비었거나 일부만 복사됐습니다.")

# 2) 벡터DB — server 모드만 Docker가 필요하다
if config.QDRANT_MODE == "server":
    try:
        from qdrant_client import QdrantClient
        QdrantClient(url=config.QDRANT_URL).get_collections()
        check(f"Qdrant 연결: {config.QDRANT_URL}", True)
    except Exception as e:
        check(f"Qdrant 연결: {config.QDRANT_URL}", False,
              "Docker Qdrant를 띄우거나(docker compose up -d), "
              "Docker 없이 쓰려면 .env에 QDRANT_MODE=path 를 설정하세요.\n"
              f"         ({e})")
elif config.QDRANT_MODE == "path":
    parent = os.path.dirname(os.path.abspath(config.QDRANT_PATH)) or "."
    check(f"Qdrant 파일 모드 경로 쓰기 가능: {config.QDRANT_PATH}",
          os.access(parent, os.W_OK), "상위 폴더에 쓰기 권한이 필요합니다.")
else:
    check("Qdrant 메모리 모드 (재시작 시 재색인 필요)", True)

# 3) LLM — 로컬 모드일 때만 Ollama가 필요하다
if config.LLM_MODE == "external":
    check("외부 LLM 모드: API 키 설정됨", config.external_configured(),
          "EXTERNAL_API_KEY를 설정하세요. (외부 전송이 발생합니다)")
else:
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5) as r:
            body = r.read().decode()
        check(f"Ollama 연결: {config.OLLAMA_BASE_URL}", True)
        check(f"Ollama 모델 로드됨: {config.OLLAMA_MODEL}",
              config.OLLAMA_MODEL.split(":")[0] in body,
              f"ollama pull {config.OLLAMA_MODEL} 로 준비하세요.")
    except Exception as e:
        check(f"Ollama 연결: {config.OLLAMA_BASE_URL}", False,
              f"Ollama 실행 여부 확인. ({e})")

print()
print("모든 항목 통과 → python -m app.ingest 진행 가능" if ok
      else "위 실패 항목을 먼저 해결하세요.")
sys.exit(0 if ok else 1)
