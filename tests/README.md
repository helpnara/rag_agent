# tests — 이중 모드 · 데모 구성 검증

Ollama · Qdrant · 외부 API **없이** 동작을 검증한다.
목(mock) Ollama·OpenAI 호환 서버를 띄워 실제 HTTP 스트리밍 경로를 그대로 태운다.
목 서버는 **표준 라이브러리만** 쓰므로 온프레미스/데모 두 환경에서 모두 돌아간다.

## 실행

```bash
# 1) LLM 이중 모드 (온프레미스 환경: requirements-onprem.txt)
python tests/verify_llm_modes.py

# 2) 데모 구성 — fastembed + 메모리 Qdrant + 외부 LLM (데모 환경: requirements.txt)
python tests/verify_demo_rag.py

# 3) 브라우저로 FastAPI UI 직접 확인 (온프레미스 환경)
python tests/serve_mock.py            # 외부 API 정상 설정
python tests/serve_mock.py --no-key   # 외부 미설정 → 외부 옵션 비활성화
python tests/serve_mock.py --bad-key  # 잘못된 키 → 오류 표시
# → http://127.0.0.1:18080
```

각 스크립트는 통과/실패 요약을 출력하고 실패 시 exit 1을 반환한다.

`verify_demo_rag.py`는 실제 fastembed 모델을 우선 시도하고, 모델을 내려받을 수
없는 환경(폐쇄망·CI)에서는 **결정적 스텁 임베딩으로 자동 대체**한다. 이때도
색인·검색·스트리밍 배선은 동일하게 검증되지만 임베딩 품질은 검증 대상이 아니며,
출력 마지막 줄에 어느 쪽으로 돌았는지 표시된다.

## 검증 범위

| 구분 | 확인 내용 | 관련 요구사항 |
|------|-----------|----------------|
| 모델 목록 | 로컬=Ollama `/api/tags`, 외부=OpenAI 호환 `/models` | FR-LLM-05 |
| 로컬 모드 | 스트리밍 정상, **외부 API 호출 전혀 없음** | NFR-SEC-01 |
| 외부 모드 | 스트리밍 정상, 질문·문서 컨텍스트가 실제로 전송됨(경고 문구의 사실성) | FR-LLM-01 |
| 모드 지정 | 요청별 `mode`·모델 지정, 미지정 시 서버 기본값 | FR-LLM-02 |
| 오류 처리 | 잘못된 키(401)·연결 실패·키 미설정 → error 이벤트 반환, 크래시 없음 | FR-LLM-03 |
| 호환성 | 자체 호스팅 OpenAI 호환 엔드포인트, base_url 끝 슬래시 | FR-LLM-04 |
| 회귀 | 출처 표시, 대화기억 | FR-CHAT-03/06 |
| 데모 구성 | fastembed 384차원, 메모리 Qdrant 색인, 검색, 외부 스트리밍 | FR-DEMO-01~05 |
| 데모 회귀 | 환경변수 없으면 온프레미스 기본값(bge-m3·server·local) 유지 | NFR-SEC-01 |

## 주의

- 목 서버는 `127.0.0.1:18000`(OpenAI 호환), `127.0.0.1:18434`(Ollama), UI는 `18080`을 쓴다.
  포트가 이미 사용 중이면 먼저 떠 있는 목 서버를 종료한다.
- 실제 Ollama/외부 API 연동 최종 확인은 운영 환경에서 한 번 더 수행한다.
- 온프레미스와 데모는 **의존성이 충돌**하므로(Streamlit ↔ FastAPI의 starlette 버전)
  가상환경을 분리해서 실행한다.
