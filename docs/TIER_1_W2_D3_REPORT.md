# Tier 1 W2 D3 — Planning Agent + Plan Verify (★ 본인 직진 풀)

날짜: 2026-05-02
타입: ★ Layer 2 Stage 2-3 (Planning + Verify) 본격

## 0. 한 줄 요약
자료 2.2 Stage 2-3 정확 구현. Source classification + IP Masking 자동 + 4 항목 검증.

## 1. Phase 1 Source Classification + Planning Prompt
- source_classifier.py: 공식/팬해석/팬픽/미상 4분류 + filter_high_confidence
- prompts.py: PLANNING_PROMPT 추가 (5-section, 자료 2.2)
- test_source_classifier.py: +6 tests

## 2. Phase 2 Planning Agent
- planning.py:
  - MockPlanningAgent (★ Tier 1-2 본격 호출 X)
  - PlanningAgent 본체:
    1. 검색 (W2 D1 어댑터 활용)
    2. 분류 (Phase 1 source_classifier)
    3. ★ IP Masking 자동 재적용 (LLM 누설 회피)
    4. 5-section PLANNING_PROMPT
    5. JSON 추출 (Filter Pipeline) + dataclass 변환
    6. PLAN_REQUIRED_FIELDS 검증
- test_planning.py: +10 tests

## 3. Phase 3 Plan Verify
- plan_verify.py:
  - MockPlanVerifyAgent (★ Tier 1-2)
  - PlanVerifyAgent 본체:
    - check_ip_leakage (★ 가중치 40%, critical)
    - check_world_consistency (20%)
    - check_user_preference_match (20%)
    - check_plan_quality (20%)
    - 가중 평균 + IP 70+ 강제
    - LLM 보조 (옵션, 선택적)
  - DebateJudge 본격 X (Tier 2+ 메모)
- test_plan_verify.py: +12 tests

## 4. Phase 4 State Machine 업데이트 + 통합 E2E
- state_machine.py: apply_plan_result → PlanResult 수용 + 모든 apply 메서드 bool 반환
- test_state_machine.py: 기존 테스트 업데이트 + error 케이스 추가
- test_pipeline_e2e.py: Interview → Planning → Verify Mock E2E (3 integration tests)

## 검증
- ruff: 0 errors ✅
- mypy --strict: 0 errors (57 source files) ✅
- pytest: 500 passed (이전 444 → +56 tests) ✅
- Ship Gate: 100/100 (11번 연속) ✅

## ★ 정책 streak
- 외부 패키지 0건 (★ streak 11번) ✅
- Mock 우선 (★ #14) ✅
- DebateJudge 본격 X (Tier 2+ 메모)

## ★ Tier 1 졸업 진척
- #4 작품명 → 플랜 → 게임:
  - Stage 1 (Interview) ✅ W2 D2
  - Stage 2 (Planning) ✅ W2 D3
  - Stage 3 (Verify) ✅ W2 D3
- 다음 W2 D4-D5: Game Pipeline + 본인 풀 플레이
