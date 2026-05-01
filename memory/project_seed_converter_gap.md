---
name: seed_converter 자료 5.2 미적용
description: seed_converter.py가 자료 AI_PLAYTESTER 5.2를 부분만 적용. W1 D6 재구현 예정.
type: project
---

seed_converter.py는 자료 AI_PLAYTESTER 5.2 부분 적용 상태임.

**문제:**
- 자료 5.2: `prompt` = target_turn의 실제 user_input (재현 프롬프트)
- 현재: `prompt.user` = `finding.description` (발견 설명문 — 재현 프롬프트 아님)
- 자료 5.2: `expected_behavior` = 카테고리별 구체적 기준
- 현재: `expected_behavior` = `{"avoid_issue": True}` (너무 모호)

**근본 원인:** PlaytesterRunner playthrough_log가 단순화 (game_intro + playtester_summary 2개만). 자료 5.2는 turn별 user_input/game_response 필요.

**Why:** 자료 5.3 검토 시 10개 auto_added 시드를 직접 검토했으나, 시드 자체가 자료 5.2 위반이라 검토 의미 없어 작업 6-7 중단.

**How to apply:** W1 D6에서 PlaytesterRunner 본격 게임 루프(turn별 기록) 구현 후 seed_converter 자료 5.2 정확 재구현. 그때 본인 검토 의미 있음. evals/auto_added/ 현재 시드는 참고용으로만 유지.
