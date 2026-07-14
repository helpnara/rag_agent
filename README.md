# 사내 문서 RAG + Tool Calling 에이전트 (완전 로컬 버전)

임베딩과 LLM을 모두 내 PC에서 실행합니다.
**어떤 문서/질문도 인터넷으로 나가지 않습니다.** (랜선을 뽑아도 동작)

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
2. Docker Desktop (Qdrant 실행용)
3. Ollama for Windows  →  https://ollama.com/download
4. NVIDIA GPU 드라이버 (최신)

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
pip install -r requirements.txt

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

## GPU 확인 / CPU로 강제
- 기본값은 GPU(cuda) 사용입니다.
- GPU 인식이 안 되면 `app/vectorstore.py`의 `"device": "cuda"` 를 `"cpu"`로 변경.
- Ollama는 GPU를 자동 감지합니다.

## 완전 오프라인으로 쓰려면
최초 1회만 인터넷으로 (1) bge-m3, (2) ollama 모델을 받으면,
그 이후로는 인터넷을 끊어도 전부 동작합니다.

## 확장 포인트
- 내 모델 연결: `app/my_model.py`의 predict() 안을 실제 추론으로 교체
- 검색 품질: agent.py의 similarity_search를 하이브리드+리랭커로 교체
- 대화 기억: main.py에서 세션별 chat_history 관리
