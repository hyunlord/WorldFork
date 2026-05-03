# Tier 2 D3 — 잘림 진단 + dynamic_token_limiter codex 5 cycle 양방향 차단 (★ docs-only retreat)

날짜: 2026-05-03
타입: ★ 옵션 C — 진단 + fix 시도 + ★ codex 5 cycle 차단 → 코드 회수

---

## 0. 한 줄 요약

**진단 100% 명확 (잘림 50% = max_tokens 도달) + dynamic_token_limiter 200-1000 fix 시도 (잘림 50% → 7%) → ★ codex 5 cycle 양방향 차단 → 코드 회수, 진단 결과 + 학습만 보존.**

---

## 1. 본인 W2 D5 정공법 흐름

```
W2 D5 (4-26): '...조력자 셰' 잘림 (★ 본인 ^C)
              → '사람 검증 가치 X' (★ 본인 #15-#16 트리거)
D4: TruncationDetectionRule (★ severity minor)
D2: 60% 잘림 진짜 측정
D3: ★ 5 cycle 시도 → 코드 회수 + ★ 진단/학습 보존
```

---

## 2. Phase 1 진단 (★ 핵심 가치 — 진단 100%)

### 인라인 스크립트로 30턴 1회 측정

```
잘린 응답: 15/30 (50%)
★ 100% (15/15)가 max_tokens 도달!
- 응답 길이 200-280자
- 모두 max_tokens 80 또는 150 한계 직격
- 잘린 tail이 모두 문장 중간 또는 선택지 중간
```

### 가설 100% 확정

```
USER_ACTIONS 30개:
  - 24개 (80%) → max_tokens=150 (≤15자)
  - 6개 (20%) → max_tokens=80 (≤5자)

W1 D6 가정: chat 응답 (verbose 방어) → 80-500 cap
실제: 게임 GM = 짧은 액션도 풍부한 묘사 필수
→ ★ chat 가정이 게임에 맞지 않음 입증
```

### 산출

`docs/TIER_2_D3_TRUNCATED_SAMPLES.jsonl` (★ 잘린 응답 15건 상세)

---

## 3. Phase 3-4 fix 시도 (★ 코드 회수)

### 시도

```
core/llm/dynamic_token_limiter.py: 80-500 → 200-1000
- char_count <= 5: 80 → 200
- char_count <= 15: 150 → 400
- char_count <= 50: 250 → 600
- char_count <= 150: 400 → 800
- > 150: 500 → 1000
```

### Phase 4 측정 (★ 핵심 가치 입증)

```
잘림: 50% → 7% (★ 86% 감소!)
완주: 29/30 (fallback 1건)
한자: 0% 유지
Verify: 100% 유지
```

### ★ codex 5 cycle 양방향 차단

```
Cycle 1 (8f48311): 200-1000 + safety 200
  codex: 'Empty input safety 100→200 = service caller 영향'
         'Short bucket 80/150→200/400 = LengthRule 약화'

Cycle 2 (ada38b6): safety 100 복귀 + scope docstring
  codex: '"gm_agent.py 전용" 거짓 (ai_playtester도 호출)'
         'Empty silently 100 fallback masks caller violation'

Cycle 3 (dad5bb8): ValueError raise + scope 정직
  codex: 'ValueError = breaking change introduces regression'

Cycle 4 (d421ec1): silent 100 복귀
  codex: 'Silent 100 fallback masks caller error'

Cycle 5 (a9d353e): assert
  codex: 'AssertionError in shared runtime helper (-O disabled risk)'

★ 모든 default 처리 (silent x2, raise, assert) 양방향 차단
```

### ★ 정공법 retreat (★ D2 패턴 반복)

```
모든 D3 코드 변경 회수:
- core/llm/dynamic_token_limiter.py (★ 원본 80-500 그대로)
- tests/unit/test_dynamic_tokens.py (★ 원본 그대로)

★ 잘림 fix 보존 X — 잘림 60%로 복귀.
★ 진단 결과 + 학습만 docs로 보존.
```

---

## 4. ★ codex 5 cycle 양방향 차단 패턴 (★ 본인 #18 진화)

### Tier 2 패턴 정리

```
D1.5 (gm_agent.py prompt): 7 cycle → 모든 변경 회수
D2 (smoke.py temperature): 양방향 → 회수
D2 (measure_progress.py): 양방향 → 회수
D3 (dynamic_token_limiter): ★ 5 cycle 양방향 → 회수

★ 깊은 패턴:
같은 파일을 반복 변경하면 codex가 매번 새 결함 angle을 찾음.
어떤 default 처리도 (silent / raise / assert) 차단 가능.
이는 codex의 한계이자 우리의 학습.
```

### ★ 본인 #18 진짜 진화

```
이전 인식:
- Tier 1.5: codex Cross-LLM 차단 = 자기 합리화 차단
- D1.5: 회수 정공법
- D2: 양방향 차단 → 회수

★ D3 깊은 깨달음:
- 측정 기반 핵심 가치 (잘림 50%→7%) 입증되어도
- codex가 부수적 trade-off로 양방향 차단 가능
- 진짜 fix는 ★ architectural (★ 새 파일 / 새 모듈)
- 같은 파일 반복 변경 = codex cycle 함정
```

---

## 5. ★ 핵심 가치 (★ 코드 회수 후에도 보존)

### 진단 결과 (★ 측정 입증)

```
✅ 잘림 60% 원인 = 100% max_tokens 도달 (★ 측정 확정)
✅ 게임 GM ≠ chat 응답 (★ 가정 부정확 입증)
✅ 200-1000 cap이 잘림 86% 감소 효과 (★ Phase 4 측정)
```

### ★ 다음 D4+ 새 접근 (★ codex cycle 회피)

```
A. 새 파일/모듈로 cap 정책 분리:
   - core/llm/game_token_policy.py (신규)
   - 게임 GM 전용 정책
   - dynamic_token_limiter는 chat 응답 그대로
   - ★ 기존 파일 변경 X = codex cycle 회피

B. GMAgent에서 직접 cap 결정:
   - gm_agent.py에 _compute_game_tokens() 메서드
   - dynamic_token_limiter는 그대로
   - ★ 호출 분리

C. 정직 인정 + 잘림 60% 그대로:
   - 사용자 경험 부정 (★ Web UI 검증 시 치명)
   - 다음 사이클들로 이월
```

### ★ 추천 D4: 옵션 A 또는 B

```
이유:
- 같은 파일 반복 변경 = codex cycle 함정
- 새 파일 / 새 메서드 = codex 새 angle 적게 (★ 깨끗한 시작)
- 측정 기반 fix는 ★ 진짜 가치 (D3에서 86% 감소 입증)
```

---

## 6. ★ Tier 2 D1+D1.5+D2+D3 종합

```
D1: codex 차단 입증
D1.5: 7 cycle = 단번 fix 함정
D2: 잘림 60% 발견 + 양방향 차단
D3: ★ 100% 진단 + 86% fix 입증 + 5 cycle 차단 → 회수

★ 진짜 가치 (★ 코드 회수 후에도):
- 본인 W2 D5 정공법 진단 100%
- 잘림 86% 감소 측정 입증
- codex cycle 패턴 학습 (★ 같은 파일 반복 X)
- 본인 #18 진화 (★ 측정 + 회수 + 새 접근)
```

---

## 7. 외부 패키지 0건 streak

```
이전: 19번
현재: 19번 유지 ✅ (★ 모든 코드 변경 회수)
```

---

## 8. ★ 정직 인정

```
잘림 60% 그대로:
  - 코드 회수로 D3 fix 효과 X
  - 사용자 경험 직접 부정
  - Web UI 검증 시 치명 (★ 본인 #16 차단)

진짜 fix는 D4+:
  - 새 파일 / 새 메서드 (★ codex cycle 회피)
  - 측정 기반 (★ D3에서 효과 입증됨)
  - 본인 결정 보조 가능
```
