# 사내 문서 RAG + Tool Calling 에이전트

이 저장소는 **두 가지 실행 형태**를 함께 담고 있습니다.

| | 온프레미스 (본 운영) | 공개 데모 (Streamlit Cloud) |
|---|---|---|
| 진입점 | `app/main.py` (FastAPI) | `streamlit_app.py` |
| 의존성 | `requirements-onprem.txt` | `requirements.txt` |
| LLM | Ollama 로컬 | 외부 OpenAI 호환 API |
| 임베딩 | bge-m3 (로컬, 1024차원) | fastembed 경량 (로컬, 384차원) |
| 벡터DB | Qdrant (Docker) | qdrant-client 메모리 모드 |
| 데이터 | 사내 문서, 외부 전송 없음 | 공개 샘플 문서만 |

개발 전략은 **데모로 먼저 검증 → 온프레미스 이식**입니다.
아래 문서는 온프레미스 기준이며, 데모 배포는 [공개 데모 배포](#공개-데모-streamlit-cloud-배포)를 보세요.

---

## 온프레미스 (완전 로컬 버전)

임베딩과 LLM을 모두 내 PC에서 실행합니다.
**어떤 문서/질문도 인터넷으로 나가지 않습니다.** (랜선을 뽑아도 동작)

> 💡 **개인 PC에서 처음 돌려보는 경우**는 아래 [개인 PC 빠른 시작](#개인-pc-빠른-시작-windows--docker-없이)을 먼저 보세요.
> Docker 없이 더 적은 준비물로 동일한 온프레미스 구성을 시험할 수 있습니다.
>
> 💡 **VS Code로 개발·테스트하려면** `개발환경_VSCode_가이드.md`를 보세요.
> 저장소에 실행·디버그 구성(`.vscode/`)이 포함되어 있어 F5로 바로 실행됩니다.

---

## 개인 PC 빠른 시작 (Windows · Docker 없이)

사내 반입 전에 **내 PC에서 온프레미스 형태를 그대로 시험**하는 절차입니다.
폐쇄망 절차(반입·오프라인 강제)와 달리, 인터넷으로 모델을 직접 내려받습니다.

### 준비물
| 필요 | 비고 |
|------|------|
| Python 3.11 | "Add python.exe to PATH" 체크 |
| Ollama for Windows | https://ollama.com/download |
| 디스크 약 8GB | bge-m3 약 2GB + LLM 약 5GB |
| Docker | **불필요** (`QDRANT_MODE=path` 사용) |
| GPU | **불필요** (기본 CPU) |

### 1) 저장소 + 가상환경
```powershell
git clone https://github.com/helpnara/rag_agent.git
cd rag_agent

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements-onprem.txt      # torch 포함이라 10분 이상 걸릴 수 있음
```

### 2) 로컬 LLM 받기
```powershell
ollama pull qwen2.5:7b
```
- CPU만 있으면 응답이 느립니다. 가볍게 확인하려면 `ollama pull qwen2.5:3b` 후
  `.env`의 `OLLAMA_MODEL=qwen2.5:3b`로 바꾸세요.

### 3) 임베딩 모델 받기 (약 2GB)
```powershell
python download_models.py
```
→ `models\bge-m3` 폴더에 저장됩니다. 이후에는 인터넷 없이 동작합니다.

### 4) 설정 파일
```powershell
copy .env.example .env
```
`.env`를 열어 **Docker를 쓰지 않도록** 한 줄만 바꿉니다.
```
QDRANT_MODE=path        # server → path  (Docker 불필요, 로컬 파일에 저장)
```
> `path` 모드는 색인 결과가 `qdrant_local\` 폴더에 저장되어 **재시작해도 유지**됩니다.
> Docker Desktop을 쓰고 싶으면 `QDRANT_MODE=server`로 두고 `docker compose up -d`를 실행하세요.

### 5) 준비 상태 점검
```powershell
python check_offline.py
```
현재 설정(임베딩·벡터DB·LLM)에 맞춰 점검하고, 부족한 항목과 해결 방법을 알려줍니다.
**모든 항목이 통과한 뒤** 다음으로 넘어가세요.

### 6) 문서 넣고 색인
```powershell
# docs 폴더에 PDF/xlsx/pptx/txt/md 파일을 넣은 뒤
python -m app.ingest
```
테스트용 문서가 없다면 `demo_docs\`의 샘플 3종을 `docs\`로 복사해 쓰면 됩니다.

### 7) 실행
```powershell
uvicorn app.main:app --reload
```
브라우저 → http://localhost:8000

### 두 번째부터
```powershell
cd rag_agent
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```
(Ollama는 설치 후 백그라운드로 자동 실행됩니다. `path` 모드면 Docker도 필요 없습니다.)

### 잘 안 될 때
| 증상 | 확인 |
|------|------|
| `ModuleNotFoundError: huggingface_hub` | 가상환경 미활성 또는 설치 전. `python -c "import sys; print(sys.executable)"` 로 확인 후 `.\.venv\Scripts\Activate.ps1` |
| `Qdrant 연결 실패` (`WinError 10061`) | 4) `.env`에 `QDRANT_MODE=path` 설정 여부 확인. `.env`가 없으면 `copy .env.example .env` 먼저 |
| `임베딩 모델 폴더가 없습니다` | 3) `python download_models.py` 실행 여부 |
| `Ollama 연결 실패` | 작업 표시줄에 Ollama 실행 중인지, `ollama list` 확인 |
| 답변이 매우 느림 | CPU 추론 특성. 더 작은 모델(`qwen2.5:3b`)로 교체 |
| 답변이 "모른다"만 함 | 6) 색인을 했는지, 화면 좌측에 문서가 보이는지 확인 |
| `torch` 설치 실패 | Python 3.11인지 확인(3.13은 미지원 패키지 있음) |

### 외부 LLM API도 함께 시험하려면
`.env`에 아래를 추가하면 화면 상단에서 **로컬 ↔ 외부 API**를 전환할 수 있습니다.
```
EXTERNAL_API_KEY=sk-...
```
> ⚠️ 외부 모드에서는 질문과 검색된 문서 내용이 외부로 전송됩니다. 개인 PC 시험 시에만 쓰세요.

### 폐쇄망(사내)으로 옮길 때 달라지는 점
| | 개인 PC | 폐쇄망 |
|---|---|---|
| 모델 수급 | 인터넷에서 직접 다운로드 | 반입 PC에서 받아 복사 (`README_OFFLINE.md`) |
| 벡터DB | `QDRANT_MODE=path` 권장 | Docker Qdrant(`server`) 권장 |
| 패키지 | `pip install`로 온라인 설치 | wheel 파일 반입 후 오프라인 설치 |
| LLM 모드 | 필요 시 외부 API 시험 가능 | **로컬만 사용** |

---

## 온프레미스 상세 (기존 절차)

```
문서 폴더 → 로더 → 청킹 → bge-m3 임베딩(로컬) → Qdrant(로컬)
질문 → FastAPI → Ollama LLM(로컬, Tool Calling) → [문서검색 | 내 모델] → 응답
```

## 데이터 경로 (전부 로컬)
| 구성요소 | 위치 |
|---|---|
| 원본 문서 | 내 PC (docs/) |
| 벡터DB Qdrant | 내 PC (Docker) |
| 임베딩 bge-m3 | 내 PC (GPU) |
| LLM Ollama | 내 PC (GPU) |
→ 외부 전송 지점 없음.

## 사전 설치 (윈도우, 한 번만)
1. Python 3.11 (설치 시 "Add python.exe to PATH" 체크)
2. Ollama for Windows  →  https://ollama.com/download
3. Docker Desktop — **선택**. 설치하지 않으려면 `QDRANT_MODE=path`를 쓰세요(아래 참고).
4. NVIDIA GPU 드라이버 — **선택**. 없으면 CPU로 동작합니다(기본값).

## 준비: 로컬 LLM 받기
Ollama 설치 후 PowerShell에서:
```powershell
ollama pull qwen2.5:7b
```
- GPU 메모리가 넉넉하면 품질↑ 위해 `qwen2.5:14b` 또는 `qwen2.5:32b` 권장
- 반드시 tool calling 지원 모델을 쓸 것 (qwen2.5, llama3.1 계열)

## 실행 순서 (PowerShell, C:\rag-agent 기준)
```powershell
cd C:\rag-agent

# 1) 가상환경
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) 패키지 설치 (torch/transformers 포함이라 시간이 걸림)
pip install -r requirements-onprem.txt

# 3) 환경변수 (키 입력 불필요, 그대로 복사만)
copy .env.example .env

# 4) Qdrant 띄우기 (Docker Desktop 실행 중이어야 함)
docker compose up -d

# 5) docs 폴더에 문서 넣고 벡터 적재
#    (최초 실행 시 bge-m3 모델 약 2GB 자동 다운로드)
python -m app.ingest

# 6) 웹서버 실행
uvicorn app.main:app --reload
```
브라우저 → http://localhost:8000

## 두 번째부터
```powershell
cd C:\rag-agent
.\.venv\Scripts\Activate.ps1
docker compose up -d
uvicorn app.main:app --reload
```
(Ollama는 설치 후 백그라운드 서비스로 자동 실행됩니다.)

## GPU / CPU 설정
- **기본값은 CPU**입니다(운영 환경이 GPU 없는 사무용 PC 기준).
- NVIDIA GPU가 있으면 `.env`에 `DEVICE=cuda`로 올려 쓸 수 있습니다.
- Ollama는 GPU를 자동 감지하므로 별도 설정이 필요 없습니다.

## 완전 오프라인으로 쓰려면
최초 1회만 인터넷으로 (1) bge-m3, (2) ollama 모델을 받으면,
그 이후로는 인터넷을 끊어도 전부 동작합니다.

## LLM 동작 모드 (로컬 / 외부) — v4.2
기본은 위 설명대로 **완전 로컬(온프레미스)** 모드입니다. 외부망 연결이 허용되는 환경에서는
**외부 생성형 LLM API(OpenAI 호환)** 모드를 선택적으로 켤 수 있습니다.

> ⚠️ 외부 모드에서는 **질문 + 검색된 문서 컨텍스트가 외부 서버로 전송**됩니다.
> 폐쇄망 보안 정책을 확인한 뒤에만 사용하세요. **임베딩은 두 모드 모두 로컬 bge-m3**를 씁니다.

`.env`에 아래를 설정하면 화면 상단에 "외부 API" 옵션이 활성화됩니다(키가 없으면 비활성).
```
LLM_MODE=local                          # 기본 모드 (local / external)
EXTERNAL_BASE_URL=https://api.openai.com/v1
EXTERNAL_API_KEY=sk-...                  # 비어 있으면 외부 모드 비활성화
EXTERNAL_MODEL=gpt-4o-mini
```
- 화면 상단 콤보박스에서 **온프레미스(로컬) ↔ 외부 API**를 전환합니다.
- 외부 모드 선택 시 상단에 전송 경고 배너가 나타납니다.
- OpenAI 외에 vLLM·OpenRouter 등 **OpenAI 호환 서버**도 `EXTERNAL_BASE_URL`만 바꾸면 됩니다.

---

## 공개 데모 (Streamlit Cloud) 배포

포트폴리오·시연용 공개 데모입니다. **사내 문서를 올리지 않고 공개 샘플 문서로만** 시연합니다.

### 왜 구성이 다른가
Streamlit Community Cloud는 메모리가 작고 Docker·GPU가 없어 온프레미스 스택을 그대로 올릴 수 없습니다.
- bge-m3(약 2GB) → **fastembed 경량 모델**(ONNX, torch 불필요). 둘 다 로컬 실행이라 외부 임베딩 API는 쓰지 않습니다.
- Qdrant Docker → **qdrant-client 메모리 모드** (앱 재시작 시 샘플 문서를 자동 재색인)
- Ollama 로컬 LLM → **외부 OpenAI 호환 API** (Cloud에서 로컬 LLM 구동 불가)

> ⚠️ 데모는 외부 LLM API를 쓰므로 질문과 검색된 문서 내용이 외부로 전송됩니다.
> 화면 상단에도 같은 경고가 표시됩니다.

### 로컬에서 데모 실행 (Windows / PowerShell)

Cloud에 올리기 전에 **내 PC에서 먼저 확인**하는 것을 권장합니다. Docker·Ollama 없이 동작합니다.

```powershell
git clone https://github.com/helpnara/rag_agent.git
cd rag_agent

# 데모 전용 가상환경 (온프레미스용 .venv와 반드시 분리)
py -3.11 -m venv .venv-demo
.\.venv-demo\Scripts\Activate.ps1

pip install -r requirements.txt
streamlit run streamlit_app.py
```
브라우저 → http://localhost:8501

- **최초 1회 인터넷 필요**: fastembed 임베딩 모델(약 220MB)을 자동으로 내려받습니다.
  (`%USERPROFILE%\.cache\fastembed` 에 저장, 이후에는 오프라인 동작)
- 실행 후 **사이드바에 본인의 API 키를 입력**하면 바로 질문할 수 있습니다.
- 키 없이 화면만 보려면 그대로 두고 UI·색인 결과만 확인하면 됩니다.

macOS/Linux는 `python -m venv .venv-demo && source .venv-demo/bin/activate` 로 대체합니다.

### 키·모델 없이 동작만 점검하기
API 키나 모델 다운로드 없이 배선만 확인하려면 검증 스크립트를 씁니다.
```powershell
python tests\verify_demo_rag.py     # 데모 가상환경에서 (모델 못 받으면 스텁으로 자동 대체)
```

### Streamlit Cloud 배포
> 로컬 확인이 끝난 뒤 진행하는 것을 권장합니다. Cloud는 로그 확인과 재시도가 번거롭습니다.

1. Streamlit Community Cloud → **Create app** → 이 저장소 선택
   - Branch: `main`
   - Main file path: `streamlit_app.py`
2. **Settings → Secrets** 에 운영자 키를 넣습니다(선택).
   ```toml
   EXTERNAL_API_KEY = "sk-..."
   ```
   - 키를 넣으면 방문자가 키 없이 **`DEMO_QUESTION_LIMIT`(기본 5)회**까지 체험할 수 있습니다.
   - 키를 넣지 않으면 방문자가 각자 키를 입력해야 하며 운영자 비용은 0입니다.
   - 방문자가 본인 키를 입력하면 횟수 제한 없이 사용합니다.
3. 저장소가 목록에 안 보이면 Streamlit의 GitHub 연동을 재승인하세요.

### 샘플 문서
`demo_docs/`의 가상 회사 문서(인사규정·정보보안·경비처리)를 사용합니다.
실제 사규가 아니며 공개해도 문제없는 내용입니다.

---

## 확장 포인트
- 내 모델 연결: `app/my_model.py`의 predict() 안을 실제 추론으로 교체
- 검색 품질: agent.py의 similarity_search를 하이브리드+리랭커로 교체
- 대화 기억: main.py에서 세션별 chat_history 관리

## 검증
```bash
python tests/verify_llm_modes.py   # 로컬/외부 LLM 모드 (온프레미스 환경)
python tests/verify_demo_rag.py    # 데모 구성 (데모 환경)
```
자세한 내용은 `tests/README.md`를 참고하세요.
