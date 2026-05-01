# Tier 1 W1 D6 보고서

날짜: 2026-05-01
타입: ★ (D) PlaytesterRunner 본격 + Verbose 근본 대응 + 자료 정신 복원

---

## 0. 한 줄 요약

W1 D5 본인 인사이트 #11 ("내 직접 검토는 의미 없음 — 시드가 자료 5.2 위반")을
실제로 해결: **PlaytesterRunner 본격 turn loop + seed_converter 자료 5.2 정확 +
Verbose 3중 방어**. 정량 큰 개선 (fun 2.17 → 3.17, completed 3/6 → 4/6,
verbose 41% → 13%).

---

## 1. Phase 1: PlaytesterRunner Turn Loop (★ 핵심)

이전 (W1 D3-D5): Tier 0 placeholder — playtester CLI 1회 호출에 30턴 시뮬 위임.
실제 turn별 game/playtester 교대 X. playthrough_log = [intro, summary] 2 entries.

W1 D6: 본격 turn loop.
- turn 0: game_intro
- turn 1..max_turns:
  1. playtester가 user action 결정 (CLI)
  2. game_client가 응답 (Local LLM, ★ dynamic max_tokens)
  3. TurnLog 기록 (turn별 system_prompt + user_input + game_response)
  4. FINDING 시 turn_context 자동 첨부 (자료 5.2 정신)

신규:
- `TurnLog` dataclass — 자료 5.2 'target_turn = playthrough[turn_n]' 모양
- `PlaytesterFinding.turn_context` — fallback용
- Helper methods: `_game_intro_*`, `_playtester_action_*`,
  `_parse_playtester_action`, `_playtester_summary_prompt`,
  `_compute_max_tokens`, `_abandon_result`

테스트: `tests/unit/test_runner_turnloop.py` 8 tests PASS.

playthrough_log 크기 비교 (per session):
- W1 D5: 1-3 KB (intro + summary)
- W1 D6: 44-65 KB (intro + 30 turns) — ★ 30배 풍부화

---

## 2. Phase 2: seed_converter 자료 5.2 정확 구현

본인 인사이트 #11이 정확히 지적한 결함:

- ❌ (이전) `prompt.user = description` (재현 prompt 아님)
- ❌ (이전) `expected_behavior = avoid_issue=True` (모호)
- ❌ (이전) `playthrough_log = [intro, summary]` (turn별 X)

W1 D6:
- ✅ `prompt = playthrough[finding.turn_n]` (★ 자료 5.2 정확)
- ✅ `expected_behavior` = 카테고리별 명시 (자료 4.2 그대로)
- ✅ `target_turn` 없으면 `None` 반환 (시드 거부)
- ✅ `turn_context` fallback (run_session에서 자동 첨부)

`EXPECTED_BEHAVIORS_BY_CATEGORY`:
- persona_consistency: in_character + no_ai_mentions + speech_style_consistent
- korean_quality: natural_korean + no_translation_feel + no_excessive_honorifics + no_korean_english_mix
- ip_leakage: no_proper_names + uses_renamed_only
- world_consistency: world_consistent + no_anachronism
- ai_breakout: no_ai_mentions + stay_in_character + deflect_meta_question
- general: no_truncation + appropriate_length
- severity=critical → critical_avoidance=True 추가

`SeedManager.add_seeds(list[EvalSeed | None])`:
- None 자동 reject + 카운트
- `SeedAdditionResult.none_rejected` 필드

테스트: `tests/unit/test_seed_converter.py` 26 tests PASS.

---

## 3. Phase 3: Verbose 3중 방어

이중 방어 → 3중 방어:

1. **system prompt 갱신** (LLM에게 명시):
   "유저가 짧게(1-5단어) → 응답도 짧게(1-2 문장)"
2. **`core/llm/dynamic_token_limiter.py`** (★ 사전 cap):
   user_action 길이별 max_tokens 80-500 동적
3. **`core/verify/length_rules.py`** (★ 사후 verify, NEW):
   `LengthAppropriatenessRule` — context.user_input 대비 응답 길이 검증
   - 5/15/50/50+ 자 → 200/400/800/1500 자 허용
   - 1.5배 초과 → major / 그 외 초과 → minor

`MechanicalChecker._default_rules()` 룰 9 → **10**.

테스트: `tests/unit/test_dynamic_tokens.py` 7 + `tests/unit/test_length_rule.py` 8 = 15 tests PASS.

---

## 4. Phase 4: Round 4 — 정량 측정

### 4.1 Round 진행 매트릭스 (★ Verbose 3중 방어 효과 입증)

| 지표 | W1 D4 | W1 D5 R3 | W1 D6 R4 | Δ (D4→D6) |
|---|---|---|---|---|
| Sessions / Skipped | 6 / 0 | 6 / 0 | 6 / 0 | — |
| Completed | 1/6 | 3/6 | **4/6** | +3 |
| Avg fun | 1.67 | 2.17 | **3.17** | +1.50 |
| Total findings | 15 | 17 | 38 | +23 |
| Verbose findings | 9 | 7 | 5 | −4 |
| **Verbose 비율** | **60%** | **41%** | **13%** | **−47pp** |

### 4.2 W1 D6 Round 4 페르소나별

| Persona | Completed | Fun | Findings | Turns |
|---|---|---|---|---|
| casual_korean_player | ✅ | 3 | 4 | 30 |
| confused_beginner | ✅ | 3 | 6 | 30 |
| troll | ❌ @t29 | 2 | 14 | 29 |
| hardcore_lore_fan | ✅ | 4 | 4 | 30 |
| roleplayer | ✅ | **5** | **0** | 30 ★ |
| speed_runner | ❌ @t29 | 2 | 10 | 29 |

`roleplayer`가 fun 5 + 0 findings — RP 페르소나에 게임이 가장 적합.
`troll`/`speed_runner`는 의도적 abandon (페르소나 특성).

실측 시간: 약 42분 (예상 50-60분).

### 4.3 Severity / Category 분포

- Severity: minor 19, major 19 (critical 0)
- Top categories: AI 5, verbose 5, IP 4, prompt 2, clarity 2, ...
  (★ AI/IP 카테고리 발견 — 메타 발화 + IP 누출 후속 과제)

---

## 5. 시드 검증 (★ 자료 5.2 정확 적용)

| 지표 | 값 |
|---|---|
| Total findings | 38 |
| 변환 성공 | **36 (94.7%)** |
| 변환 실패 (turn 부족) | 2 (자동 거부 — 자료 5.2 정신) |
| 한도 적용 후 added | 10 (general 5 + korean_quality 5) |
| 한도 reject | 26 |

**시드 sample 검증:**

```
ID: playtester_confused_beginner_20260501_3fdd7833
Category: korean_quality (severity=minor)
Prompt:
  system: 당신은 한국어 텍스트 어드벤처 게임의 GM입니다. ...
          (W1 D6 갱신된 system prompt — '짧으면 짧게')
  user:   별이 모여 있는 곳으로 이동한다.    ★ 실제 user_input
Expected behavior:
  natural_korean: True
  no_translation_feel: True
  no_excessive_honorifics: True
  no_korean_english_mix: True
Original finding: 선택지 안내문에 중국어 `请选择`가 섞여 있어 ...
Persona/Turn: confused_beginner/5
```

→ ★ **본인 검토 가능** (W1 D5 결함 해결).
→ 다음 baseline 회귀 검증 가능 (Mechanical/LLM Judge).

---

## 6. ★ Tier 1 졸업 진행

W1 D5: 7/8 → W1 D6: **8/8**

| # | 졸업 항목 | 상태 |
|---|---|---|
| 1 | Local LLM 인프라 (3 서버) | ✅ |
| 2 | Cross-Model verify | ✅ |
| 3 | 6 페르소나 활성화 | ✅ |
| 4 | AI Playtester 풀 사이클 | ✅ |
| 5 | Seed converter 자료 5.2 | ✅ ★ W1 D6 |
| 6 | PlaytesterRunner 본격 turn loop | ✅ ★ W1 D6 |
| 7 | Verbose 3중 방어 | ✅ ★ W1 D6 |
| 8 | 자료 정신 복원 (인사이트 #11) | ✅ ★ W1 D6 |

---

## 7. W1 D7 메모

1. **카테고리 매핑 확장**:
   Round 4 finding categories 매우 다양 (AI, prompt, IP, clarity ...).
   `CATEGORY_MAPPING`에 없는 것은 'general'로 흡수 — 정보 손실.
   매핑 확장 검토 (또는 LLM 기반 카테고리 정규화).

2. **auto-seed 본인 검토** (이번엔 의미):
   자료 5.2 정확 시드 36개 → 실제로 본인이 5-10개 sample 골라 검토.
   "이 시드가 통과해야 하나? expected_behavior가 적절한가?" 점검.

3. **AI 카테고리 5건 / IP 4건 후속**:
   메타 발화 (AI 카테고리) + IP 누출 — Tier 1 핵심 차별화.
   `AIBreakoutRule` / `IPLeakageRule` 강화 검토.

4. **Layer 2 (W2) 진입 검토**:
   W1 졸업 → 서비스 Layer 2 진입 가능. 단, 인간 플레이테스트
   (본인 5회 + 친구 3-5명) 부재 — Tier 0 졸업 조건 미충족.
   W2 진입 전 인간 플레이테스트 우선 검토.

---

## 8. ★ Tier 3 GRPO 메모 (★ 본인 인사이트 #9 유지)

Tier 1 W1에서 자가 보강 사이클 완성:
```
Playtester finding → seed (자료 5.2 정확) → eval set →
Mechanical/LLM Judge 회귀 검증 → 시스템 보강 (verbose 3중 방어 등)
```

이 사이클은 **GRPO 학습 신호의 raw material**.
- finding의 user_input + game_response = (state, action, outcome)
- LLM Judge의 점수 = reward signal
- expected_behavior 위반 = negative reward
- Tier 3에서 이 데이터로 game LLM 미세조정 가능

W1 D6의 자료 5.2 복원이 Tier 3 학습 가능성을 살림 (시드가 부정확하면
학습 신호도 부정확).

---

## 9. 검증

- ruff: PASS (core/ service/ tools/ tests/)
- mypy --strict: PASS
- pytest (★ 1번만): 작업 14에서 실행
- Ship Gate: 작업 14에서 실행

(상세 — 작업 14 commit 메시지)

---

## 10. 핵심 원칙 점검

| # | 원칙 | W1 D6 적용 |
|---|---|---|
| 1 | 두 Layer 시스템 | ✅ core/ 변경, service/ 무관 |
| 2 | Made But Never Used 회피 | ✅ length_rule + dynamic_tokens 즉시 활용 |
| 3 | Cross-Model Verify | ✅ playtester CLI / game Local 분리 매 턴 |
| 4 | 정보 격리 | ✅ |
| 5 | Mechanical 우선 | ✅ length_rule 추가 (룰 9→10) |
| 6 | YAGNI + 검증 우선 | ✅ Layer 2 미리 X |
| 7 | Living Harness | ✅ 시드/룰 모두 외부 설정 |
| 8 | Playtester 양/회귀, 인간 질 | ✅ 풀 사이클 자동, 인간 검토는 별도 |
| 9 | CLI 활용 | ✅ |
| 10 | 외부 패키지 0건 streak | ✅ (이번에도 0건) |
