# CLAUDE.md — 사내 문서 RAG 에이전트

이 파일은 Claude Code가 이 프로젝트에서 작업할 때 반드시 따라야 할 컨텍스트와 규칙을 정의한다. 작업 전 항상 이 파일을 먼저 읽는다.

---

## 프로젝트 개요

특정 폴더의 사내 문서(PDF, xlsx, pptx, txt, md)를 벡터화하여, 로컬 LLM과 연동한 검색·질의응답이 가능한 웹 기반 RAG 에이전트. 사용자가 개발하는 예측 모델을 Tool Calling으로 연동한다.

상세 요구사항은 `사내문서_RAG_요구사항정의서.md`(SRS)를 참조한다.

---

## 절대 원칙 (위반 금지)

이 프로젝트는 **사내 폐쇄망 + GPU 없는 사무용 PC**에서 운영된다. 아래 제약은 예외 없이 지킨다.

1. **기본 로컬 / 외부는 선택적 옵트인** *(v4.2 개정)*
   - **기본값은 완전 로컬**이며, 온프레미스(로컬) 모드에서는 문서·질의 데이터가 외부로 나가지 않는다.
   - **임베딩은 어떤 모드에서도 항상 로컬 bge-m3**를 쓴다. 외부 임베딩 API는 도입하지 않는다.
   - **LLM만** 외부 API(OpenAI 호환) 모드를 선택적으로 제공한다. 단:
     - 서버 설정(`EXTERNAL_API_KEY`)이 있을 때만 활성화된다. 기본 `LLM_MODE=local`.
     - 외부 모드에서는 질문+문서 컨텍스트가 외부로 전송되므로 UI에 경고를 표시한다.
     - 이 옵트인 구조를 우회해 외부 전송을 기본값으로 만들거나 경고를 제거하지 않는다.
   - 새 라이브러리가 외부 호출을 하는지 확인한다. LLM 외의 목적으로 외부 호출을 추가하지 않는다.

2. **폐쇄망 / 오프라인 동작**
   - 최초 모델 반입 이후 인터넷 없이 동작해야 한다.
   - 임베딩 모델은 로컬 폴더(`./models/bge-m3`)에서만 로드한다. 모델명으로 허브에서 받지 않는다.
   - `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` 설정을 해제하지 않는다.

3. **프론트엔드 외부 리소스 금지**
   - `static/index.html`은 CDN·외부 폰트·외부 JS 라이브러리를 사용하지 않는다.
   - 단일 파일로 자기완결적이어야 한다. 마크다운 렌더러 등은 자체 구현한다.

4. **GPU 없는 CPU 환경 전제**
   - 무거운 모델·연산을 기본값으로 넣지 않는다. LLM 기본은 `qwen2.5:7b`.
   - `DEVICE` 설정(cuda/cpu)으로 전환 가능하게 유지한다. 기본은 cpu 가정.

5. **Windows 실행 호환**
   - 실사용 환경은 Windows다. 경로·명령이 Windows에서 동작하는지 고려한다.

---

## 기술 스택

| 계층 | 기술 |
|------|------|
| 웹 | FastAPI + Uvicorn (REST + SSE 스트리밍) |
| 프론트 | 단일 HTML/CSS/JS (`static/index.html`) |
| 오케스트레이션 | LangChain |
| 벡터DB | Qdrant (로컬 Docker) |
| 임베딩 | bge-m3 (로컬, 1024차원, CPU) — 모드 무관 공통 |
| LLM (로컬) | Ollama (qwen2.5:7b 기본, 사용자 선택) |
| LLM (외부, 선택) | OpenAI 호환 API (langchain-openai) — 옵트인 |
| 로더 | PyMuPDF, openpyxl, python-pptx |

---

## 파일 구조

```
rag-agent-web4/
├─ CLAUDE.md                      # 이 파일
├─ 사내문서_RAG_요구사항정의서.md   # SRS (변경 이력 관리)
├─ README.md / README_OFFLINE.md  # 실행/반입 가이드
├─ requirements.txt
├─ docker-compose.yml             # Qdrant
├─ download_models.py             # [반입PC] bge-m3 다운로드
├─ check_offline.py               # [폐쇄망PC] 준비상태 점검
├─ docs/                          # RAG 대상 문서 폴더
├─ static/
│  └─ index.html                  # 웹 UI (파일패널 + 채팅)
└─ app/
   ├─ config.py         # 설정 (모델경로, 청크크기, DEVICE 등)
   ├─ loaders.py        # 형식별 문서 로더 + LOADERS 확장자맵
   ├─ vectorstore.py    # Qdrant + bge-m3 임베딩, delete_by_source()
   ├─ retrieval.py      # 검색 + 출처 메타데이터 반환
   ├─ ingest.py         # run()=전체적재, ingest_file()=단일적재
   ├─ chat_engine.py    # 스트리밍/대화기억/커스텀모델 통합 엔진
   ├─ my_model.py       # ★사용자 예측 모델 자리 (predict())
   ├─ models_util.py    # 로컬/외부 모델목록 조회 + 업로드 저장
   ├─ files.py          # docs 폴더 파일목록 조회
   └─ main.py           # FastAPI 엔드포인트
```

---

## 주요 엔드포인트

| 메서드 | 경로 | 기능 |
|--------|------|------|
| GET | `/` | 웹 UI |
| GET | `/api/files` | docs 파일 목록 |
| GET | `/api/models` | 모드별 모델 목록(로컬/외부) + 기본 모드 |
| POST | `/api/upload` | 문서 업로드 + 자동 색인 |
| POST | `/api/chat/stream` | SSE 스트리밍 답변 (`mode`로 로컬/외부 지정) |
| POST | `/api/chat/reset` | 세션 대화 초기화 |
| POST | `/api/ingest` | 폴더 전체 재색인 |

---

## 실행 방법

```bash
# 개발/테스트 (인터넷 되는 환경)
pip install -r requirements.txt
docker compose up -d          # Qdrant
python -m app.ingest          # docs 색인
uvicorn app.main:app --reload # http://localhost:8000
```

폐쇄망 반입·설치는 `README_OFFLINE.md`를 따른다.

---

## 작업 규칙

### 요구사항 정의서 자동 갱신 (중요)
기능을 추가/변경할 때마다 **반드시** `사내문서_RAG_요구사항정의서.md`를 함께 갱신한다.
- 새 기능은 해당 분류에 `FR-`/`NFR-` ID를 부여해 표에 추가한다.
- 문서 하단 **7장 변경 이력** 표에 새 버전과 변경 내용을 기록한다.
- 현재 최신 버전: **v4.2**

### 코드 스타일
- 주석·문서·UI 텍스트는 한국어를 기본으로 한다.
- 기존 파일 구조와 명명 규칙을 따른다. 큰 리팩터링 전에는 이유를 설명한다.
- 새 의존성 추가 시 외부 호출 여부를 확인하고 `requirements.txt`에 버전 고정.

### 사용자 예측 모델 연동
`app/my_model.py`의 `predict()`가 사용자 모델 자리다. 지금은 데모(제곱+상수)이며,
실제 모델 연결 시 입력 시그니처가 바뀌면 `chat_engine.py`의 호출부와
`agent.py`(에이전트 버전)의 도구 정의도 함께 수정한다.

---

## 보류·예정 과제 (Backlog)

작업 지시가 있을 때 아래를 참고한다. 임의로 먼저 구현하지 않는다.

- **BL-01 (대화기억 영구보관)**: 현재 대화기록은 `chat_engine.py`의 `_HISTORY`
  (서버 메모리)에 저장되어 재시작 시 소실. 요청 시 파일/DB로 교체.
- **BL-02 (브라우저 테마·세션 저장)**: 현재 다크모드는 세션 동안만 유지, 새로고침 시
  초기화. 요청 시 localStorage 등으로 저장. (단, 폐쇄망 보안 검토 후 도입)
- **FR-TOOL-04 (로컬 모델 Tool Calling 안정성)**: docstring 정교화, 재시도 처리.
- **BL-03 (답변 중단 시 서버측 생성 즉시 중지 검증)**: 현재 GeneratorExit로 정리하나
  Ollama 생성이 실제로 멈추는지 검증 필요.

---

## 하지 말아야 할 것 (요약)

- ❌ 외부 API로 **임베딩** 호출 추가 (임베딩은 항상 로컬 bge-m3)
- ❌ 외부 LLM 모드를 기본값으로 강제하거나 외부 전송 경고 제거 (외부는 옵트인)
- ❌ 프론트에 CDN·외부 라이브러리 도입
- ❌ 오프라인 강제 환경변수 해제
- ❌ 요구사항 정의서 갱신 없이 기능만 추가
- ❌ GPU 전제의 무거운 기본값 설정
