# F6 rift prerequisite prompt — ENTER_RIFT 0/38 → 20/20 success

> 본 commit (★ F6, F5b 본격 mechanic prereq 답)

## 본격 진단 본질

F5b 실측 trace 분석 결과 **두 본격 mismatch**:

### (A) Korean name vs rift_id mismatch
- LLM 본격 한국어 name target: '핏빛성채' (29) / '빙하굴' (6) / '녹색탄광' (3)
- `enter_rift`/`offer_to_stone`/`exit_rift` 본격 `rift_id` 본격 검색 (`bloody_castle` 등)
- = 한국어 본격 lookup 실패 → success=False
- ★ F4 essence color → monster명 본격 동일 패턴

### (B) LLM 본격 OFFER_TO_STONE 0회 호출
- F5b 90턴 RIFT phase 본격 OFFER 0회
- 원인: prompt 본격 prerequisite (OFFER → 균열 활성화 → ENTER_RIFT) 명시 X
- LLM이 ENTER_RIFT를 본격 호출하면 작동 본격 추측

## 본 commit fix

### 1. `service/game/turn_handler_v2.py` — alias bridge (★ F4 패턴 동일)
```python
def _resolve_rift_id(target: str) -> str | None:
    f1 = get_floor1_definition()
    for r in f1.rifts:
        if r.rift_id == target or r.name == target:
            return r.rift_id
    return None
```
`offer_to_stone` / `enter_rift` / `exit_rift` 모두 한국어 name 또는 rift_id 본격 accept.

### 2. `service/sim/player_agent.py` — prompt 본격 강화

**ACTION_TYPE_GUIDANCE 본격**:
- OFFER_TO_STONE 본격 본질 명시:
  - 비석 공동 + 정수/마석 → world.active_rifts 등록 → ENTER_RIFT 가능
- ENTER_RIFT 조건 명시:
  - `world.active_rifts ≥ 1` 본격
  - 활성 X 시 사용 금지 + OFFER_TO_STONE 먼저
- EXIT_RIFT 본격: 균열 안 본격 조건

**_build_situation_summary 본격**:
- active_rifts empty 본격 명시 경고:
  - "**활성 균열**: 없음 ⚠️ (★ ENTER_RIFT 사용 금지 — OFFER_TO_STONE 먼저)"
- active_rifts ≥ 1 본격: "(★ ENTER_RIFT 가능)"

**RIFT encounter hint 본격 conditional**:
- 활성 본격 → "활성 본격, ENTER_RIFT 가능"
- 비활성 → "비활성, OFFER_TO_STONE 먼저 (★ active_rifts 등록 후 ENTER)"

## F5b → F6 RIFT phase 본격 비교 (★ 실측)

| 항목 | F5b | F6 | 변화 |
|---|---|---|---|
| completed_turns | 90/100 | 83/100 | -7 |
| end_reason | time_limit_168h | time_limit_168h | 동일 ✅ |
| final_hours | 169 | 168 | -1 (★ 본격 정합) |
| HP 에르웬 | 90→55 | 90→45 | -10 (★ 위험 ↑) |
| **OFFER_TO_STONE** | **0** | **13** | **+13** ✅✅✅ |
| OFFER success | 0/0 | **11/13** | 본격 작동 본격 |
| **ENTER_RIFT** | 38 | 20 | -18 (★ 효율 ↑) |
| **ENTER_RIFT success** | **0/38** | **20/20** | **100% ✅✅✅** |
| **rift_entered** | True | **True** | 유지 |
| EXIT_RIFT | 0 | 0 | (★ 잔여 finding) |
| ActionType 다양성 | 6/13 | **8/13** | +2 ✅ |
| ABSORB_ESSENCE | 0 | 1 | +1 |
| player_fallback | 0 | 0 | ✅ |
| player_retry | 0 | 1 | +1 (★ 본격 미세) |

## F6 입증 기준 ✅ 모두 통과

- ✅ OFFER_TO_STONE 본격 증가 (0 → **13**)
- ✅ ENTER_RIFT success > 0 (실측 **20/20**, 100%)
- ✅ rift_entered True (★ 본 commit 핵심 본질 입증)

## ActionType 빈도 (★ 본격 변화)

| ActionType | F5b | F6 |
|---|---|---|
| ENTER_RIFT | 38 | 20 |
| FLEE | 20 | (필요 시 trace 본격) |
| ATTACK | 12 | 11 |
| EXPLORE | 10 | (필요 시) |
| MOVE | 7 | (필요 시) |
| ACTIVATE_LIGHT | 3 | (필요 시) |
| **OFFER_TO_STONE** | **0** | **13** ✅ |
| **ABSORB_ESSENCE** | 0 | 1 ✅ |

## OFFER target 본격 (★ 본격 정합)

F6 OFFER targets:
- '핏빛성채' × 11 (★ 한국어 name 본격 작동)
- '마석' × 2 (★ 한국어 X — '마석'은 rift_id 본격 X)

→ '마석' 2회 fallback (★ 본격 미세 정합), 11/13 success.

## 잔여 finding (★ F6 후)

### ⚠️ EXIT_RIFT 0 (★ F6 본격 별도 finding)
- ENTER_RIFT 20/20 success 본격 진입 후
- 균열 안에서 LLM이 EXIT_RIFT 호출 본격 X
- 원인 추정:
  - 균열 안 LLM 본격 (★ 클리어/도주 본격 prompt X)
  - 또는 본격 진입 즉시 본격 다른 action
- = 별도 F7 본격 후보

### ⚠️ rift_exited False
- ENTER만 호출, 균열 안에서 본격 다른 action
- 본격 location 본격 X (★ side_effect만 본격, location 변경 caller가)
- = F7 mechanic 본격

### ⚠️ HP 에르웬 -45
- F5b -35 → F6 -45 (★ 본격 위험 ↑)
- RIFT 본격 본격 LLM이 본격 진입 → 본격 위협 본격
- 본격 trade-off

## 본인 #19 정공법 7연속 입증

- F1 추측 'resolution' → 실측 '위치스램프 누락'
- F2 추측 '데미지' → 실측 'resolution 이미 작동'
- F3 추측 'dominance' → 실측 'phase 정합'
- F4 추측 'spawn' → 실측 'alias 매핑'
- F5 실측 'post-cap spam' → prompt 답
- F5b 실측 'RIFT phase' → test 본격 + mechanic prereq
- **F6** 실측 '두 본격 mismatch (alias + prompt)' → 동시 답 ✅

## 본 commit 결정

**F6 본격 ship ✅** — RIFT mechanic 본격 작동:
- 한국어 name alias bridge (★ F4 동일 패턴)
- prompt 본격 prerequisite 본격 명시
- ENTER_RIFT 0/38 → 20/20 success (★ 100%)
- OFFER_TO_STONE 0 → 13 (11/13 success)

## 다음 commit 후보

1. **F7 EXIT_RIFT mechanic** (★ 추천): 균열 안 LLM 본격 prompt + location 본격
2. **Phase 7 동적 사이클**: 본격 게임 통합
3. 본인 결정
