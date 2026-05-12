# F8 post-EXIT prompt — 9연속 정공법 마무리

## 본 commit (★ F8)

본 commit은 F7 잔여 finding (post-EXIT ENTER_RIFT 6/19 fail) 답.

## F7 잔여 finding 본격 진단 (★ 본 commit 출발점)

F7 trace 본격 EXIT 후 ENTER_RIFT 본격 본격 분석:

| EXIT @ turn | 직후 시퀀스 | 결과 |
|---|---|---|
| 13 | MOVE → ATTACK → FLEE → ... | (★ ENTER 본격 X — 정상 본격) |
| 39 | FLEE → **ENTER FAIL** → OFFER → ATTACK → ENTER OK | (★ 1 fail) |
| 59 | OFFER OK → ATTACK → ENTER OK | (★ 모범 순서) |
| 69 | **OFFER FAIL (target='마석')** → ATTACK → **ENTER FAIL** | (★ table 본격 prompt 본격 본격) |

**Root cause** (★ F8 진단):
1. EXIT 후 active_rifts 비움 본격 — 그러나 LLM 본격 prompt 본격 본격 본격 X
2. system prompt table 본격 `offer_to_stone | target: 마석 등급` 본격 본격
   → LLM이 target='마석' 본격 호출 → fail (★ rift name 본격)
3. F6 prompt 본격 본격 X — recent EXIT 본격 본격 본격

## F7 → F8 RIFT phase 본격 비교 (★ 실측)

| 항목 | F7 | F8 | 변화 |
|------|-----|-----|------|
| completed_turns | 90 | 84 | -6 |
| end_reason | time_limit_168h | time_limit_168h | — |
| ENTER_RIFT | 19 | 14 | -26% (★ 무의미 시도 본격) |
| **ENTER success** | **13/19 (68%)** | **13/14 (93%)** | **★ +25%p** |
| **EXIT_RIFT** | **4** | **10** | **★ +150% (사이클 2.5x)** |
| **EXIT success** | **4/4 (100%)** | **10/10 (100%)** | 유지 |
| **OFFER_TO_STONE** | 6 | 11 | **★ +83% (post-EXIT 활성화)** |
| **OFFER success** | **5/6 (83%)** | **11/11 (100%)** | **★ +17%p (table 본격 답)** |
| ATTACK | 22 | 23 | +1 |
| EXPLORE | 2 | 3 | +1 |
| FLEE | 31 | 20 | -35% |
| MOVE | 4 | 1 | -3 |
| rift_entered | True | True | — |
| rift_exited | True | True | — |
| player_fallback | 0 | [0] | — |
| gm_fallback | 0 | [0] | — |

## 본격 변경 (★ F8 본 commit)

### 1. service/sim/player_agent.py — prompt 본격 본격

- **`PLAYER_AGENT_SYSTEM_PROMPT`** 본격:
  * 균열 사이클 5단계 본격 명시:
    1. OFFER_TO_STONE → world.active_rifts 등록
    2. ENTER_RIFT → 균열 안 진입
    3. ATTACK / EXPLORE / ABSORB (균열 안 행동)
    4. EXIT_RIFT → 1층 복귀 (★ active_rifts에서 제거됨)
    5. 다시 OFFER_TO_STONE → ENTER_RIFT
  * EXIT 직후 ENTER_RIFT 호출 금지 본격 명시
  * ActionType table 본격 offer_to_stone target 본격:
    * 본격: '마석 등급' → '균열 이름 (예: "핏빛성채")'

- **`_build_player_prompt`** 본격 recent_exit 검출:
  * `last_actions[-3:]` 본격 `"exit_rift"` 검출
  * active_rifts empty + recent_exit 본격 강한 경고:
    * '방금 EXIT_RIFT — active_rifts 비움'
    * 'OFFER_TO_STONE으로 새 균열 활성화 먼저 (★ target=균열 이름)'
    * 'ENTER_RIFT 다시 호출 X (★ success=False)'
  * 일반 empty 본격 기존 F6 경고 유지

### 2. tests/unit/test_player_agent_prompt_v2.py — 5 신규 tests

- `test_build_prompt_post_exit_empty_strong_warning` — 강한 경고 본격
- `test_build_prompt_no_recent_exit_normal_warning` — 일반 경고 본격 (★ F6 패턴 유지)
- `test_build_prompt_active_rifts_with_recent_exit` — active 본격 본격 정상 본격
- `test_system_prompt_rift_cycle_sequence` — 사이클 5단계 명시 본격
- `test_system_prompt_offer_target_is_rift_name` — '균열 이름' 본격, '마석 등급' X

## 본인 #19 정공법 9연속 본격 마무리 ✅

- F1: 'resolution' → 위치스램프 누락 (★ data fix)
- F2: '데미지' → resolution 작동 (★ prompt)
- F3: 'dominance' → phase 정합 (★ data)
- F4: 'spawn' → essence color alias (★ data)
- F5: 'spam' → prompt slot 인지 (★ prompt)
- F5b: 'SimHarness.from_default' → SimRunner + SimConfig (★ harness)
- F6: 'EXIT_RIFT 미발현' → 'active_rifts empty' → prompt + alias bridge (★ prompt + data)
- F7: 'EXIT_RIFT 0' → 'location.realm 변경 X' → mechanism + prompt (★ mechanism + prompt)
- **F8**: 'post-EXIT ENTER fail' → 'recent_exit prompt + offer target table' → prompt only (★ prompt)

= **9연속 모두 prompt/data/mechanism fix**
= mechanism 변경 1회 (★ F7 location.realm)
= 추측 X 실측 답 본격
= **균열 사이클 완전 마무리**: ENTER + EXIT + post-EXIT ✅

## 본 사이클 완전 마무리

- 1층 안정화: 13/13 ✅
- Phase 6 시각화: 7/7 ✅
- 9연속 정공법: F1-F8 ✅
- 균열 mechanic: ENTER + EXIT + post-EXIT ✅
- success rate: ENTER 93%, EXIT 100%, OFFER 100% ✅

## 본 commit 후

본인 결정 (★ weekly limit 본격):
- Phase 7 동적 사이클 (★ 후속 사이클)
- 본격 마무리 (★ 본 commit 충분)
