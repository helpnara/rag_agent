# VS Code + Claude Code 개발환경 구성 가이드

내 PC(Windows)에서 이 프로젝트를 열고, **테스트를 실행하면서 Claude Code와 대화로 과제를 이어가기** 위한 절차다.
저장소에 `.vscode/` 설정이 포함되어 있어 대부분 자동으로 잡힌다.

---

## 0. 전체 그림

```
VS Code
├─ .venv        (온프레미스: FastAPI + Ollama + bge-m3)   ← 기본
├─ .venv-demo   (데모: Streamlit + fastembed)             ← 별도
├─ F5 / Tasks   실행·디버그·검증 구성 (.vscode/)
└─ Claude Code  터미널에서 대화하며 코드 수정·검증
```

> ⚠️ 가상환경 2개는 **반드시 분리**한다. Streamlit과 FastAPI는 starlette 버전이 충돌한다.

---

## 1. 사전 설치 (한 번만)

| 항목 | 확인 명령 | 비고 |
|------|-----------|------|
| VS Code | — | https://code.visualstudio.com |
| Python **3.11** | `py -3.11 --version` | 3.13은 일부 패키지 미지원 |
| Git | `git --version` | https://git-scm.com |
| Node.js 18+ | `node --version` | Claude Code 설치에 필요 |
| Ollama | `ollama --version` | 온프레미스 LLM용 |

---

## 2. 저장소 열기

```powershell
git clone https://github.com/helpnara/rag_agent.git
cd rag_agent
code .
```

VS Code가 열리면 우측 하단에 **"권장 확장을 설치하시겠습니까?"** 알림이 뜬다 → **설치**를 누른다.
(Python, Debugpy, Claude Code 확장이 설치된다. 알림을 놓쳤다면
`Ctrl+Shift+X` → 검색창에 `@recommended` 입력)

---

## 3. 가상환경 만들기

VS Code 터미널(`Ctrl+``)에서:

```powershell
# 1) 온프레미스용 (기본)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-onprem.txt      # torch 포함, 10분 이상 소요

# 2) 데모용 (별도)
deactivate
py -3.11 -m venv .venv-demo
.\.venv-demo\Scripts\Activate.ps1
pip install -r requirements.txt
```

> `Activate.ps1` 실행이 차단되면 PowerShell에서 한 번만:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 인터프리터 선택
`Ctrl+Shift+P` → **Python: Select Interpreter** → `.venv` 선택.
데모 코드를 편집할 때만 `.venv-demo`로 바꾼다.
(F5 실행 구성은 각자 올바른 환경을 지정하므로, 선택과 무관하게 정상 동작한다.)

---

## 4. 모델·설정 준비 (온프레미스)

```powershell
ollama pull qwen2.5:7b          # CPU라 느리면 qwen2.5:3b
python download_models.py       # bge-m3 (약 2GB)
copy .env.example .env
```

`.env`에서 Docker 없이 쓰려면 한 줄만 수정:
```
QDRANT_MODE=path
```

---

## 5. 실행하기

### F5 (디버그 실행)
좌측 **실행 및 디버그** 패널에서 구성을 고르고 F5:

| 구성 | 설명 |
|------|------|
| 온프레미스: FastAPI 서버 | http://localhost:8000 |
| 온프레미스: 준비 상태 점검 | 부족한 항목과 해결법 출력 |
| 온프레미스: 문서 색인 | `docs/` 폴더 색인 |
| 검증: LLM 이중 모드 | Ollama·API 없이 32항목 검증 |
| 검증: 목 서버로 웹UI 확인 | 모델 없이 화면만 확인 |
| 데모: Streamlit 실행 | http://localhost:8501 |
| 검증: 데모 RAG 구성 | 데모 경로 20항목 검증 |

중단점을 찍고 F5로 돌리면 그대로 디버깅된다.

### Tasks (디버거 없이 빠르게)
`Ctrl+Shift+P` → **Tasks: Run Task** → 원하는 항목.
`검증: 전체`를 고르면 온프레미스·데모 검증을 순서대로 돌린다.

### 권장 첫 실행 순서
```
1. 검증: 목 서버로 웹UI 확인   ← 모델 없이 화면부터 확인
2. 온프레미스: 준비 상태 점검   ← 전 항목 통과까지 해결
3. 온프레미스: 문서 색인
4. 온프레미스: FastAPI 서버
```

---

## 6. Claude Code 연동

### 설치
```powershell
npm install -g @anthropic-ai/claude-code
```

### 실행
VS Code 통합 터미널에서 **프로젝트 폴더 안에서**:
```powershell
claude
```
첫 실행 시 로그인 안내가 나온다. VS Code 통합 터미널에서 실행하면
확장과 연결되어 편집 중인 파일·선택 영역이 대화에 함께 전달된다.

### 이 프로젝트가 Claude Code와 잘 맞물리는 이유
`CLAUDE.md`가 저장소 루트에 있어 **대화 시작 시 자동으로 읽힌다.**
여기에 절대 원칙(로컬 우선·폐쇄망·CPU 전제), 파일 구조, 작업 규칙이 정리되어 있어
매번 설명하지 않아도 맥락이 유지된다.

함께 읽히면 좋은 문서:
| 파일 | 내용 |
|------|------|
| `CLAUDE.md` | 지켜야 할 원칙과 구조 (자동 로드) |
| `개발_진행상황.md` | 일자별 작업 내역 + 다음 할 일 |
| `사내문서_RAG_요구사항정의서.md` | 요구사항 ID와 변경 이력 |
| `tests/README.md` | 검증 방법 |

### 첫 대화 예시
```
개발_진행상황.md 읽고 지금 상태와 다음 할 일 정리해줘.
```
```
A2 항목부터 진행하려고 해. 지금 환경에서 실행 순서 알려줘.
```

### 작업 흐름 권장
1. **변경 요청** → Claude Code가 코드 수정
2. **검증 실행** → `Tasks: 검증: 전체` 또는 F5 (직접 눈으로 확인)
3. **문서 갱신** → 기능이 바뀌면 SRS·진행상황도 함께 갱신하도록 요청
4. **커밋** → 검증이 통과한 뒤에 커밋

> 이 프로젝트 규칙상 **기능을 바꾸면 `사내문서_RAG_요구사항정의서.md`도 함께 갱신**한다.
> Claude Code에게 "요구사항정의서도 같이 갱신해줘"라고 말하면 된다.

### 권한 프롬프트 줄이기
Claude Code는 명령 실행 전 승인을 묻는다. 자주 쓰는 명령(예: 검증 스크립트)은
설정에서 허용 목록에 넣어두면 매번 묻지 않는다.
자세한 내용은 공식 문서를 참고한다 → https://code.claude.com/docs

---

## 7. 자주 겪는 문제

| 증상 | 원인 / 해결 |
|------|-------------|
| 터미널에서 한글·✅ 가 깨짐 | `.vscode/settings.json`이 UTF-8을 강제한다. VS Code를 다시 열면 적용됨 |
| `Activate.ps1` 실행 불가 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| F5 눌러도 인터프리터 못 찾음 | `.venv` / `.venv-demo` 생성 여부 확인 (3장) |
| `ModuleNotFoundError: fastapi` | 데모 환경에서 온프레미스 코드를 실행한 것. 구성을 다시 확인 |
| `ModuleNotFoundError: streamlit` | 반대 경우. `.venv-demo` 사용 구성으로 실행 |
| Streamlit 실행 후 FastAPI가 깨짐 | 두 환경을 섞어 설치한 것. `.venv`를 지우고 3장부터 다시 |
| `임베딩 모델 폴더가 없습니다` | `python download_models.py` 실행 |
| Ollama 연결 실패 | 작업 표시줄에서 Ollama 실행 확인, `ollama list` |
| 답변이 매우 느림 | CPU 추론 특성. `qwen2.5:3b`로 교체 |

---

## 8. 참고

- 온프레미스 상세 절차 → `README.md`
- 폐쇄망 반입 절차 → `README_OFFLINE.md`
- 검증 스크립트 설명 → `tests/README.md`
- Claude Code 공식 문서 → https://code.claude.com/docs
