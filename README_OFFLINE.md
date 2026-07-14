# 폐쇄망(오프라인) 반입 및 설치 가이드

인터넷을 타는 요소는 4가지입니다. 각각을 [반입용 PC]에서 받아
승인 매체로 옮긴 뒤 [운영용 폐쇄망 PC]에서 오프라인 설치합니다.

| # | 요소 | 크기(대략) | 방법 |
|---|------|-----------|------|
| 1 | 파이썬 패키지 | 수 GB | pip download → 오프라인 설치 |
| 2 | 임베딩 bge-m3 | 약 2GB | download_models.py |
| 3 | LLM (Ollama) | 5~20GB | ollama 모델 파일 복사 |
| 4 | Qdrant 도커 이미지 | 약 150MB | docker save/load |

⚠️ [반입용 PC]와 [운영용 PC]는 **OS·Python 버전·CPU 아키텍처를 동일하게**
맞추세요. (예: 둘 다 Windows 11 x64 + Python 3.11). torch 등 바이너리 패키지가
환경에 종속되기 때문입니다.

================================================================
## A. 반입용 PC (인터넷 O) 에서 준비
================================================================

프로젝트 폴더에서 PowerShell:

```powershell
# 가상환경 (운영용과 동일 파이썬 버전)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# --- 1. 파이썬 패키지를 wheel 파일로 모두 내려받기 ---
mkdir wheels
pip download -r requirements.txt -d wheels
#   (GPU torch가 필요하면 아래처럼 인덱스 지정해 별도 다운로드)
#   pip download torch --index-url https://download.pytorch.org/whl/cu121 -d wheels

# --- 2. 임베딩 모델 받기 → ./models/bge-m3 ---
pip install huggingface_hub
python download_models.py

# --- 3. Ollama LLM 받기 ---
#   Ollama 설치 후:
ollama pull qwen2.5:7b
#   받은 모델은 아래 폴더에 저장됨 (통째로 복사할 것):
#   Windows:  C:\Users\<사용자>\.ollama\models
#   이 models 폴더 전체를 매체에 복사

# --- 4. Qdrant 도커 이미지 저장 ---
docker pull qdrant/qdrant:latest
docker save qdrant/qdrant:latest -o qdrant_image.tar
```

이제 매체에 담을 것:
- 프로젝트 폴더 전체 (models/bge-m3 포함)
- wheels/ 폴더
- Ollama의 .ollama\models 폴더
- qdrant_image.tar

================================================================
## B. 운영용 PC (폐쇄망, 인터넷 X) 에서 설치
================================================================

사전에 오프라인 설치본이 필요한 것 (사내 승인 후 반입):
- Python 3.11 설치 파일
- Docker Desktop 설치 파일
- Ollama 설치 파일
- NVIDIA GPU 드라이버

프로젝트를 C:\rag-agent 에 풀고 PowerShell:

```powershell
cd C:\rag-agent

# 가상환경
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# --- 1. 파이썬 패키지 오프라인 설치 (인터넷 접속 안 함) ---
pip install --no-index --find-links=wheels -r requirements.txt

# --- 2. 임베딩 모델: 이미 models/bge-m3 에 있으면 그대로 사용 ---

# --- 3. Ollama 모델 배치 ---
#   반입한 .ollama\models 폴더를 아래 위치에 복사:
#   C:\Users\<사용자>\.ollama\models
#   그 후 Ollama가 실행 중이면 확인:
ollama list        # qwen2.5:7b 가 보이면 성공

# --- 4. Qdrant 도커 이미지 로드 ---
docker load -i qdrant_image.tar

# 환경변수
copy .env.example .env

# Qdrant 실행
docker compose up -d

# --- 준비상태 자동 점검 ---
python check_offline.py
#   모든 항목 OK 나오면 진행

# 문서 적재 → 서버 실행
python -m app.ingest
uvicorn app.main:app --reload
```
브라우저 → http://localhost:8000

================================================================
## 자주 걸리는 부분
================================================================
- **check_offline.py에서 임베딩 폴더 실패**: models/bge-m3 안에
  .safetensors 파일까지 전부 복사됐는지 확인 (일부만 복사되기 쉬움).
- **Ollama 모델이 안 보임**: .ollama\models 를 폴더 구조 그대로
  (blobs, manifests 하위폴더 포함) 복사해야 함.
- **torch가 GPU를 못 씀**: 반입 PC에서 CPU용 torch를 받았을 가능성.
  cu121 인덱스로 다시 받거나, 급하면 .env의 DEVICE=cpu 로 임시 동작.
- **pip install에서 인터넷 시도**: --no-index 옵션이 빠졌는지 확인.

================================================================
## 웹 UI (좌측 파일 목록 + 우측 채팅)
================================================================
서버 실행 후 브라우저에서 http://localhost:8000 접속.

- 좌측: docs 폴더의 파일 목록. 지원 형식은 색상 배지, 미지원은 흐리게 표시.
  · [새로고침] 파일 목록 다시 읽기
  · [색인 갱신] 문서를 다시 벡터화 (파일 추가/변경 후 누르기)
- 우측: 질문 입력 → 문서 근거로 답변. Enter 전송, Shift+Enter 줄바꿈.

UI는 static/index.html 단일 파일이며 외부 리소스(CDN)를 쓰지 않아
폐쇄망에서도 그대로 동작합니다.

향후 고도화 여지:
- 답변 스트리밍(타이핑 효과), 출처 문서 클릭 시 원문 미리보기
- 대화 기억(세션별 chat_history), 파일 업로드 버튼
- 마크다운 렌더링, 다크 모드

----------------------------------------------------------------
## 웹 UI 고도화 (v2)
----------------------------------------------------------------
다음 4가지가 반영되어 있습니다.

1) 답변 스트리밍: 서버가 SSE(text/event-stream)로 토큰을 흘려보내고
   화면에 실시간으로 타이핑되듯 표시됩니다. CPU 추론이라 답변이 느려도
   즉시 반응이 보여 체감이 크게 개선됩니다.
   · 엔드포인트: POST /api/chat/stream

2) 출처 미리보기: 답변 위에 참고한 문서가 카드로 표시되고,
   카드를 클릭하면 해당 문서 조각(스니펫)이 펼쳐집니다.

3) 대화 기억: 브라우저마다 세션ID가 생성되어 최근 대화(기본 8턴)를
   기억합니다. [새 대화] 버튼으로 초기화합니다.
   · 기록은 서버 프로세스 메모리에 저장됩니다. 재시작하면 사라집니다.
     영구 보관이 필요하면 app/chat_engine.py의 _HISTORY를 파일/DB로 교체.

4) 마크다운 렌더링: 굵게, 목록, 표, 코드블록을 지원합니다.
   외부 라이브러리 없이 static/index.html 안의 경량 렌더러로 처리하므로
   폐쇄망에서도 그대로 동작합니다.

관련 파일:
  app/retrieval.py    검색 + 출처 메타데이터
  app/chat_engine.py  스트리밍/기억/커스텀모델 통합 엔진
  app/main.py         SSE 엔드포인트
  static/index.html   스트리밍 수신 + 마크다운 + 출처 UI

----------------------------------------------------------------
## 웹 UI 고도화 (v3)
----------------------------------------------------------------
1) 문서 업로드: 좌측 [＋ 문서 추가]로 웹에서 직접 docs 폴더에 파일 추가.
   업로드 후 [색인 갱신]을 눌러야 검색에 반영됩니다.
   · 엔드포인트: POST /api/upload (지원: pdf/xlsx/xls/pptx/txt/md)

2) 다크 모드: 상단바 ◐ 버튼으로 라이트/다크 전환.
   (세션 동안만 유지. 브라우저 저장은 폐쇄망/보안 고려로 미사용)

3) 답변 복사: 각 답변 아래 [복사] 버튼으로 클립보드 복사.

4) 모델 선택: 상단바 콤보박스에서 사용할 Ollama 모델 선택.
   목록은 Ollama에 pull된 모델을 자동으로 읽어옵니다 (GET /api/models).
   선택한 모델이 다음 질문부터 적용됩니다.

관련 파일:
  app/models_util.py  Ollama 모델 목록 조회 + 업로드 저장
  app/main.py         /api/models, /api/upload 엔드포인트
  app/chat_engine.py  stream_answer(model=...) 로 모델 지정 지원
  static/index.html   업로드/테마/복사/모델선택 UI

----------------------------------------------------------------
## 웹 UI 고도화 (v4)
----------------------------------------------------------------
1) 업로드 시 자동 색인: [＋ 문서 추가]로 파일을 올리면 저장 즉시
   청킹→임베딩→Qdrant 적재까지 자동 수행됩니다. 별도로 [색인 갱신]을
   누를 필요 없이 바로 검색 대상이 됩니다.
   · 같은 파일명을 다시 올리면 기존 벡터를 지우고 새로 적재 (중복 방지).
   · [색인 갱신] 버튼은 폴더 전체 재색인용으로 남아 있습니다
     (반입 절차로 파일을 직접 넣었을 때 사용).
   · 관련: app/ingest.py의 ingest_file(), app/vectorstore.py의
     delete_by_source(), app/main.py의 /api/upload

2) 답변 중단: 스트리밍 중 전송 버튼이 ■(중단)로 바뀝니다. 누르면
   그때까지 생성된 내용은 남기고 즉시 멈춥니다. 중단된 답변도 복사 가능.
   · 클라이언트는 AbortController로 연결을 끊고, 서버는 GeneratorExit로
     생성을 정리합니다.

주의: 자동 색인은 CPU 임베딩(bge-m3)으로 수행되므로, 페이지가 많은 PDF나
큰 엑셀을 올리면 "색인 중…" 상태가 수 초~수십 초 걸릴 수 있습니다.
