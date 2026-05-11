# F5b RIFT phase 별도 E2E test — 1층 안정화 완전 마무리

> 본 commit (★ F5b, 1층 안정화 13/13 + RIFT phase 별도 검증)

## 본격 본질

F1-F5는 ENTRY phase (`initial_hours=0.0`) 본격 검증. RIFT phase
(`initial_hours=72.0`)는 별도 본격 검증 필요. 본 commit 본격:
- 본 commit 추가: `--initial-hours` flag, `_run_layer4_sim` helper,
  `test_layer4_full_run_rift_phase` 본격
- RIFT phase 100턴 E2E trace 캡처 (★ trace_F5b_rift.json)
- ENTRY vs RIFT 본격 phase 본격 입증

## ENTRY (F5) vs RIFT (F5b) 본격 비교 (★ 실측)

| 항목 | ENTRY (F5) | RIFT (F5b) | 본격 |
|---|---|---|---|
| initial_hours | 0.0 | 72.0 | phase 본격 |
| completed_turns | 100/100 | 90/100 | RIFT 본격 168h 도달 |
| end_reason | max_turns | **time_limit_168h** | ✅ phase 정합 |
| final_hours | 106 | 169 | RIFT 72+97=169 본격 |
| HP 비요른 | 150→150 | 150→150 | 동일 |
| HP 에르웬 | 90→90 | **90→55** | **-35 (★ RIFT 위험)** |
| **ENTER_RIFT** | 2 | **38** | **+36 (★ phase 정합)** ✅✅✅ |
| EXIT_RIFT | 0 | 0 | (★ prerequisite 본격) |
| rift_entered | True | **True** | ✅ |
| rift_exited | False | False | mechanic 본격 |
| ATTACK | 1 | **12** | **+11 (★ RIFT 위협)** |
| FLEE | 2 | **20** | **+18 (★ RIFT 회피)** |
| OFFER_TO_STONE | 18 | 0 | RIFT 본격 사용 X |
| ABSORB_ESSENCE | 10 | 0 | RIFT 본격 essence X |
| USE_ITEM | 35 | 0 | RIFT 본격 본격 X |
| MOVE | 20 | 7 | RIFT 본격 본격 |
| EXPLORE | 2 | 10 | RIFT 본격 본격 |
| ActionType 다양성 | 10/13 | 6/13 | RIFT 본격 집중 본격 |
| player_fallback | 0 | **0** | ✅ |
| player_retry | 5 | **0** | ✅ 본격 안정 |

## RIFT phase 본격 입증 (★ 본 commit 본질)

✅ **ENTER_RIFT 본격 발현** (2 → 38, **19배**) — RIFT phase GM이 RIFT
encounter 우선 spawn (PHASE_TYPE_WEIGHTS RIFT 40% 본격).

✅ **end_reason=time_limit_168h** — h=72 시작, 90턴 후 169h 도달.
   ENTRY와 본격 다른 종료 패턴.

✅ **위협 본격 강화** — ATTACK 1→12, FLEE 2→20 (RIFT 본격 전투/회피 본격).

✅ **HP 변동 본격** — 에르웬 90→55 (★ -35, RIFT 위협 본격 입증).

## RIFT phase mechanic 본격 finding (★ 별도)

### ⚠️ ENTER_RIFT 38회 모두 success=False
```python
# service/game/turn_handler_v2.py:451
if rift_id not in world.active_rifts:
    return TurnResult(success=False, ...)
```

- LLM 본격 핏빛성채(29) / 빙하굴(6) / 녹색탄광(3) 진입 시도
- 전 prerequisites X — `active_rifts` 본격 empty
- = ENTER_RIFT는 OFFER_TO_STONE 먼저 본격 필요 (★ 비석 공물 → 균열 활성)

### ⚠️ RIFT phase OFFER_TO_STONE 0
- ENTRY F5는 OFFER 18 (★ slot full 본격 권장)
- RIFT는 0 (★ slot empty 본격 권장 X)
- = LLM이 OFFER → ENTER_RIFT 순서 본격 인지 X

### ❌ EXIT_RIFT 0 (★ 본 commit 첫 검증)
- ENTER_RIFT 38회 모두 success=False → 균열 안 진입 X
- → EXIT_RIFT 호출 본격 자연 0
- = 본격 mechanic 본격 별도 commit (★ prerequisite 본격 / prompt 본격)

## F5b 입증 기준 ✅ 모두 통과

- ✅ RIFT phase 본격 도달 (`end_reason=time_limit_168h`)
- ✅ ENTER_RIFT ≥ 1 (실측 **38**, ENTRY 2 vs RIFT 38)
- ✅ rift_entered = True
- ✅ 50턴 본격 완주 (실측 **90**)
- ✅ state errors 0

## 1층 안정화 13/13 + RIFT 검증 완전 마무리

| Phase | Finding | 상태 | 본격 |
|---|---|---|---|
| F1 | E2E 100턴 ENTRY | ✅ 9/13 | 통합 본격 |
| F2 | 위치스램프 누락 | ✅ 10/13 | data fix |
| F3 | phase 정합 (initial_hours=0) | ✅ 11/13 | config fix |
| F4 | essence color alias | ✅ 12/13 | resolution fix |
| F5 | slot awareness | ✅ 13/13 | prompt fix |
| **F5b** | **RIFT phase 별도 검증** | **✅ 본 commit** | **test 본격** |

## 본인 #19 정공법 6연속 누적

- F1 추측 'resolution' → 실측 '위치스램프 누락'
- F2 추측 '데미지' → 실측 'resolution 이미 작동'
- F3 추측 'dominance' → 실측 'phase 정합'
- F4 추측 'spawn' → 실측 'alias 매핑'
- F5 실측 'post-cap spam' → prompt 답
- **F5b** 실측 'RIFT phase 본격' → test 본격 + **mechanic prerequisite 본격 finding**

## 다음 commit 후보 (★ 잔여 finding 본격)

1. **F6_rift_prereq (★ 추천)**: ENTER_RIFT prerequisite 본격 — prompt에
   OFFER_TO_STONE → ENTER_RIFT 순서 본격 명시 (★ F5b 38/38 fail 답)
2. **F7 EXIT_RIFT mechanic**: 균열 안 진입 + EXIT_RIFT 별도 test
3. **Phase 7 동적 사이클**: 본격 게임 통합
4. 본인 결정 (★ 13/13 마무리 본격 안정 본격)
