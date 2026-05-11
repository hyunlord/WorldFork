# F1 E2E Layer 4 100턴 통합 검증 결과

> 본 commit (★ F1, 1층 안정화 8/13 → 9/13): Phase 6 시각화 7/7 + 1층 안정화 누적 → 통합 본격 검증

## 시뮬 설정

| 항목 | 값 |
|---|---|
| target_turns | 100 |
| completed_turns | **77/100** (★ time_limit_168h 본격) |
| end_reason | `time_limit_168h` ✅ |
| LLM Player | qwen35_9b_q3 (8083) |
| LLM GM | qwen36_27b_q2 (8082) |
| 시뮬 시간 | 1156.8s (≈19.3분) |
| initial_hours_in_dungeon | 72h (★ commit I, RIFT phase 시작) |

## E2E pass 자체 검증

| 검증 | 결과 |
|---|---|
| state 음수 X | ✅ |
| 50턴 본격 완주 (77 ≥ 50) | ✅ |
| 13 ActionType ≥5 (★ 실측 8) | ✅ |
| end_reason 정합 | ✅ time_limit_168h |
| 168h 한도 정합 | ✅ final_hours=168 |

**E2E pass ✅** — Layer 4 통합 본격 작동 입증.

## 잔여 finding 본격 실측 진단

### F2 차단 — ✅ **양호**
- gm_fallback_count: 0
- player_fallback_count: 0
- gm_retry_count: 0
- player_retry_count: 3 (★ minor, 본격 안정)
- early_termination_lt_30: False
- **차단 본격 X — 안정 본격 입증**

### F3 균형 — ❌ **본격 미달 (★ 핵심 finding)**
- 비요른 HP: 150 → 150 (★ **변동 X**)
- 에르웬 HP: 90 → 90 (★ **변동 X**)
- essences_absorbed_by_actor: bjorn 0 / erwen 0 (★ **흡수 X**)
- essences_max: 0
- ATTACK 9회 시도하지만 **HP 변동 0 — 데미지 본격 X resolution**
- ABSORB_ESSENCE 1회 시도하지만 **흡수 0 — encounter spawn X 또는 mechanic 본격 X**

### F4 다양성 — ⚠️ **부분 (5 ActionType 미사용)**
- action_types_used: **8 / 13**
- 사용 본격: ENTER_RIFT (35), EXPLORE (13), ATTACK (9), OFFER_TO_STONE (8), FLEE (6), MOVE (4), ACTIVATE_LIGHT (1), ABSORB_ESSENCE (1)
- **미사용 5개**:
  - `REST` (★ 휴식 4시간, 본문 27화)
  - `WAIT` (★ 시간 흐름)
  - `COMMUNICATE` (★ 메시지 스톤, 본문 11화)
  - `USE_ITEM` (★ 아이템 사용)
  - `EXIT_RIFT` (★ 균열 이탈)
- light 활성 32턴 (★ 41% 본격 정합)
- 비요른 39 / 에르웬 38 (★ 균등 분배)

### F5 본문 정합 — ⚠️ **부분 (ENTER_RIFT 본격 dominance)**
- **ENTER_RIFT spam: 35/77 ≈ 45%** ❌ (★ 본격 finding)
  - "Player rule violation actor=... reason=enter_rift dominance" 발화 (★ 직전 commit A.6 enforcement 작동)
  - LLM 본격 ENTER_RIFT 본격 선호 → server-side enforcement 본격 차단 가능성
- rift_entered: True (★ 한 번 success)
- rift_exited: False ❌ (★ EXIT_RIFT 본격 X 사용 → 균열 이탈 mechanic X)
- absorb_essence_count: 1 (★ 흡수 시도 부족)
- attack_count: 9 (★ encounter 본격 부족 또는 무력)
- offer_to_stone_count: 8 (★ 비석 공물 본격 시도 — 본문 374화 정합)
- communicate_count: 0 ❌ (★ 메시지 스톤 통신 본격 X)
- hours_consumed: 168h ✅ (★ 한도 정합)

## 본격 진단 요약

본 100턴 시뮬은 **state 안정 ✅** + **시간 정합 ✅** + **end_reason 정합 ✅** 입증.

그러나 다음 **4 finding 본격 실측**:

| Finding | 상태 | 핵심 본질 |
|---|---|---|
| **F3 HP/정수 곡선 X** | ❌ 본격 미달 | HP 변동 0, 정수 흡수 0 — encounter resolution mechanic 본격 X 작동 |
| **F5 ENTER_RIFT spam 45%** | ❌ 본격 finding | LLM 본격 ENTER_RIFT 선호, dominance enforcement 본격 통과? |
| **F4 5 ActionType 미사용** | ⚠️ 부분 | REST/WAIT/COMMUNICATE/USE_ITEM/EXIT_RIFT 본격 X |
| **F5 rift_exited X** | ⚠️ EXIT_RIFT 본격 X | 균열 진입 후 이탈 본격 mechanic 본격 X 작동 |

## 잔여 4 finding 본격 우선순위 (★ 본인 결정 본격)

1. **F3 HP/정수 곡선 X** (★ 최우선) — combat / essence absorption mechanic 본격 X resolution
   - encounter spawn rate 본격 진단
   - ATTACK → 데미지 본격 propagation X
   - ABSORB_ESSENCE → essence_slots 본격 X 증가

2. **F5 ENTER_RIFT spam dominance** — LLM 선호 본격 답
   - A.6 enforcement 본격 통과? player_retry=3 본격 정합
   - LLM prompt 본격 ENTER_RIFT 본격 줄이기

3. **F4 미사용 5 ActionType** — REST/WAIT/COMMUNICATE/USE_ITEM/EXIT_RIFT
   - 본문 상황 본격 LLM 본격 X 인식 가능
   - 또는 phase enforcement 본격 ENTER_RIFT 본격 우선

4. **F5 EXIT_RIFT 본격 X** — 균열 이탈 mechanic 본격 X

## 본 commit 결정

- **F1 pass ✅** (★ 자체 검증 본격 pass — state/시간/end_reason)
- 잔여 finding 본격 실측 답 (★ 추측 X)
- **다음 commit 후보 본격**:
  - **F2** (★ 추천): F3 HP/정수 곡선 본격 답 — encounter resolution mechanic 본격
  - **F3**: ENTER_RIFT dominance 본격 답 (★ LLM prompt 본격)
  - **F4**: 미사용 ActionType 본격 답 (★ phase prompt 본격)

본인 결정 대기.
