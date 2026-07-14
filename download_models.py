"""[반입용 PC에서 실행] 인터넷 되는 PC에서 bge-m3 임베딩 모델을 내려받아
프로젝트의 ./models/bge-m3 폴더에 저장한다. 이 폴더째로 폐쇄망에 옮긴다.

Ollama LLM은 이 스크립트로 받지 않는다. README의 Ollama 반입 절차를 따를 것.

실행: python download_models.py
필요: pip install huggingface_hub
"""
from huggingface_hub import snapshot_download

TARGET = "./models/bge-m3"

print("bge-m3 다운로드 시작 (약 2GB)...")
snapshot_download(
    repo_id="BAAI/bge-m3",
    local_dir=TARGET,
    local_dir_use_symlinks=False,   # 실제 파일로 저장(복사·이동 안전)
    ignore_patterns=["*.onnx", "onnx/*"],  # 불필요한 대용량 파일 제외
)
print(f"완료: {TARGET}")
print("이 폴더(models/bge-m3)를 프로젝트와 함께 폐쇄망으로 옮기세요.")
