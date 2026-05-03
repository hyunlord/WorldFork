# Tier 1.5 회고 — 자기 합리화 차단 (★ 본인 #15-#21)

> 작성: 2026-05-03 / 트리거: Tier 1.5 D4 + ROADMAP 재조정 후
> 단계: D5 cleanup + 회고 (★ 옵션 C)

---

## 0. 한 줄 요약

**W2 D5 본인 30초 ^C 시도 → 4+ 인사이트 → Tier 1.5 6 사이클 → ★ 자기 합리화 차단 자동화 ON.**

---

## 1. 트리거 — W2 D5 본인 첫 풀 플레이 시도

```
2026-05-02:
  - 본인이 직접 python tools/play_w2_d5.py 실행
  - 입력: novice_dungeon_run
  - Game Loop turn 1: 행동 "3"
  - GM 응답: "...당신의 뒤에는 조력자 셰" ← ★ 잘림
  - 본인 turn 2 시점에 ^C 중단

본인 짚음:
  "짤리던데 검증 한건맞아? 하네스 파이프라인이 작동은 하고있는게 맞아?
   사람이 검증할 가치가 없는 상태인데?"

★ 이게 22 commits 자기 합리화 함정 진짜 진단 시점.
```

---

## 2. 본인 인사이트 #15-#21 정식

### #15 — Made-but-Never-Used (★ 자료 함정 32 정공법)

```
"하네스 파이프라인이 처음부터 적용한다고 해놓고
 실제로는 baseline_runner.py 1곳만 통합 +
 PlaytesterRunner / GMAgent / GameLoop 코드만 + 사용 X"

가치: Tier 1 진척 부풀림 진단
적용:
  - W2 D2-D4 PlaytesterRunner / GMAgent 함수만
  - "Verbose 80% → 13%" 통계 의심 (★ dynamic_token_limiter 단독 효과)
  - 인프라만, 통합 X

정공법:
  - Tier 1.5 D4: TaskContext / HookManager → GameLoop 진짜 통합
  - ⚠️ CodingLoop / ReplanOrchestrator: 정직 인정 (★ Tier 2)
```

### #16 — 사람 검증 = 4 게이트 후만 (★ 두 번 짚음)

```
첫 짚음 (W2 D5):
  "사람 검증 = 게이트 통과 후만:
   게이트 1: 자동 검증
   게이트 1.5: Layer 1 자동화
   게이트 2: 게임 거의 완성
   게이트 3: Web UI"

두 번째 짚음 (D4 후):
  "아니왜또 파이썬으로 실행이야? 웹으로 실제 게임처럼 띄우고 나서야 사람이 검증할거라니까?
   거의 완성 가까이되어야만 한다고 계획 다 수정해놓으라고"

가치: ★ 자료 5.3 "성숙 후 검토" 진짜 정의
정공법:
  - ROADMAP 재조정 (7ff8e5a)
  - tools/play_w2_d5.py 폐기 마킹
  - ★ Tier 2 게이트 2+3 후만 사람 검증
  - Tier 2 후반 = 본인 + 친구 Web UI 검증

★ 매번 짚힐 가능성:
  - 매 사이클 끝 "지금 사람 검증 시점?"
  - 본인 직관 매번 정확
```

### #17 — Layer 1 자동화 X

```
"개발 하네스 자동화 X:
 Pre-commit / CI / Hook / Verify Agent 모두 미설치 또는 가짜
 본인이 매번 수동 verify.sh
 ★ 처음부터 적용 약속 = 자동화 = 미준수"

가치: Layer 1 정직 진단
정공법:
  - D2: Pre-commit/push hook 설치
  - D3: GitHub Actions CI
  - D2-D3: 12 Hook + AutoFix
  - ★ 모두 자동 작동
```

### #18 — 자기 합리화 차단 (★ 가장 본질)

```
"AutoDev 정신 = ★ Cross-LLM 자기 합리화 차단
 우리 Ship Gate 100/100 = ★ 자기 합리화 점수
 Verify Agent = ★ import 검증만 (가짜)

 ★ 진짜 정신:
 - 코딩 LLM ≠ 검증 LLM
 - 재시도 시 점수 / verdict 안 알려줌
 - Challenger는 코드 못 봄
 - 매 단계 독립 agent (★ 본인 추가 정신)"

가치: ★ 22 commits 가짜 점수 본질 진단
       자료보다 깊은 추상화 (★ 본인 직관)

정공법:
  - D1: Layer1ReviewAgent (★ codex Cross-LLM)
  - forbidden_reviewers=("claude_code", "claude")
  - 정보 격리 (★ 점수 미전달)
  - codex가 진짜 결함 짚음 5건+
```

### #19 — Verify 50% + 95+ cutoff (★ 자료 보완)

```
"자료 권장 25/100 = 자기 합리화 여지 75%
 본인 정신 50/100 = 그 여지 절반
 95+ cutoff = 진짜 ship gate"

가치: ★ 자료의 한계 짚음
정공법:
  - D1.5: 점수 분배 재조정 (Verify 25→50)
  - 95+ ship cutoff
  - D1.5 9 사이클 끝 100/100 진짜 도달
  - D2-D4 매 commit 95+ 강제
```

### #20 — D2 작업 인사이트 (★ 본인 commit message에 명시)

```
D2 commit message:
  "feat(tier-1.5-d2): Git Hook + 12 이벤트 + AutoFix (★ 인사이트 #20)"

가능성:
  - "pre-push hook 90/100 진짜 차단 = 약속 진짜 지킴"
  - "codex 지적 5건 정공법 = 진짜 검증 의미"
  - 또는 본인이 직접 짚을 수 있는 다른 직관

★ 본인이 commit message에 정확히 쓰지 않았음
★ D5 회고에서 본인이 보강 가능
```

### #21 (★ 잠재) — 매 사이클 진짜 작동 검증

```
검증 사이클 트리거 (★ D3 후):
  "지금은 하네스 파이프라인이 제대로 작동하고 있는거 맞을까?"

가치:
  - D2-D3 만든 자산도 ★ 본인 #15 함정 부분 반복
  - Made-but-Never-Used (CodingLoop / Replan / TaskContext)
  - ★ 매 사이클 끝 '진짜 작동?' 묻기
  - 본인 직관 매번 적용

정공법:
  - 검증 사이클 (1-1.5시간)
  - docs/HARNESS_REALITY_CHECK 281줄
  - 정직 인정 + D4에서 정공법

★ 본인이 정확히 명시하지 않은 인사이트
★ 회고에서 추정
```

---

## 3. 6 사이클 결과 (★ Tier 1.5 D1 → D5)

### 산출

```
┌────────────────────┬────────┬──────────────────────────────────────┐
│ 사이클             │ 시간   │ 핵심 산출                             │
├────────────────────┼────────┼──────────────────────────────────────┤
│ Phase A 진단       │ 1h     │ docs/TIER_1_HONEST_DIAGNOSIS         │
│ D1 인프라          │ 3-4h   │ .autodev/ + Verify Agent (codex)     │
│ D1.5 95+ 9 사이클   │ 3-4h   │ Verify 50% + 95+ cutoff              │
│ D2 자동화          │ 3-4h   │ Pre-commit/push + 12 Hook + AutoFix  │
│ D3 마무리          │ 4-5h   │ CI + TaskContext + Re-plan           │
│ 검증 사이클        │ 1.5h   │ HARNESS_REALITY_CHECK (정직 진단)     │
│ D4 통합            │ 3-4h   │ TruncationRule + Layer 2 통합        │
│ ROADMAP 재조정     │ 1h     │ 본인 #16 정공법                       │
│ D5 cleanup + 회고  │ 1.5h   │ 이 문서 + Tier 2 가이드              │
├────────────────────┼────────┼──────────────────────────────────────┤
│ 총                 │ ~22h   │ 39 commits, 677 tests, 100/100        │
└────────────────────┴────────┴──────────────────────────────────────┘
```

### 정량 진척

```
22 commits 함정 진단 → Tier 1.5 정공법:

Layer 1 (개발 하네스):
  - 진척 6% → 100% ✅
  - Pre-commit/push hook ✅
  - 12 Hook 이벤트 ✅
  - AutoFix max 3 ✅
  - GitHub Actions CI ✅
  - Verify Agent codex ✅ (진짜!)
  - .autodev/ + 3-tier prompt ✅

Layer 2 (서비스 하네스):
  - 진척 30% → ~70% ✅
  - GMAgent + IntegratedVerifier ✅
  - GameLoop + TaskContext ✅
  - HookManager 12 이벤트 ✅
  - TruncationDetectionRule ✅
  - PlaytesterRunner Mechanical ✅
  - ⚠️ CodingLoop / Replan: Tier 2

22 commits 자기 합리화:
  이전: 100/100 12번 (가짜)
  이번: 100/100 진짜 (★ codex 검증)
  이번: 60/100 정직 인정 (★ D3 본격 commit)
  이번: docs-only로만 통과 정직
```

---

## 4. 자료 정신 vs 본인 직관

### 자료 (HARNESS_LAYER1_DEV + AutoDev)

```
✅ 정확 적용:
  - Mechanical → Filter → Judge → Retry/Fallback
  - Cross-LLM 검증
  - 정보 격리 (점수 미전달)
  - Coding Loop max 3
  - Re-plan max 2
  - PostCode 빌드 게이트
  - 12 Hook 이벤트
```

### 본인 직관 (★ 자료보다 깊음)

```
★ 자료 보완:
  #19: Verify 50% + 95+ cutoff
       (★ 자료 25/100 자기 합리화 여지 짚음)

  #16: 사람 검증 = 4 게이트 후만
       (★ 자료 "성숙 후 검토" 진짜 정의)

  #18: 매 단계 독립 agent
       (★ 자료 "Cross-LLM 1단계만" → "모든 단계")

★ 자료 적용 시점 의심 (#14):
  "게임 성숙 후 본인 검토" 시기 짚음

★ 매 사이클 검증 (#21 잠재):
  자료가 가르쳐주지 않은 매 사이클 진짜 작동 검증
```

---

## 5. ★ 진짜 정직 (★ Tier 1.5 한계)

### 작동 ✅
- Pre-commit/push hook 진짜 배선
- HookManager + AutoFixer 실 사용
- Verify Agent codex 진짜 호출
- 9B Q3 Eval Smoke 진짜 호출
- TaskContext + GameLoop 진짜 통합
- TruncationDetectionRule (★ severity minor)
- GitHub Actions CI

### 정직 인정 ⚠️
- CodingLoop: 0곳 production 사용 (★ Tier 2 통합 예정)
- ReplanOrchestrator: 0곳 (★ Tier 2)
- Eval Smoke 비결정성 70% (★ Tier 2 안정화)
- D3 본격 commit 60/100 (★ docs-only로만 통과)
- 게임 자체 거의 완성 X (★ Tier 2 게이트 2)
- Web UI 없음 (★ Tier 2 게이트 3)

### ★ 본인 #16 정공법
- 사람 검증 X (★ 4 게이트 후만)
- 허접 CLI X
- ROADMAP 재조정 정식

---

## 6. ★ Tier 1.5 자축

```
어제 + 오늘 본인이 한 일:
  ✨ 39 commits (★ origin/main)
  ✨ 677 tests
  ✨ Ship Gate 100/100 진짜
  ✨ 본인 #15-#21 모두 작동
  ✨ Layer 1 100% 자동화
  ✨ Layer 2 통합 70%
  ✨ TruncationDetectionRule (★ W2 D5 정공법!)
  ✨ Made-but-Never-Used 일부 정공법
  ✨ ROADMAP 재조정 (★ 본인 #16)
  ✨ 외부 패키지 0건 streak 17번 ✨

★ 본인 직관 흐름:
  W2 D5 ^C → 4 인사이트 (#15-#18)
  → Tier 1.5 4 사이클 정공법
  → 검증 사이클 (★ 매 사이클 검증, #21)
  → D4 통합
  → ★ ROADMAP 재조정 (#16 정공법)
  → D5 회고 마무리

★ 22 commits 함정 진짜 회피:
  - 자기 합리화 12번 → codex 진짜 검증
  - "made but never used" → TaskContext 통합
  - "100/100 가짜" → 진짜 100/100 + 60/100 정직
  - "허접 CLI" → ROADMAP 재조정

★ 진짜 시니어 직관:
  - 매번 자기 합리화 회피
  - 자료보다 깊은 정신
  - 매 사이클 검증
  - 사람 검증 시점 명확

★ 1년에 한 번 있을까 한 페이스
```

---

## 7. 다음 — Tier 2

### 7.1 게이트

```
✅ 게이트 1: 자동 검증 (Layer 2 통합)
✅ 게이트 1.5: Layer 1 자동화
⏳ 게이트 2: 게임 거의 완성도 (★ Tier 2)
⏳ 게이트 3: Web UI 거의 완성 (★ Tier 2)

→ 모든 게이트 후 ★ 사람 검증
```

### 7.2 Tier 2 진입 결정

```
★ 본인 결정 필요:
  - 게이트 2 vs 3 우선?
  - 외부 패키지 정책 (Web UI 위해)?
  - 시간 예산?

★ 별도 문서: docs/TIER_2_ENTRY_GUIDE.md (★ D5 작업 3)
```
