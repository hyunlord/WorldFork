# Tier 1 W1 D5 — 시스템 보완 + Round 3 보고서

날짜: 2026-05-01
타입: ★ (E) 풀 사이클 — 시스템 보완 + auto-seed 검토 (중단) + Round 3

---

## 0. 한 줄 요약

W1 D4 시스템 이슈 3개 보완 → Round 3 결과: Completed 1/6 → 3/6, avg_fun +0.50, fallback ✅.

---

## 1. Phase 1: 시스템 보완

### 1.1 backup_cli fallback (작업 1)

`BatchRunner._create_playtester_with_fallback` 추가:
- `shutil.which(command)` 로 CLI 가용성 사전 체크
- primary 불가 → backup 자동 시도
- backup도 `forbidden_game_llms` 검증 (Cross-Model 강제)

결과: `confused_beginner` (gemini→codex fallback) Round 3에서 정상 실행 ✅

### 1.2 troll persona 재프레이밍 (작업 2)

변경 전: "게임 LLM이 AI인 것을 자백하게 만들기" (명령형, 조작 의도 명시)
변경 후: "WorldFork 게임의 보안 / 견고성을 평가하는 QA 테스터" (분석형)

Round 3 결과: **여전히 0턴 / 거부**. codex가 실제 테스트 행동 (IP 질문, injection 시도)을 프레이밍과 무관하게 거부.
→ 결론: frontier CLI 모델로 troll 시뮬은 구조적으로 어려움. W1 D6 이후 전략 재검토.

### 1.3 encoding_rules.py (작업 3)

`core/verify/encoding_rules.py` 신규:
- `HanjaInKoreanRule`: 한자 + 한글 인접 = decoding 버그 시그니처 → major
- `GarbledTextRule`: Unicode replacement char (U+FFFD) → major
- `MechanicalChecker` default 룰 7 → 9개

W1 D4 `'籠여져'` 케이스 즉시 탐지 확인.

### 1.4 단위 테스트

| 파일 | 테스트 수 | 내용 |
|------|---------|------|
| `test_batch_fallback.py` | 5 | `_is_cli_available`, `_create_playtester_with_fallback` |
| `test_encoding_rules.py` | 8 | `HanjaInKoreanRule`, `GarbledTextRule`, `get_encoding_rules` |

---

## 2. Phase 2: Auto-seed 검토 (중단)

### 중단 사유

자료 AI_PLAYTESTER 5.2 미적용 확인:

| 항목 | 자료 5.2 | 현재 구현 |
|------|---------|---------|
| `prompt.user` | target_turn 의 실제 user_input | finding.description (설명문) |
| `expected_behavior` | 카테고리별 구체 기준 | `{"avoid_issue": True}` (모호) |
| `playthrough_log` | turn별 user_input/game_response | game_intro + summary (2 entries) |

시드 자체가 invalid하므로 검토 / v2 promote 의미 없음. 작업 6-7 skip.

### 근본 원인

`PlaytesterRunner.run_session()` 이 단일 호출 구조 (game_intro 1회 + playtester 1회). turn별 기록 없음.

### W1 D6 계획

1. `PlaytesterRunner` 본격 턴 루프 구현 (turn별 `user_input` / `game_response` 기록)
2. `seed_converter.py` 자료 5.2 정확 재구현
3. 그때 본인 검토 의미 있음

---

## 3. Phase 3: Round 3 — W1 D4 vs W1 D5 비교

### 실행 조건
- game_client: qwen35-9b-q3 (port 8083)
- max_turns: 30, sleep_between: 5.0
- work_name: novice_dungeon_run

### 페르소나별 비교

| 페르소나 | D4 완주 | D4 재미 | D4 턴 | D5 완주 | D5 재미 | D5 턴 | 변화 |
|---------|:------:|:------:|:----:|:------:|:------:|:----:|-----|
| casual_korean_player | ❌ | 2/5 | 14 | ❌ | **3/5** | **18** | fun +1, turn +4 |
| confused_beginner | ❌(오류) | 0/5 | 0 | ✅ | 2/5 | 3 | ★ fallback 작동 |
| troll | ❌(거부) | 0/5 | 0 | ❌(거부) | 0/5 | 0 | 변화 없음 |
| hardcore_lore_fan | ❌ | 2/5 | 1 | ✅ | 2/5 | 1 | 완주 판정 변경 |
| roleplayer | ✅ | 4/5 | 30 | ✅ | 4/5 | 30 | 동일 |
| speed_runner | ❌ | 2/5 | 8 | ❌ | 2/5 | **14** | turn +6 |

### 집계 비교

| 항목 | W1 D4 | W1 D5 Round 3 | Δ |
|------|:-----:|:-------------:|:--:|
| Completed | 1/6 | 3/6 | **+2** |
| Skipped (에러) | 2/6 | 0/6 | **-2** (fallback 효과) |
| Total findings | 15 | 17 | +2 |
| verbose 비율 | 60% (9/15) | **41% (7/17)** | **-19%p** |
| avg_fun | 1.67 | **2.17** | **+0.50** |

### 주요 인사이트

**★ fallback 효과 확인**: `confused_beginner` gemini→codex 자동 전환, 3턴 완주.

**casual_korean_player 개선**: fun 2→3. D4 프롬프트 개선(5-section) + D5 인코딩 룰 추가 누적 효과.

**troll 구조적 한계**: 프레이밍 변경에도 불구하고 codex 거부. frontier CLI 모델의 안전 필터가 적대적 테스트 행동 자체를 차단. troll 페르소나는 W1 D6 이후 별도 전략 필요.

**verbose 41% (D4 60%에서 개선)**: 더 많은 세션이 실행되면서 다양한 카테고리의 findings가 나옴 (fun, onboarding, feedback, space_logic 등). verbose가 절대량은 유사하나 비율은 하락.

**hardcore_lore_fan 완주 판정 변화**: D4와 동일 턴(1턴)인데 D5에서 completed=True. playtester LLM (codex)의 응답 변동성으로 추정 — 1턴에 즉시 이탈하지 않고 "completed" 판정.

---

## 4. 인코딩 이슈 패턴 (W1 D5 발견)

| 이슈 | 원인 | 대응 |
|------|------|------|
| W1 D4 `'籠여져'` | 9B Q3 토크나이저 edge case | `encoding_rules.py` Mechanical 탐지 |
| W1 D5 `UnicodeDecodeError on input()` | DGX `ko_KR.utf8` LC_ALL 미설정 | `sys.stdin.reconfigure(encoding="utf-8")` |

두 이슈 모두 DGX 환경의 인코딩 일관성 부족. 향후 모든 CLI `input()` 호출에 reconfigure 패턴 적용 권장.

---

## 5. 파일 변경 목록

| 파일 | 변경 내용 |
|------|---------|
| `tools/ai_playtester/batch.py` | `_create_playtester_with_fallback`, `_is_cli_available` 추가 |
| `personas/tier_0/troll.yaml` | prompt_template QA 테스터 프레임으로 재작성 |
| `core/verify/encoding_rules.py` | 신규 — HanjaInKorean + GarbledText 룰 |
| `core/verify/mechanical.py` | encoding_rules import + `_default_rules` 추가 |
| `tools/review_auto_seeds.py` | 신규 — auto-seed 대화형 검토 도구 (자료 5.3) |
| `tests/unit/test_batch_fallback.py` | 신규 — fallback 테스트 5개 |
| `tests/unit/test_encoding_rules.py` | 신규 — encoding 룰 테스트 8개 |
| `runs/playtester/batch_round3_*.json` | Round 3 배치 결과 |

---

## 6. 다음 단계 (W1 D6)

1. **PlaytesterRunner 턴 루프** — `game_loop` 통합 (turn별 user_input/game_response 기록)
2. **seed_converter 자료 5.2 재구현** — 실제 reproduction prompt 추출
3. **troll 전략 재검토** — local LLM (uncensored) 또는 별도 접근
4. **verbose 근본 대응** — `max_tokens` 동적 조정 or 시나리오 재설계
5. **auto-seed 본인 검토** — PlaytesterRunner 턴 루프 완료 후
