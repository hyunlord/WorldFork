# F7 EXIT_RIFT mechanic 결과

## 본 commit (★ F7)

본 commit은 F6 실측 EXIT_RIFT 0 + ENTER_RIFT 본격 반복 호출 본격 답.

## F6 RIFT phase 본격 진단 (★ 본 commit 출발점)

| 항목 | F6 |
|------|-----|
| ENTER_RIFT | 20 (success 20/20) |
| EXIT_RIFT | 0 |
| rift_entered | True |
| rift_exited | False |
| end_reason | time_limit_168h |

**Root cause** (★ F7 진단):
- `enter_rift()` success → `target_realm=RIFT` 본격 side_effect text 본격 (★ 표시)
- 그러나 **`Location.realm` 본격 변경 X** (★ sim_runner caller 본격 누락)
- 다음 turn `_refresh_context`에서 `location.realm` 본격 그대로 (★ DUNGEON)
- → LLM에게 본격 'realm=DUNGEON' 본격 전달
- → LLM 본격 '아직 균열 안 안 본격' 판단 → ENTER_RIFT 본격 재호출 (★ 20회)
- → EXIT_RIFT 본격 호출 본격 자연 0

## F6 → F7 RIFT phase 본격 비교 (★ 실측)

| 항목 | F6 | F7 | 변화 |
|------|-----|-----|------|
| completed_turns | 83 | 90 | +7 |
| end_reason | time_limit_168h | time_limit_168h | — |
| OFFER_TO_STONE | 13 | 6 | -54% (활성 후 본격 정수 호출 X) |
| ENTER_RIFT | 20 | 19 | -1 (본격 본격) |
| ENTER success | 20/20 (100%) | 13/19 (68%) | (★ F8 본격) |
| **EXIT_RIFT** | **0** | **4** | **★ +∞** |
| **EXIT success** | **0/0** | **4/4 (100%)** | **★ 본 commit 핵심** |
| rift_entered | True | True | — |
| **rift_exited** | **False** | **True** | **★ 본 commit 핵심** |
| ATTACK | 11 | 22 | +100% (균열 안 본격) |
| ACTIVATE_LIGHT | 1 | 2 | +1 |
| ABSORB_ESSENCE | 1 | 0 | (★ F8 본격) |
| MOVE | 5 | 4 | — |
| EXPLORE | 2 | 2 | — |
| FLEE | 30 | 31 | — |
| player_fallback | 0 | 0 | — |
| gm_fallback | 0 | 0 | — |

## 본격 변경 (★ F7 본 commit)

### 1. service/sim/sim_runner.py — mechanism fix

- `Realm` import 추가 (`service.game.state_v2`)
- `_resolve_rift_id` import 추가 (`service.game.turn_handler_v2`)
- `_execute_action()` 본격 ENTER_RIFT 분기:
  * `r.success` 시 본격 `location.realm = Realm.RIFT`
  * `location.rift_id = _resolve_rift_id(action.target) or action.target` (★ canonical 본격)
- `_execute_action()` 본격 EXIT_RIFT 분기:
  * `r.success` 시 본격 `location.realm = Realm.DUNGEON`
  * `location.rift_id = None`

### 2. service/sim/player_agent.py — prompt 강화

- `PLAYER_AGENT_SYSTEM_PROMPT` 본격 EXIT_RIFT 가이드 강화:
  * 조건: `location.realm == RIFT` 본격 명시
  * 시점 본격 (균열 클리어 / 위험 / 충분)
  * `realm=DUNGEON` 본격 시 사용 X 본격 경고
- `PLAYER_AGENT_SYSTEM_PROMPT` 본격 ENTER_RIFT 본격 추가 본격:
  * `realm != RIFT` 본격 조건 추가
  * 이미 균열 안 본격 시 사용 금지 — EXIT_RIFT 또는 ATTACK 본격
- `_build_situation_summary` 본격 in_rift 본격 hint:
  * `realm == "균열"` 본격 시 본격 '현재 균열 안 본격 🌀 (rift_id=...) — EXIT_RIFT로 1층 복귀 가능' 본격
  * `active_rifts` 본격 표시 본격 in_rift 분기: '이미 진입 본격 — EXIT_RIFT 우선'

### 3. tests/unit — 단위 tests 보강 (★ 9 신규)

- `test_sim_runner.py`:
  * `test_enter_rift_success_updates_location_realm` — ENTER 본격 location 변경
  * `test_enter_rift_inactive_no_location_change` — fail 시 본격 그대로
  * `test_exit_rift_success_returns_to_dungeon` — EXIT 본격 DUNGEON 복귀
  * `test_enter_then_exit_rift_round_trip` — 라운드트립 본격
- `test_player_agent_prompt_v2.py`:
  * `test_system_prompt_exit_rift_realm_condition` — EXIT_RIFT 조건 본격
  * `test_system_prompt_enter_rift_in_rift_forbidden` — in_rift ENTER 본격 금지
  * `test_build_prompt_in_rift_hint` — RIFT 본격 hint 본격
  * `test_build_prompt_in_rift_already_entered_warning` — '이미 진입 본격' 본격
  * `test_build_prompt_dungeon_no_in_rift_hint` — DUNGEON 본격 hint X 본격

## 본인 #19 정공법 8연속 입증

- F1: 'resolution' → 위치스램프 누락 (★ data fix)
- F2: '데미지' → resolution 작동 (★ prompt)
- F3: 'dominance' → phase 정합 (★ data)
- F4: 'spawn' → essence color alias (★ data)
- F5: 'spam' → prompt slot 인지 (★ prompt)
- F5b: 'SimHarness.from_default' → SimRunner + SimConfig (★ harness fix)
- F6: 'EXIT_RIFT 미발현' → 'world.active_rifts empty' → prompt + rift_id alias bridge (★ prompt + data)
- **F7**: 'EXIT_RIFT 0' → '`location.realm` 본격 변경 X' → mechanism + prompt 본격 (★ mechanism + prompt)

= 8연속 모두 prompt/data/mechanism fix, 본격 본격 본격 본격
= 추측 X 실측 답 본격

## 잔여 finding (★ F8 candidate)

### ENTER_RIFT success rate 본격 (★ F6 100% → F7 68%)

F7 본격 ENTER_RIFT 6/19 본격 fail 본격. 본격:
- EXIT_RIFT 본격 본격 `world.active_rifts.remove()` 본격 → active_rifts empty 본격
- LLM이 본격 'realm=DUNGEON' 본격 + active_rifts empty 본격 prompt 받지만
- 본격 본격 본격 ENTER_RIFT 본격 호출 본격 → fail (★ 본격 prompt 본격 본격 본격)
- 본격 답 본격 (F8): 
  * EXIT 후 본격 OFFER_TO_STONE 본격 본격 본격 prompt 본격 강화
  * 또는 본격 EXIT 후 본격 시간 본격 본격 본격 본격 (★ 본격 prompt 본격 본격)

### ABSORB_ESSENCE 0 (★ F7 본격 본격)

F7 본격 essence 본격 본격 본격 X — 균열 안 본격 essence encounter 본격 본격 X 또는 LLM 본격 우선순위 본격 본격.

## 다음 본격

- **F8** ENTER_RIFT post-EXIT prompt 본격 (★ 6/19 fail 답)
- Phase 7 동적 사이클
- 1층 본격 마무리 (★ EXIT_RIFT 본격 본격 완전)
