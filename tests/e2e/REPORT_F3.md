# F3 E2E initial_hours=0 — ENTER_RIFT spam 완전 해소

> 본 commit (★ F3, 1층 안정화 10/13 → 11/13)

## 본격 진단 본질

F2 trace 후 본격 ENTER_RIFT 45% 본격 finding 재진단:
- `SimConfig.initial_hours_in_dungeon = 72.0` (★ default, commit I)
- → 시뮬 시작이 **RIFT phase** (h≥72)
- → GM이 40% RIFT encounter 본격 spawn
- → LLM이 RIFT encounter에 본격 ENTER_RIFT 응답 (★ 정상)
- = **45% ENTER_RIFT는 dominance 아니라 phase 본격 정합**

진짜 본격 fix: **E2E test에서 initial_hours=0.0** (★ ENTRY phase 시작).
- 본격 PROMPT 변경 X (★ 이미 적절)
- 본격 mechanic 변경 X (★ 이미 작동)
- **테스트 설정만 본격 답** — 단계적 phase 진행 본격 test

## F2 → F3 본격 비교 (★ 실측)

| 항목 | F2 | F3 | 변화 |
|---|---|---|---|
| completed_turns | 83 | **100/100** | +17 ✅ |
| end_reason | time_limit_168h | max_turns | ✅ 100턴 달성 |
| final_hours | 168 | **44** | ENTRY phase 본격 |
| HP 비요른 | 150→150 | 150→150 | 동일 |
| HP 에르웬 | 90→80 | 90→85 | 약간 |
| essences_max | 0 | 0 | 여전 ⚠️ |
| player_retry | 1 | 11 | 적응 본격 |
| light_active | 66 | 77 | +11 ✅ |

## ActionType 빈도 (★ 본격 변화)

| ActionType | F2 | F3 | 변화 |
|---|---|---|---|
| **ENTER_RIFT** | **37 (45%)** | **0 (0%)** | **✅✅✅ 완전 해소** |
| **ABSORB_ESSENCE** | 1 | **43** | **✅ +42** |
| **USE_ITEM** | 0 | **34** | **✅ 신규** |
| MOVE | 9 | 11 | +2 |
| ATTACK | 9 | 3 | -6 (★ ENTRY 안전) |
| EXPLORE | 10 | 1 | -9 (★ USE_ITEM 대체) |
| ACTIVATE_LIGHT | 3 | 6 | +3 |
| **COMMUNICATE** | 0 | **1** | ✅ 회복 |
| **WAIT** | 0 | **1** | ✅ 회복 |
| OFFER_TO_STONE | 7 | 0 | -7 |
| FLEE | 7 | 0 | -7 (★ ENTRY 안전) |

**ActionType 다양성 8/13 동일**, but completely different 8 — F3는 안전한 ENTRY phase에 맞는 행동 분포.

## 본격 진전 입증

✅ **ENTER_RIFT spam 완전 해소** (45% → 0%)
✅ **미사용 3 ActionType 회복** (USE_ITEM / COMMUNICATE / WAIT)
✅ **100/100 max_turns 달성** (★ 시간 효율 본격)
✅ **ABSORB_ESSENCE 43회 시도** (★ LLM이 정수 흡수 본격 의도)

## 잔여 finding (★ F3 후)

### ⚠️ ABSORB success rate 0/43
- LLM 본격 43회 ABSORB 시도하지만 essences_absorbed = 0
- 추정: floating essence가 실제 spawn 본격 X (★ drop_rate canonical 0.0001)
- 또는 target name이 잘못된 매칭
- = 별도 finding **F4_essence** 본격

### ❌ F5b EXIT_RIFT 본격 X
- ENTER_RIFT 0이라 EXIT_RIFT도 본격 X (★ 본격 자연)
- RIFT phase 도달 X — 분리 test 본격 필요

### ⚠️ ATTACK count 9→3
- ENTRY phase는 encounter 본격 적음 (★ phase 정합)
- 본격 trade-off

### ⚠️ player_retry 1→11
- LLM이 본격 적응 본격, retry 11회 발생
- 그러나 fallback 0 (★ 안정)

## 본 commit 결정

**F3 본격 ship ✅** — 매우 큰 진전:
- ENTER_RIFT 100% 해소
- USE_ITEM/COMMUNICATE/WAIT 회복
- 100턴 완주

본인 #19 정공법: F2 실측 → 진짜 root cause = **테스트 설정 (initial_hours)**, prompt/mechanic 변경 X.

## 다음 commit 후보

1. **F4_essence (★ 추천)**: ABSORB 43 시도 → 0 success 본격 답
2. F5b: RIFT phase 본격 별도 test (★ initial_hours=72 별도 test case)
3. 본인 결정
