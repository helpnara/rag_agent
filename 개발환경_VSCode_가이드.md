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

> ⚠️ **PowerShell ISE는 사용하지 않는다.** ISE는 개발이 중단된 레거시 도구이고,
> 진짜 콘솔 호스트가 없어 **대화형 CLI가 정상 동작하지 않는다**(Claude Code 포함).
> **VS Code 통합 터미널**, Windows Terminal, 또는 일반 PowerShell 콘솔을 쓴다.

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
| `git : Cloning into ...` 가 빨간 오류로 표시됨<br>(`NativeCommandError`) | **오류가 아니다.** git은 진행 상황을 stderr로 출력하는데 PowerShell(특히 ISE)이 이를 오류로 간주해 다시 보여주는 것. `$LASTEXITCODE`가 `0`이면 성공. 진짜 실패는 `fatal:` 로 시작한다. ISE 대신 VS Code 터미널 사용 권장 |
| Claude Code가 실행되지 않거나 화면이 깨짐 | PowerShell ISE에서 실행한 경우. ISE는 대화형 TUI를 지원하지 않는다 → VS Code 통합 터미널에서 실행 |
| 터미널에서 한글·✅ 가 깨짐 | `.vscode/settings.json`이 UTF-8을 강제한다. VS Code를 다시 열면 적용됨 |
| `Activate.ps1` 실행 불가 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| F5 눌러도 인터프리터 못 찾음 | `.venv` / `.venv-demo` 생성 여부 확인 (3장) |
| **`ModuleNotFoundError`** (huggingface_hub, fastapi, streamlit 등) | **가장 흔한 원인은 가상환경 미활성.** 아래 «가상환경 확인» 참고 |
| `ModuleNotFoundError: fastapi` | 데모 환경에서 온프레미스 코드를 실행한 것. 구성을 다시 확인 |
| `ModuleNotFoundError: streamlit` | 반대 경우. `.venv-demo` 사용 구성으로 실행 |
| Streamlit 실행 후 FastAPI가 깨짐 | 두 환경을 섞어 설치한 것. `.venv`를 지우고 3장부터 다시 |
| `Qdrant 연결 실패` (`WinError 10061`) | Docker Qdrant가 안 떠 있는데 설정이 `server` 모드. `.env`에 `QDRANT_MODE=path`를 넣으면 Docker 없이 동작. (`.env`는 gitignore라 clone 후 `copy .env.example .env` 필요) |
| `ImportError: DLL load failed ... 애플리케이션 제어 정책에서 이 파일을 차단했습니다` | **Windows 앱 제어 정책(WDAC/AppLocker/스마트 앱 제어)이 네이티브 DLL을 차단**한 것. 코드 문제가 아니다. → 아래 «네이티브 DLL 차단» 참고 |
| `임베딩 모델 폴더가 없습니다` | `python download_models.py` 실행 |
| Ollama 연결 실패 | 작업 표시줄에서 Ollama 실행 확인, `ollama list` |
| 답변이 매우 느림 | CPU 추론 특성. `qwen2.5:3b`로 교체 |

### 가상환경 확인 (ModuleNotFoundError가 났을 때)

지금 어떤 Python이 실행되는지부터 확인한다.
```powershell
python -c "import sys; print(sys.executable)"
```

| 출력 | 상태 | 대응 |
|------|------|------|
| `...\rag_agent\.venv\Scripts\python.exe` | 온프레미스 환경 활성 | 패키지 설치가 안 끝난 것 → `pip install -r requirements-onprem.txt` |
| `...\rag_agent\.venv-demo\Scripts\python.exe` | 데모 환경 활성 | 온프레미스 코드를 실행했다면 환경을 바꾼다 |
| `C:\Users\...\Python311\python.exe` 등 | **가상환경 비활성** | 아래 활성화 |

```powershell
.\.venv\Scripts\Activate.ps1      # 프롬프트 앞에 (.venv) 가 붙어야 정상
```

**활성화 없이 확실하게 실행하는 방법** — 인터프리터를 직접 지정한다.
```powershell
.\.venv\Scripts\python.exe download_models.py
.\.venv\Scripts\python.exe -m app.ingest
.\.venv-demo\Scripts\python.exe -m streamlit run streamlit_app.py
```
F5 실행 구성과 Tasks는 이 방식을 쓰므로 **활성화 여부와 무관하게 항상 정상 동작**한다.

> 💡 VS Code 터미널은 **인터프리터를 고르기 전에 열어둔 창**에는 가상환경을 적용하지 않는다.
> `Python: Select Interpreter` 후에는 터미널을 닫고 새로 열어야 한다.

### 네이티브 DLL 차단 (`애플리케이션 제어 정책에서 이 파일을 차단했습니다`)

```
ImportError: DLL load failed while importing _xxhash:
             애플리케이션 제어 정책에서 이 파일을 차단했습니다.
```

Windows의 앱 제어 정책(**스마트 앱 제어**, WDAC, AppLocker)이 서명되지 않은
네이티브 확장 모듈(`.pyd`) 로딩을 막을 때 나온다. 파이썬·패키지 문제가 아니다.

**이 프로젝트에서의 대응 (이미 반영됨)**
`xxhash`는 `langsmith`(LangChain 추적 기능)가 끌어오는 의존성인데,
이 프로젝트는 추적 기능을 쓰지 않는다. 그래서 네이티브 의존성이 가장 적은
버전으로 고정해 두었다.
```
langsmith==0.4.31      # 0.5+ : uuid-utils 추가,  0.6.7+ : xxhash 추가
```
이미 설치했다면 최신 버전이 들어가 있을 수 있으니 다시 맞춘다.
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-onprem.txt
.\.venv-demo\Scripts\python.exe -m pip install -r requirements.txt
```

**다른 패키지에서 같은 오류가 난다면**
차단된 파일 경로를 확인하고 아래 중 하나로 대응한다.
1. Windows 보안 → **앱 및 브라우저 컨트롤 → 스마트 앱 제어**가 "켬"이면 "끔"으로 변경
   (한 번 끄면 다시 켤 수 없으니 확인 후 결정)
2. 회사 관리 PC라면 정책상 해제가 불가능할 수 있다 → IT에 해당 파일 허용 요청
3. 이벤트 뷰어 → `Microsoft-Windows-CodeIntegrity/Operational` 에서 차단 기록 확인

---

## 8. 참고

- 온프레미스 상세 절차 → `README.md`
- 폐쇄망 반입 절차 → `README_OFFLINE.md`
- 검증 스크립트 설명 → `tests/README.md`
- Claude Code 공식 문서 → https://code.claude.com/docs
