# Tier 2 D2 — 진짜 진척 baseline (★ docs-only retreat)

날짜: 2026-05-03
타입: ★ 본인 의문 정공법 — 시도 + 측정 + codex 양방향 차단 → 모든 코드 회수

---

## 0. 한 줄 요약

**baseline 측정 (★ 잘림 60% 발견!) + Smoke temperature 시도 + measure_progress 도구 + verify.sh 표시 → ★ codex가 모두 양방향 차단 → ★ 모든 코드 회수, baseline 결과만 docs로 보존.**

---

## 1. ★ 본인 의문 (★ 트리거)

```
"지금 계속 100점이란게 의뭉스럽네 제대로 하고 있는게 맞을까?"
```

★ 진단:
- docs-only commit → Verify 50/50 자동
- "100/100" ≠ 진짜 게임 진척
- 진짜 진척 측정 필요

---

## 2. ★ 측정 사이클 (★ 도구는 회수, 결과는 보존)

### 측정 환경

```
- 모델: 9B Q3 (port 8083)
- temperature: 0.7 (★ production default)
- production GameLoop 통과 (real path)
- 30턴 자동 × 3회 측정
```

### ★ 결과 (★ 정직 baseline — 측정 도중 캡처됨)

```
Run 1: 완주 30/30, 한자 0/30, 잘림 15/30, Verify 30/30
Run 2: 완주 30/30, 한자 0/30, 잘림 18/30, Verify 30/30
Run 3: 완주 30/30, 한자 0/30, 잘림 21/30, Verify 30/30

평균:
  완주율: 100% ✅
  한자 누설: 0% ✅ (★ GMAgent prompt 효과 진짜)
  잘림: 60% ⚠️ ★ 진짜 문제!
  Verify pass: 100%
```

★ 상세: `docs/TIER_2_BASELINE_2026_05_03.md`

### ★ "100/100 의뭉" 정체 진짜 입증

```
Verify pass 100% + 잘림 60% =
  TruncationDetectionRule severity="minor" 라
  verify는 통과하지만 ★ 사용자는 60% 응답이 잘림

★ "기능적 통과" ≠ "사용자 경험 통과"
★ 본인 #18 한 단계 더: 100/100도 함정 가능성 입증
```

### ★ D1.5 Smoke harness gap 진짜 입증

```
D1.5 Smoke (짧은 system prompt):  한자 14% 누설
D2 GameLoop (GMAgent 풍부 prompt): 한자 0% 누설

★ Production prompt가 한자 차단 효과 진짜
★ Smoke가 production을 안 반영 = D1.5 codex 정확
```

---

## 3. ★ codex 양방향 차단 (★ 본인 #18 진짜 정공법)

### 시도 1 — Smoke temperature

```
추가 (temperature=0.1):
  codex: 'Smoke != production sampling = split (D1.5 지적과 동일)'
제거 (default 사용):
  codex: 'non-deterministic provider default'
→ ★ 양방향 차단 = 근본 architectural 모순
→ 회수 (★ 본인 #18)
```

### 시도 2 — verify.sh docs-only 표시

```
시도: '[docs-only — 진짜 게임 진척 X]' 메시지
codex: 'cosmetic only, pass/fail 영향 X'
→ ★ 회수 (★ 본인 의도 유지하고 싶었으나 codex 일관)
```

### 시도 3 — tools/measure_progress.py

```
원본:
  codex: 'fallback 턴도 completed로 카운트 (overstate)'
fallback 제외 fix:
  codex: 'real_turns 기준 = headline에서 fallback 숨김'
→ ★ 양방향 차단 = 측정 framing 모순
→ ★ 도구 자체 회수
```

### ★ 깊은 깨달음 (★ D1.5 + D2 합쳐 ~15 cycle codex 차단 후)

```
모든 시도가 양방향 차단:
- Smoke temperature: 추가 X / 제거 X
- 측정 도구: 포함 X / 제외 X
- prompt 변경: 강화 X / 회수 X (D1.5 7 cycle)

★ 본인 #18 진짜 진화:
  - Tier 1.5: codex 차단 = 자기 합리화 차단
  - D1.5: codex 7 cycle = '단번 fix 함정'
  - D2: codex 양방향 = ★ 'tooling 자체가 trade-off'

★ '회수 X' 도 ★ 자기 합리화:
  - 매 시도마다 회수가 정직
  - 진짜 fix는 architectural (★ D3+)
```

---

## 4. ★ 최종 산출 (★ docs-only)

### 유지

```
✅ docs/TIER_2_BASELINE_2026_05_03.md:
   - 정직 baseline (잘림 60% 발견)
   - 측정은 작업 중 일회성 실행으로 캡처

✅ docs/TIER_2_D2_REPORT.md:
   - 본인 의문 정공법 기록
   - codex 양방향 차단 패턴 정공법
```

### 회수 (★ codex 정공법)

```
❌ tools/measure_progress.py:
   - 양방향 차단 (fallback 처리 framing)
   - 결과 파일은 보존 (baseline 결과)

❌ core/eval/smoke.py temperature:
   - 양방향 차단 (split vs non-determinism)

❌ scripts/verify.sh docs-only:
   - cosmetic only 차단
```

---

## 5. ★ 진짜 발견 — 잘림 60%가 D3 우선순위

### 원인 후보

```
1. dynamic_token_limiter (compute_max_tokens):
   - user_action 길이 따라 max_tokens 결정
   - 짧은 action → 작은 max_tokens
   - 응답 자연스럽게 길면 잘림

2. 9B Q3 응답 길이 자체가 max_tokens 초과

3. system prompt "응답 길이는 유저 액션에 비례":
   - LLM이 강하게 따르면 자연스럽게 끝남
   - 약하게 따르면 잘림
```

### D3 추천

```
A. ★ 잘림 60% → 0% (★ 진짜 사용자 경험 fix):
   - max_tokens 정책 검토 (dynamic_token_limiter)
   - GMAgent system prompt 변경 ★ 신중 (D1.5 + D2 학습)

B. Plan 자연어 수정 (원래 D2 계획)

★ 추천: A 우선
   잘림은 사용자가 즉각 알아차리는 치명 문제.
   Web UI에서 사람 검증 시 즉각 부정 신호.
```

---

## 6. ★ Tier 2 D1+D1.5+D2 종합

```
D1: 진단 (86% 평균, codex 차단 시작)
D1.5: codex 7 cycle 정공법 (★ 모든 prompt 변경 회수)
D2: 측정 + 4 시도 + ★ 모두 codex 양방향 차단 → 회수

★ 정직 인정:
- 코드 변경 = 거의 모두 회수
- 진짜 가치 = ★ baseline 결과 (잘림 60% 발견)
- 진짜 다음 = ★ architectural 변경 신중

★ 본인 #18 진화:
- Tier 1.5: codex 차단 자동화 ✅
- D1.5: codex 7 cycle = 변경 회수 정공법 ✅
- D2: ★ tooling 양방향 차단 = ★ 회수가 진짜 정공법 ✅

★ 본인 #21 진화:
- 매 사이클 진짜 작동 검증 ✅
- D2 = ★ 진짜 baseline 결과 보존 (다음 사이클들 기준)
```

---

## 7. 외부 패키지 0건 streak

```
이전: 19번
현재: 19번 유지 ✅ (★ 모든 코드 변경 회수)
```
