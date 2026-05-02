# Tier 1 W2 D4 — Game Pipeline (★ 본인 직진 풀)

날짜: 2026-05-02
타입: ★ Layer 2 Stage 5-7 본격

## 0. 한 줄 요약
Plan → GameState → GM Agent → Game Loop. Layer 1 자산 (Mechanical 10룰 + dynamic_token_limiter) 활용.

## 1. Phase 1 Plan → GameState
- service/game/init_from_plan.py
  - Plan의 main + supporting → Character dict
  - opening_scene → location 추출 (키워드 휴리스틱)
  - build_game_context: GM Agent용 풍부 컨텍스트
- test_init_from_plan.py: +12 tests

## 2. Phase 2 Agent Selection (★ 자료 Stage 5-6)
- service/pipeline/agent_selection.py
  - TIER_CANDIDATES (tier_1: qwen35-9b-q3 / qwen36-27b-q2)
  - select_game_llm: cheap / balanced / premium
  - select_verify_llm: ★ Cross-Model 강제 (game ≠ verify)
  - select_agents: 통합 페어 선택
- test_agent_selection.py: +5 tests

## 3. Phase 3 GM Agent + Game Loop
- service/game/gm_agent.py:
  - Plan + State 컨텍스트 → _gm_system_prompt
  - compute_max_tokens (★ Layer 1 dynamic_token_limiter)
  - MechanicalChecker (★ Layer 1 10 룰)
  - MockGMAgent + GMAgent 본체
- service/game/game_loop.py (★ 자료 Stage 7):
  - classify_action: rule-based (combat/explore/dialogue/...)
  - Retry max 3 (Layer2Policy)
  - Fallback message
  - Game state 자동 업데이트
- test_gm_agent.py: +8 tests
- test_game_loop.py: +10 tests

## 4. Phase 4 통합 E2E
- tests/integration/test_pipeline_full.py
  - Interview → Plan → Verify → State → GameLoop
  - 3 turn 시뮬 검증
- +2 tests

## 검증
- ruff: 0 errors ✅
- mypy --strict: 0 errors (61 source files) ✅
- pytest: 541 passed (+41 vs D3) ✅
- Ship Gate: 100/100 (★ 12번 연속) ✅

## ★ 정책 streak
- 외부 패키지 0건 (★ streak 12번) ✅
- Mock 우선 (★ #14) ✅

## ★ Tier 1 졸업 진척
- #4 Pipeline 8단계 중 5단계 완료:
  - Stage 1 (Interview) ✅ W2 D2
  - Stage 2 (Planning) ✅ W2 D3
  - Stage 3 (Verify) ✅ W2 D3
  - Stage 5 (Agent Select) ✅ W2 D4
  - Stage 7 (Game Loop) ✅ W2 D4
- 다음 W2 D5: ★ 본인 1회 풀 플레이
