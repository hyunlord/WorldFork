# F2 encounter resolution 결과 — 위치스램프 누락 답

> 본 commit (★ F2, 1층 안정화 9/13 → 10/13): F1 실측 F3 finding 본격 답.

## 본격 진단 본질

F1 trace 분석 결과 **resolution mechanic 자체는 이미 작동** (★ `_execute_action` + `execute_attack` 본격).

진짜 root cause: **floor1.py `FLOOR1_MONSTERS`에 위치스램프 누락** (★ 7종/8종 정합 X).
- LLM이 매 턴 ATTACK target='위치스램프' 본격 시도
- `execute_attack`에서 `f1.monsters` 검색 → None → success=False
- = 9/9 ATTACK 본격 fail (★ F1 trace 입증)

본 commit 본격 fix:
- `_WITCH_LAMP` MonsterDef 본격 추가
- `FLOOR1_MONSTERS` 7 → 8종 (★ Phase 3 시각화 정합)
- 테스트 7→8 본격 갱신 (3 tests)

## F1 → F2 본격 비교

| 항목 | F1 | F2 | 본격 변화 |
|---|---|---|---|
| completed_turns | 77 | **83** | +6 (★ 시간 효율 ↑) |
| end_reason | time_limit_168h | time_limit_168h | 동일 |
| HP 비요른 곡선 | 150→150 | 150→150 | 동일 (★ strength+physical=30, 처치 후 데미지 X) |
| HP 에르웬 곡선 | 90→90 | **90→80** | ✅ **데미지 본격 발생** |
| ATTACK success | 0/9 | **5/9** | ✅ **본격 처치 발생** |
| essence 흡수 max | 0 | 0 | ⚠️ drop_rate 0.0001 본격 낮음 |
| light_active 턴 | 32 | **66** | ✅ +34 (★ 2배 ↑) |
| player_retry | 3 | **1** | ✅ 안정 ↑ |

## ATTACK 본격 success 본격 (★ F2 핵심 입증)

| Turn | Actor | Target | Success | 본격 |
|---|---|---|---|---|
| 5 | 비요른 | 노움 | ✅ | 9등급 처치 |
| 17 | 비요른 | 위치스램프 | ✅ | **★ 신규 monster** |
| 21 | 비요른 | 위치스램프 | ✅ | 본격 |
| 30 | 에르웬 | 위치스램프 | ❌ | strength 부족 |
| 31 | 비요른 | 위치스램프 | ✅ | 본격 |

## ActionType 다양성 (★ 8/13 동일, 분포 본격)

| ActionType | F1 | F2 |
|---|---|---|
| ENTER_RIFT | 35 | 37 (⚠️ 본격 spam 여전) |
| EXPLORE | 13 | 10 |
| ATTACK | 9 | 9 |
| OFFER_TO_STONE | 8 | 7 |
| FLEE | 6 | 7 |
| MOVE | 4 | **9** (★ +5, 이동 활용 ↑) |
| ACTIVATE_LIGHT | 1 | **3** (★ +2) |
| ABSORB_ESSENCE | 1 | 1 |

미사용 5종: REST / WAIT / COMMUNICATE / USE_ITEM / EXIT_RIFT (★ 동일)

## 잔여 finding 본격 재진단

| # | Finding | F1 | F2 | 상태 |
|---|---|---|---|---|
| F3 HP 변동 | ❌ 0 | ✅ -10 | **본격 답** |
| F3 ATTACK success | ❌ 0/9 | ✅ 5/9 | **본격 답** |
| F3 essence 흡수 | ❌ 0 | ❌ 0 | ⚠️ drop_rate 본격 낮음 (별도 finding) |
| F5a ENTER_RIFT spam | ❌ 35 (45%) | ❌ 37 (45%) | 잔여 |
| F4 5 ActionType 미사용 | ⚠️ | ⚠️ | 잔여 |
| F5b EXIT_RIFT X | ❌ | ❌ | 잔여 |

## 본 commit 결정

- **F2 본격 ship ✅** (★ ATTACK success + HP 변동 입증)
- 본 fix은 **데이터 본격** (★ floor1.py 1 monster 추가), mechanic 변경 X
- 본인 #19 정공법: F1 실측 → 추측 X 진짜 root cause 답

## 다음 commit 후보

1. **F3 (★ 추천)**: ENTER_RIFT dominance 본격 답 (★ LLM prompt 본격, 45% spam 본격)
2. F4: 미사용 ActionType 본격 답 (★ REST/WAIT/COMMUNICATE/USE_ITEM/EXIT_RIFT)
3. essence drop_rate 본격 답 (★ 0.0001 → 본격 높이기, 또는 별도 essence 자료 본격)
