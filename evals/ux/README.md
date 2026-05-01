# UX Eval Category

Tier 1 W1 D7 추가. WorldFork UX 검증.

## 카테고리 매핑

`tools/ai_playtester/seed_converter.py::CATEGORY_MAPPING`:
- `ux`, `ui`, `broken_ux` → ux
- `clarity`: 응답이 명확하지 않음
- `pacing`: 페이싱이 너무 빠름/느림
- `navigation`: 사용자가 어디로 가야 할지 모름
- `too_many_choices`: 선택지 과다 (선택 마비)
- `onboarding`: 첫 진입 지원 부족
- `feedback`, `help`: 피드백/도움말 부족
- `repetitive_intro`: 반복적 인트로
- `fun`: 재미 결함

## Expected Behavior

`EXPECTED_BEHAVIORS_BY_CATEGORY["ux"]`:
- `clear_choices: True` — 명확한 행동 선택지
- `no_navigation_loss: True` — 어디로 가야 할지 알 수 있음
- `appropriate_pacing: True` — 페이싱 적절

## 시드 출처

W1 D7 옵션 A: W1 D6 Round 4 finding 재변환에서 자동 채워짐.
본인 검토 후 `v_next.jsonl` 채택, baseline 회귀 검증.
