# tests — LLM 이중 모드 검증

Ollama · Qdrant · 외부 API **없이** 로컬/외부 모드 분기를 검증한다.
목(mock) Ollama·OpenAI 호환 서버를 띄워 실제 HTTP 스트리밍 경로를 그대로 태우고,
임베딩·벡터DB는 모드 분기와 무관하므로 `app.retrieval`을 스텁으로 대체한다.

## 실행

```bash
# 자동 검증 (권장) — 통과/실패 요약 출력, 실패 시 exit 1
python tests/verify_llm_modes.py

# 브라우저로 직접 확인
python tests/serve_mock.py            # 외부 API 정상 설정
python tests/serve_mock.py --no-key   # 외부 미설정 → 외부 옵션 비활성화
python tests/serve_mock.py --bad-key  # 잘못된 키 → 오류 표시
# → http://127.0.0.1:18080
```

추가 의존성은 없다(`requirements.txt`의 fastapi·uvicorn·langchain-* 만 사용).

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

## 주의

- 목 서버는 `127.0.0.1:18000`(OpenAI 호환), `127.0.0.1:18434`(Ollama), UI는 `18080`을 쓴다.
- 실제 Ollama/외부 API 연동 최종 확인은 운영 환경에서 한 번 더 수행한다.
