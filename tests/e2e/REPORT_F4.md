# F4 floating essence color alias — ABSORB 0/43 → 10/10 (cap 도달)

> 본 commit (★ F4, 1층 안정화 11/13 → 12/13)

## 본격 진단 본질

F3 trace 분석 결과 ABSORB_ESSENCE 43회 시도, 0회 성공.

진짜 root cause: **GM prompt와 resolution data의 명명 본격 불일치**:
- GM (sim_gm_agent.py:146-152): essence를 **색명**으로 spawn
  - 갈색 → 고블린 / 흙색 → 노움 / 청록색 → 슬라임 / 핏빛 → 칼날늑대 / 회청색 → 레이스
- Player LLM: GM가 spawn한 색명을 그대로 ABSORB target
- `absorb_floating_essence` (turn_handler_v2.py:286-294): floor1.py drops를 **monster명** ('고블린 정수')만 lookup
- = 43회 모두 essence_name 매칭 실패 → success=False

## 본 commit fix

**Case C+B 본격** — spawn mechanism은 LLM 본격 작동 중, resolution layer가 둘을 연결 X.

본 commit 본격 `_COLOR_TO_ESSENCE_NAME` alias 매핑 추가 (★ turn_handler_v2.py:286-302):

```python
_COLOR_TO_ESSENCE_NAME: dict[str, str] = {
    "갈색 정수": "고블린 정수",
    "흙색 정수": "노움 정수",
    "청록색 정수": "슬라임 정수",
    "산성록 정수": "슬라임 정수",
    "핏빛 정수": "칼날늑대 정수",
    "회청색 정수": "레이스 정수",
    "녹색 정수": "위치스램프 정수",
}
```

본 매핑이 GM prompt의 색 인지와 floor1.py의 본문 정합 monster 명명을 연결.
- Data 본격 유지 (★ 본문 fidelity 1차)
- Resolution layer가 색→monster bridge

## F3 → F4 본격 비교 (★ 실측)

| 항목 | F3 | F4 | 변화 |
|---|---|---|---|
| completed_turns | 100/100 | **100/100** | 동일 ✅ |
| end_reason | max_turns | max_turns | 동일 ✅ |
| final_hours | 44 | 46 | +2 |
| HP 비요른 | 150→150 | 150→150 | 동일 |
| HP 에르웬 | 90→85 | **90→75** | **-15 (★ 본격 변동)** |
| **essences_max** | **0** | **5** | **✅✅✅ +5** |
| **essences_absorbed_by_actor** | 0,0 | **비:5, 에:5** | **본격 cap 도달** |
| ABSORB attempts | 43 | 44 | 동일 빈도 |
| ABSORB success | **0/43** | **10/10 (cap 전)** | **✅ 100% pre-cap** |
| light_active | 77 | 99 | +22 ✅ |
| player_retry | 11 | 9 | -2 |

## ABSORB 본격 success 본격 (★ 핵심 입증)

| Turn | Actor | Target | Slot 후 | Success |
|---|---|---|---|---|
| 2 | 에르웬 | 고블린 정수 | 1 | ✅ |
| 3 | 비요른 | 고블린 정수 | 1 | ✅ |
| 6 | 에르웬 | 고블린 정수 | 2 | ✅ |
| **8** | **에르웬** | **갈색 정수** | **3** | **✅ (★ alias)** |
| 11 | 비요른 | 갈색 정수 | 2 | ✅ |
| 12 | 에르웬 | 갈색 정수 | 4 | ✅ |
| 15 | 비요른 | 갈색 정수 | 3 | ✅ |
| 17 | 비요른 | 갈색 정수 | 4 | ✅ |
| 20 | 에르웬 | 갈색 정수 | 5 | ✅ |
| 21 | 비요른 | 고블린 정수 | 5 | ✅ |
| 24+ | (★ slot 5 cap) | * | 5 | ❌ (★ slot 본격 full, 매핑 X) |

**Pre-cap success rate: 10/10 = 100%** ✅
**Post-cap: 0/34** (★ slot cap 본격, 매핑 X — essence_slots_used == essence_slot_max).

## ActionType 빈도 (★ 본격 변화)

| ActionType | F3 | F4 |
|---|---|---|
| ABSORB_ESSENCE | 43 | 44 |
| USE_ITEM | 34 | 34 |
| MOVE | 11 | 12 |
| ATTACK | 3 | 6 |
| ACTIVATE_LIGHT | 6 | 2 |
| WAIT | 1 | 1 |
| EXPLORE | 1 | 1 |
| COMMUNICATE | 1 | 0 |
| 미사용 | 5 | 6 |

action_types_used: 8 → 7 (★ COMMUNICATE 사라짐 본격 trivial).

## 본격 진전 입증

✅ **ABSORB success 본격 작동** (0/43 → 10/10 pre-cap, **100%**)
✅ **essences_max 0 → 5** (★ slot cap 도달 본격)
✅ **HP 변동 본격 발생** (★ 에르웬 90→75, F3 90→85에서 ↑)
✅ **light_active 77 → 99** (★ 거의 매 턴 빛)

## 잔여 finding (★ F4 후)

### ⚠️ Slot cap 후 ABSORB spam (post-cap 34/44)
- LLM이 slot 5/5 후에도 ABSORB 시도 (★ 34회)
- = prompt 본격 보강 후보 (★ essence_slots_used 본격 인지 X)
- 별도 finding **F5_slot_awareness** 본격

### ❌ F5b EXIT_RIFT 본격 X
- ENTRY phase 시작이라 RIFT phase 미도달 (★ F3 본격 동일)
- 분리 test 본격 필요 (initial_hours=72 별도)

### ⚠️ COMMUNICATE 1 → 0
- 본격 trivial — 본인 결정 가능

## 본 commit 결정

**F4 본격 ship ✅** — ABSORB resolution 완전 작동:
- Color alias 매핑 본격 입증 (★ 갈색 정수 6/11 success, slot cap 전 100%)
- essences_max 0 → 5 (★ 본 commit 진정한 진전)
- HP 변동 본격 발생 (★ 에르웬 -15)

본인 #19 정공법: F3 실측 → 진짜 root cause = **명명 본격 불일치** (★ GM 색명 / data monster명), prompt/mechanic 변경 X, resolution layer alias만.

## 다음 commit 후보

1. **F5_slot_awareness (★ 추천)**: Player prompt에 essence_slots_used 본격 cap 인지 추가
2. F5b: RIFT phase 본격 별도 test (★ initial_hours=72 분리 test case)
3. F6: 5 미사용 ActionType (REST/WAIT/COMMUNICATE/USE_ITEM/EXIT_RIFT) 본격 답
