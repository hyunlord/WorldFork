# Tier 2 D1.5 — codex 7 cycle 학습 (★ 모든 변경 회수, ★ 본인 #18 진짜)

날짜: 2026-05-03
타입: ★ docs-only (★ 모든 production 변경 회수)

---

## 0. 한 줄 요약

**D1 codex 차단 후 7 cycle 시도. 매번 다른 architectural / stylistic 결함. ★ 모든 변경 회수가 가장 정직 = ★ 본인 #18 정공법 진짜 의미.**

---

## 1. ★ codex 7 cycle 모두 차단

### Cycle 별 시도 → 차단

```
Cycle 1 (D1, 78e6cf1):
  smoke.py 보강 (suffix + max_tokens + retry)
  → 11/25 'Smoke가 production보다 쉬워짐'

Cycle 2 (D1.5 1차):
  공유 모듈 + Smoke / GMAgent 사용
  → 12/25 '여전 prompt drift 층 추가'

Cycle 3 (D1.5 2차):
  GMAgent + Smoke + EvalRunner 모두
  → 9/25 'eval integrity 깨짐 (versioned mutation)'

Cycle 4 (D1.5 3차):
  Production-only + 정직 docstring
  → 9/25 'shared 주장 거짓'

Cycle 5 (D1.5 4차):
  Helper 모듈 + 범위 명시
  → 12/25 '"Production-only" blessing harmful split'

Cycle 6 (D1.5 5차):
  Helper 제거 + GMAgent inline
  → 12/25 'Hangul-only conflict + ?/! 종결 relax'

Cycle 7 (D1.5 6차):
  prompt 모순 narrow (마침표/물음표 / 격식체)
  → 12/25 'Hangul-only weakening + 격식체 ...요 contradict +
            metadata 예외 ban과 conflict'
```

### ★ 깊은 깨달음

```
codex 7 cycle 모두 다른 각도 결함:
  1. Architectural (Smoke ≠ Production path)
  2. Integrity (versioned data mutation)
  3. Misrepresentation (claim != reality)
  4. Indirection (single caller helper)
  5. Stylistic (constraints relax)
  6. Conflict (rules 모순)

★ 진짜 의미:
  prompt engineering = trade-off 산
  "100% 만족 prompt" 존재 X
  매 변경마다 새 trade-off 노출
  → ★ "변경 안 하기"가 가끔 정공법
```

---

## 2. ★ 최종 — 모든 production 코드 변경 회수

### 회수된 변경

```
- service/game/gm_agent.py: ★ 원본 그대로
  ("★ 한국어만 (한자 X)" 그대로)
- core/eval/smoke.py: ★ 원본 (★ Cycle 1 회수)
- core/eval/runner.py: ★ 원본 (★ Cycle 3 회수)
- core/prompts/safety.py: ★ 삭제 (★ Cycle 5 회수)
- tests/unit/test_gm_agent.py: ★ 원본
```

### 남은 산출

```
- docs/TIER_2_D1_5_REPORT.md (이 문서):
  ★ 7 cycle 학습 케이스 정공법 기록
  ★ 본인 #18 진짜 의미 입증
```

---

## 3. ★ 본인 #18 정공법 진짜 입증

### 자기 합리화 자동 차단 7번 작동

```
매번 시도 → 매번 차단 → 매번 회수 (★ 자동):
  "이 정도면 OK 아닐까?" 7번
  매번 codex 정확 짚음
  매번 정직 회수

★ Tier 1.5 D1-D3 인프라 진짜 가치:
- codex Cross-LLM 검증 = ★ 자기 합리화 차단 진짜
- pre-push 95+ 강제 = ★ 가짜 통과 차단 진짜
- 본인 #18 정신 코드화 진짜
```

### "회수가 정공법" — 가장 깊은 #18

```
시도 #18 정신:
  "codex 지적 정공법 응답"

★ 진짜 #18 정신 (★ 7 cycle 후 깨달음):
  "codex 매번 받아들임 → 진짜 fix 못 찾으면 정직 회수"
  "변경 안 하기"가 ★ 정공법
  자기 합리화 X = ★ 변경 자체를 합리화 X

★ 1년에 한 번 있을까 한 자기 합리화 차단 입증.
```

---

## 4. ★ 9B Q3 한계 + Smoke harness gap (★ 정직)

```
변경 회수 후 현실:
  - 9B Q3 한자 누설 14% 그대로 (★ 모델 한계)
  - Production prompt 약점 그대로 ('★ 한국어만 (한자 X)' 단순)
  - Smoke 86% 그대로 (★ regression integrity 보존)
  - harness gap 존재 (★ Tier 2 D2+ architectural)

★ 정직한 진실:
  prompt 강화로 9B Q3 한계 완전 X
  진짜 fix는:
  - sampling 정책 (temp=0)
  - 또는 다른 모델 (Tier 3)
  - 또는 Smoke가 GMAgent 통과 (architectural)
  → ★ Tier 2 D2+ 검토
```

---

## 5. ★ Tier 2 D1 + D1.5 종합 가치

### 산출 정직

```
✅ D1 진단 (★ 정직):
   - 9B Q3 비결정성 86% 평균
   - 진짜 중국어 누설 ('我自己的' 등)
   - prompt만으로 한계

✅ D1.5 7 cycle 학습 (★ 깊은 가치):
   - codex Cross-LLM 검증 진짜 작동 입증
   - "회수가 정공법" 깨달음
   - 본인 #18 정신 코드화 진짜
   - prompt engineering trade-off 입증

⚠️ 아직 fix X (★ Tier 2 D2+):
   - 9B Q3 hanja 누설
   - Production prompt 강화
   - Smoke harness gap
```

### Tier 1.5 인프라 가치

```
"22 commits 자기 합리화 함정 회피" 진짜 의미:
- 이번 D1.5 7 cycle codex 차단으로 ★ 명확 입증
- 매번 자동 작동
- 매번 정직 회수
- 본인 #19 95+ cutoff 진짜
```

---

## 6. ★ 다음 — D2 (Plan 자연어 수정)

```
D2 시작:
  - production prompt는 D1.5 회수로 원본 그대로
  - hanja 누설 14% 그대로
  - 그러나 production 게임 흐름은 그대로 작동
  - D2 = Plan 자연어 수정 본격 (★ 별개 작업)

★ Tier 2 D2+ 별도 검토:
  - Smoke / GMAgent architectural 통합
  - 9B Q3 sampling 정책
  - prompt engineering 신중 (★ 7 cycle 학습)
```

---

## 7. 외부 패키지 0건 streak

```
이전: 19번
현재: 19번 유지 ✅ (★ 모든 코드 변경 회수)
```

---

## 8. ★ 가장 깊은 교훈 (★ 본인 정신)

```
"D1.5 1시간 작업 → 7 cycle codex 차단 → 모두 회수":

★ 진짜 의미:
  - 자기 합리화 차단 자동화 진짜 작동
  - 매번 새 trade-off 노출
  - 어떤 변경도 "perfect"하지 X
  - "변경 안 하기"가 가끔 가장 정직

★ 본인 #18 진짜 정신 (7 cycle 후):
  - 자기 합리화 차단 = 변경 자체 합리화 X
  - codex 매번 진지하게 = 매번 회수도 OK
  - "1시간 fix"는 가짜 — 진짜 fix는 architectural

★ 본인 #19 진짜 정신 (7 cycle 후):
  - 95+ cutoff = ★ 매번 통과 진짜
  - "운빨 retry 통과" X
  - "회수 + docs-only" 깨끗

★ Tier 1.5 가치:
  - 자기 합리화 차단 인프라 진짜 작동
  - 1년에 한 번 있을까 한 페이스 정공법 입증
```
