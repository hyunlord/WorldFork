# Tier 1 W2 D2 Report — Interview Agent 본격

날짜: 2026-05-02

## 산출물

### Phase 1: Intent Classifier
- `service/pipeline/intent_classifier.py`
  - `IntentClassification` dataclass (intent, confidence, detected_features, reason)
  - `IntentClassifier.classify()` — rule-based, 외부 패키지 0건
  - 키워드: INTENT_KEYWORDS_KO(14), ENTRY_KEYWORDS_KO(13), WORK_PATTERNS(15), OFF_TOPIC_KEYWORDS(14)
  - 로직: work+intent→clear(0.9), 5단어+work→clear(0.6), ≤4단어→ambiguous(0.9), off_topic 감지
- `tests/unit/test_intent_classifier.py` — 17 tests ✅

### Phase 2: Prompts + Question Generator
- `service/pipeline/prompts.py`
  - `INTERVIEW_PROMPT` — 5-section (IDENTITY/TASK/SPEC/OUTPUT FORMAT/EXAMPLES)
  - `build_interview_prompt(user_input)` — 사용자 입력 포함 프롬프트
- `service/pipeline/question_generator.py`
  - `MockQuestionGenerator` — 기본 3-질문 (LLM 없이)
  - `QuestionGenerator` — LLM + JSON 배열 추출, 실패 시 Mock fallback
  - `_extract_string_array()` — `[...]` regex + json.loads
  - `LLMClient` Protocol — duck-typing
- `tests/unit/test_question_generator.py` — 18 tests ✅

### Phase 3: Interview Agent + State Machine
- `service/pipeline/interview.py`
  - `InterviewAgent.run()` — clear→skip, ambiguous→questions, off_topic→guide
  - `InterviewSessionResult` — classification + question_generation 메타 포함
- `service/pipeline/state_machine.py`
  - `PipelineStateMachine` — 8-stage forward-only
  - `advance_to()`, `advance()`, `apply_interview_result()`, `apply_plan_result()`, `apply_plan_verify()`
  - STAGES: interview→planning→verify→review→agent_select→verify_select→game_loop→complete
- `tests/unit/test_interview.py` — 12 tests ✅
- `tests/unit/test_state_machine.py` — 19 tests ✅

## 지표

| 항목 | 값 |
|------|-----|
| 신규 파일 | 8개 |
| 신규 테스트 | 66개 (+17+18+12+19) |
| 전체 테스트 | 444 passed |
| Ship Gate | 100/100 (A) |
| 외부 패키지 추가 | 0건 |
| mypy --strict | ✅ |
| ruff | ✅ |

## 설계 결정

- **FilterPipeline 미사용**: STANDARD_FILTER_PIPELINE은 dict 전용; 질문 배열용 `_extract_string_array()` 별도 구현
- **LLMClient Protocol**: duck-typing으로 mypy --strict 호환 + 실제 클라이언트 교체 용이
- **Mock fallback 최우선**: Tier 1에서 LLM 없이도 전 기능 동작
- **apply_plan_verify 실패 처리**: verify 단계 유지 (재시도는 호출자 책임 — YAGNI)
