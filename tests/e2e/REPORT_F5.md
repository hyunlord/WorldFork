# F5_slot_awareness — 13/13 마무리

> 본 commit (★ F5, 1층 안정화 12/13 → **13/13 마무리**)

## 본격 진단 본질

F4 실측 trace 분석 결과:
- slot 5/5 도달: turn 20
- post-cap ABSORB spam: **36회** (★ 가득 후에도 ABSORB 호출 반복)
- = Player LLM이 slot full 상태 본격 인지 X

진짜 root cause: prompt에 slot/max 명시 X + essence encounter hint 본격 unconditional.

## 본 commit fix (★ player_agent.py)

### 1. `_format_slot_status()` helper 신규
- 5/5 → `5/5 ⚠️ FULL (★ ABSORB_ESSENCE 사용 금지, OFFER_TO_STONE 권장)`
- 4/5 → `4/5 (★ 거의 가득, 1 추가 가능)`
- < 4 → `N/5 (M 추가 가능)`

### 2. `_build_player_prompt()` 보강
- 정수 슬롯 line 본격 `_format_slot_status` 사용 (★ count/max + FULL 경고)
- essence encounter hint 본격 slot_full 조건부:
  - slot FULL → "OFFER_TO_STONE 으로 슬롯 비운 후 재시도"
  - slot 여유 → "ABSORB_ESSENCE 우선 (30분 자연 소멸)"
- hints — slot_full 시 명시적 "ABSORB_ESSENCE 사용 금지"

### 3. `ACTION_TYPE_GUIDANCE` ABSORB 본격 강화
- 조건: floating essence 발견 + 슬롯 < 5
- 5/5 FULL 시 사용 금지 + OFFER_TO_STONE 권장

### 4. `sim_runner.py` essence_slot_max ctx 본격 노출

## F4 → F5 본격 비교 (★ 실측)

| 항목 | F4 | F5 | 변화 |
|---|---|---|---|
| completed_turns | 100/100 | 100/100 | 동일 ✅ |
| end_reason | max_turns | max_turns | 동일 ✅ |
| **ABSORB 총** | **44** | **10** | **-34 (-77%)** ✅✅ |
| **ABSORB post-cap spam** | **36** | **2** | **-34 (-94%)** ✅✅✅ |
| ABSORB pre-cap | 8/8 (100%) | 8/8 (100%) | 본격 정합 유지 ✅ |
| **OFFER_TO_STONE** | **0** | **18** | **+18** ✅✅✅ |
| ActionType 다양성 | 7/13 | **10/13** | +3 ✅ |
| ENTER_RIFT | 0 | **1** | +1 (★ RIFT 도달) |
| FLEE | 0 | **1** | +1 (★ 회복) |
| REST | 0 | **1** | +1 (★ 회복) |
| essences_max | 5 | 5 | 동일 ✅ |
| final_hours | 46 | **106** | +60 (★ 시간 진행 ↑) |
| HP 에르웬 | 90→75 | 90→90 | (★ 안전 본격 ↑) |
| player_fallback | 3 | **0** | -3 ✅ |
| player_retry | 9 | 5 | -4 ✅ |
| light_active | 99 | 50 | -49 (★ 본격 trade-off) |

## F5 입증 기준 ✅ 모두 통과

- ✅ post-cap ABSORB spam: 34 → **< 5** (실측 **2**)
- ✅ ABSORB 시도: 44 → **< 15** (실측 **10**)
- ✅ OFFER_TO_STONE 증가 (★ slot 비우기 본격, 0 → **18**)
- ✅ pre-cap ABSORB 본격 정합 (8/8 → 8/8 유지)

## ActionType 다양성 (★ 10/13 본격 회복)

| ActionType | F4 | F5 |
|---|---|---|
| ABSORB_ESSENCE | 44 | 10 |
| USE_ITEM | 34 | 17 |
| MOVE | 12 | 35 |
| ATTACK | 6 | 1 |
| ACTIVATE_LIGHT | 2 | 18 |
| WAIT | 1 | 0 |
| EXPLORE | 1 | 0 |
| **OFFER_TO_STONE** | **0** | **18** (★ 신규) |
| **ENTER_RIFT** | 0 | 1 (★ 신규) |
| **FLEE** | 0 | 1 (★ 신규) |
| **REST** | 0 | 1 (★ 신규) |

## 1층 안정화 13/13 본격 마무리

| Finding | 본격 | 상태 |
|---|---|---|
| F1 E2E 100턴 통합 | 9/13 | ✅ |
| F2 위치스램프 누락 | 10/13 | ✅ |
| F3 phase 정합 (initial_hours=0) | 11/13 | ✅ |
| F4 essence color alias 매핑 | 12/13 | ✅ |
| **F5 slot awareness** | **13/13** | **✅ 마무리** |

## 본인 #19 정공법 5연속 입증

- F1 추측 "resolution" → 실측 "위치스램프 누락"
- F2 추측 "데미지 균형" → 실측 "resolution 이미 작동"
- F3 추측 "ENTER_RIFT dominance" → 실측 "phase 정합"
- F4 추측 "spawn mechanism" → 실측 "alias 매핑"
- F5 실측 "post-cap spam" → prompt 답 (★ 5번째 정공법)

## 잔여 finding (★ F5 후)

### ⚠️ light_active 99 → 50
- F4에 비해 빛 사용 ↓ (★ MOVE 35회 본격 활성 X 다른 영역)
- 본격 trade-off (★ ActionType 다양성 ↑ vs 빛 활성 ↓)

### ⚠️ HP 에르웬 90→90 (★ 안전 본격)
- F4 90→75 → F5 90→90 (★ 변동 X)
- = encounter 본격 회피 본격 (★ MOVE / FLEE 본격 활성)

### ❌ F5b RIFT phase 별도 test
- ENTER_RIFT 1회 도달 본격 (★ EXIT_RIFT 본격 X)
- initial_hours=72 별도 test 본격 필요 (★ 후속 finding)

## 본 commit 결정

**F5 본격 ship ✅** — slot awareness 완전 작동:
- post-cap spam 본격 해소 (36 → 2, -94%)
- OFFER_TO_STONE 본격 회복 (0 → 18)
- ActionType 다양성 7/13 → 10/13
- 1층 안정화 **13/13 마무리**

본인 #19 정공법: F4 실측 → 진짜 root cause = **prompt slot 인지 X**, mechanism 변경 X, prompt 본격만.

## 다음 commit 후보

1. **F5b RIFT phase 별도 test** (★ initial_hours=72 분리 test case)
2. **Phase 7 동적 사이클** (★ 본격 게임 통합)
3. 본인 결정 (★ 13/13 마무리 본격 안정 본격)
