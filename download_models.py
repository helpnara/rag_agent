"""[반입용 PC에서 실행] 인터넷 되는 PC에서 bge-m3 임베딩 모델을 내려받아
프로젝트의 ./models/bge-m3 폴더에 저장한다. 이 폴더째로 폐쇄망에 옮긴다.

Ollama LLM은 이 스크립트로 받지 않는다. README의 Ollama 반입 절차를 따를 것.

실행: python download_models.py
필요: pip install huggingface_hub
"""
import os
import sys

try:
    from huggingface_hub import snapshot_download
except ModuleNotFoundError:
    venv = os.path.join(".venv", "Scripts" if os.name == "nt" else "bin",
                        "python.exe" if os.name == "nt" else "python")
    print("[오류] huggingface_hub 패키지를 찾을 수 없습니다.\n")
    print(f"  지금 실행 중인 Python : {sys.executable}")
    print(f"  가상환경 활성 여부    : {'예' if sys.prefix != sys.base_prefix else '아니오'}\n")
    print("대부분 가상환경이 활성화되지 않았거나 의존성 설치 전인 경우입니다.")
    print("아래 중 하나로 해결하세요.\n")
    print("  1) 가상환경을 활성화하고 설치")
    print("       .\\.venv\\Scripts\\Activate.ps1        (Windows)")
    print("       source .venv/bin/activate            (macOS/Linux)")
    print("       pip install -r requirements-onprem.txt\n")
    print("  2) 인터프리터를 직접 지정해 실행")
    print(f"       {venv} download_models.py\n")
    print("  3) 이 스크립트만 쓰는 반입용 PC라면")
    print("       pip install huggingface_hub")
    sys.exit(1)

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
