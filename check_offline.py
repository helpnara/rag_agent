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

# 1) 임베딩 모델 폴더
mp = config.EMBEDDING_MODEL_PATH
check(f"임베딩 모델 폴더 존재: {mp}", os.path.isdir(mp),
      "download_models.py로 받은 models/bge-m3 폴더를 넣으세요.")
if os.path.isdir(mp):
    has_weight = any(f.endswith((".safetensors", ".bin")) for f in os.listdir(mp))
    check("임베딩 가중치 파일 존재", has_weight, "폴더가 비었거나 일부만 복사됐습니다.")

# 2) Qdrant 연결
try:
    from qdrant_client import QdrantClient
    QdrantClient(url=config.QDRANT_URL).get_collections()
    check(f"Qdrant 연결: {config.QDRANT_URL}", True)
except Exception as e:
    check(f"Qdrant 연결: {config.QDRANT_URL}", False, f"docker compose up -d 실행. ({e})")

# 3) Ollama 연결 + 모델 존재
try:
    with urllib.request.urlopen(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5) as r:
        body = r.read().decode()
    check(f"Ollama 연결: {config.OLLAMA_BASE_URL}", True)
    check(f"Ollama 모델 로드됨: {config.OLLAMA_MODEL}",
          config.OLLAMA_MODEL.split(":")[0] in body,
          f"ollama create/pull 로 {config.OLLAMA_MODEL} 를 준비하세요.")
except Exception as e:
    check(f"Ollama 연결: {config.OLLAMA_BASE_URL}", False,
          f"Ollama 실행 여부 확인. ({e})")

print()
print("모든 항목 통과 → python -m app.ingest 진행 가능" if ok
      else "위 실패 항목을 먼저 해결하세요.")
sys.exit(0 if ok else 1)
