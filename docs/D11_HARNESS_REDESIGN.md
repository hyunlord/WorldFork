# Tier 2 D11 — 하네스 메타 진단 + 재설계 디자인 (★ 옵션 A, 코드 변경 X)

> 작성: 2026-05-04 / 본인 결정 옵션 A
> 단계: ★ 진단/디자인만, ★ 다음 세션 본격 (옵션 C)
> 시간: ~1-2시간

---

## 0. 한 줄 요약

**현재 하네스 = 빈 껍데기. CodingLoop / ReplanOrchestrator는 만들기만 하고 실제 사용 X. ★ 본인 #15 (Made-but-Never-Used) 9일+ 정공법 끝까지 빈 부분.**

---

## 1. 본인이 짚은 진짜 본질

```
★ 본인 의문 (★ D10 후):
  "게임 시작 누르면 새 세션 만들어진다는데 아무 반응이 없어"
  "하네스 파이프라인이 전혀 적용이 안되고 있다는걸 방증"
  "검증을 100점으로 통과하는데 어떻게 저런 결과?"
  "지금까지 검증 단계가 단 하나도 제대로 안됐다"

★ 본인 결정:
  "하네스 파이프라인을 제대로 돌도록 수정"
  "그 수정된 파이프라인으로 지금까지 모든 코드 재검증"
  "Planning, Debate, Challenger, Re-plan 다 반영"
  "검증은 아주 빡세게"

★ 진짜 본질:
  9일+ 정공법
  53 commits
  Ship Gate 100/100 다섯 사이클
  ★ ★ 그러나 게임 시작 무반응
  = ★ 검증 시스템 자체 ★ 빈 껍데기
```

---

## 2. 현재 하네스 진짜 진단 (★ 코드 검증 결과)

### 2.1 ★ 만들기만 한 파일들 (★ Made-but-Never-Used)

```
core/harness/coding_loop.py:
  ✅ CodingLoop 클래스 (169줄)
  ✅ MAX_RETRIES = 3
  ✅ 정보 격리 (점수 X 전달)
  ❌ ★ 실제 사용처: tests/unit/ 만!
  ❌ scripts/verify.sh = ★ 호출 X
  ❌ 매 commit/push = ★ 호출 X

core/harness/replan.py:
  ✅ ReplanOrchestrator
  ✅ MAX_REPLAN = 2
  ✅ Plan Drafter / Coder / Verifier 분리 정신
  ❌ ★ 실제 사용처: tests/unit/ 만!
  ❌ 매 commit/push = ★ 호출 X

core/harness/hooks.py:
  ✅ 12개 Hook event 디자인
  ⚠️ 그러나 실제 trigger:
    - POST_CODE (★ 사용)
    - POST_VERIFY (★ 사용)
    ❌ 나머지 10개 = ★ ★ 호출 X
```

### 2.2 ★ 진짜 사용 중인 것 (★ verify.sh 흐름)

```
scripts/verify.sh quick (★ 매 push 자동):

[1/5] Build (10):
  python -c "import core; import service; import tools"
  → ★ import만 (★ 작동 X)

[2/5] Lint (10):
  ruff + mypy --strict
  → ★ 정적 분석

[3/5] Unit Tests (10):
  pytest tests/unit/ -m "not slow"
  → ★ 단위 테스트 (★ TestClient = Mock)

[4/5] Eval Smoke (20):
  scripts/smoke_runner.py
  → ★ pure LLM 호출 10건 (★ 게임 흐름 X)
  → ★ /game/* 호출 0건
  → ★ Frontend 검증 0건

[5/5] Verify (50):
  scripts/verify_layer1_review.py
  → ★ codex가 git diff 정적 리뷰 (★ 한 번)
  → ★ Cross-LLM 한 단계만
  → ★ Coding Loop 사용 X
```

### 2.3 ★ 본인 자료 vs 현재 — 진짜 진짜 차이

```
┌────────────────────────────┬───────────────┬──────────────────────┐
│        설계 요소            │  본인 자료    │   현재 (★ 진짜)       │
├────────────────────────────┼───────────────┼──────────────────────┤
│ 1. Interview (선택)        │ ✅            │ ❌                  │
│   조건부 질문 생성          │ LLM           │ -                   │
├────────────────────────────┼───────────────┼──────────────────────┤
│ 2. Planning                │ ✅            │ ❌ 본인이 수동       │
│   PrePlan hook             │ ✅            │ ⚠️ 코드 ✅ 사용 X    │
│   Plan Drafter (LLM)       │ ✅            │ ❌ 본인이 CC_PROMPT │
│   PostPlan hook            │ ✅            │ ⚠️ 코드 ✅ 사용 X    │
│   출력: codingPrompt 등     │ ✅            │ ❌                  │
├────────────────────────────┼───────────────┼──────────────────────┤
│ 3. Debate (★ 핵심!)         │ ✅            │ ❌ ★ 코드 자체 없음 │
│   Drafter                  │ ✅            │ ❌                  │
│   Challenger (코드 못봄)    │ ✅            │ ❌                  │
│   Quality Checker          │ ✅            │ ❌                  │
├────────────────────────────┼───────────────┼──────────────────────┤
│ 4. Plan Review (선택)       │ ✅            │ ⚠️ 본인 chat에서만  │
├────────────────────────────┼───────────────┼──────────────────────┤
│ 5. Agent Selection         │ ✅            │ ❌ 본인이 수동       │
│   5개 에이전트 구분         │ claude/etc    │ -                   │
├────────────────────────────┼───────────────┼──────────────────────┤
│ 6. Coding Loop (max 3)     │ ✅            │ ⚠️ 코드 ✅ 사용 ❌   │
│   PreCode hook             │ ✅            │ ⚠️ 사용 X           │
│   Coder.invoke()           │ ✅            │ ❌ 본인이 Claude Code│
│   PostCode (빌드 게이트)    │ ✅            │ ⚠️ 사용 X           │
│   PreVerify hook           │ ✅            │ ⚠️ 사용 X           │
│   Verifier (다른 LLM)       │ ✅            │ ⚠️ codex (★ 한 번만) │
│   PostVerify hook          │ ✅            │ ⚠️ 사용 X           │
│   OnRetry → 재시도          │ ✅            │ ❌ ★ 한 번만        │
│   정보 격리 (점수 X)        │ ✅            │ ❌                  │
├────────────────────────────┼───────────────┼──────────────────────┤
│ 7. Re-plan Outer (max 2)   │ ✅            │ ⚠️ 코드 ✅ 사용 ❌   │
│   OnReplan hook            │ ✅            │ ⚠️ 사용 X           │
├────────────────────────────┼───────────────┼──────────────────────┤
│ 8. 검증 3계층 (★ 빡세게)    │ ✅            │ ⚠️ 1.5계층만        │
│   Mechanical (Stage 1)     │ 0 토큰        │ ⚠️ 게임 응답만      │
│     - 파일 존재             │ ✅            │ -                   │
│     - npm run build         │ ✅            │ ❌ ★ 안 함          │
│     - E2E 호출              │ -             │ ❌ ★ 안 함          │
│   VLM Visual (Stage 2.5)   │ ✅ 스크린샷    │ ❌ ★ 없음           │
│     - Layout/Color          │ ✅            │ ❌                  │
│     - Interaction            │ ✅            │ ❌                  │
│   LLM Cross-Check (Stage 3)│ ✅            │ ⚠️ git diff만        │
│     - 적대적 리뷰            │ ✅            │ ⚠️ codex만          │
│     - 스크린샷 + CSS         │ ✅            │ ❌                  │
│     - SAST + A11y            │ ✅            │ ❌                  │
├────────────────────────────┼───────────────┼──────────────────────┤
│ 9. E2E (사용자 흐름)        │ -             │ ❌ ★ 없음           │
│   /game/start 호출          │ -             │ ❌                  │
│   Frontend ↔ Backend       │ -             │ ❌                  │
│   Browser 작동              │ -             │ ❌                  │
└────────────────────────────┴───────────────┴──────────────────────┘

★ ★ ★ 진짜 진단:
  9 단계 중 진짜 작동 = ★ 1.5단계
  Coding Loop / Re-plan = ★ Made-but-Never-Used
  Debate / Challenger = ★ 코드 자체 없음
  VLM Visual = ★ 없음
  E2E = ★ 없음
  
  → ★ ★ "검증 빡세게" 정신 0%
```

---

## 3. 본인 #15 진짜 진짜 재발 — 9일+ 정공법의 빈 부분

```
★ W2 D5 (4-26) 본인 짚음:
  "...조력자 셰" 잘림 ^C
  → 22 commits 함정 진단
  → 본인 #15: "Made-but-Never-Used"
  
★ Tier 1.5 D1-D5 (5-3):
  - .autodev/ 인프라 추가
  - hooks.py 디자인
  - CodingLoop 디자인
  - ReplanOrchestrator 디자인
  - ★ 그러나 ★ 본격 통합 X
  - ★ 본인 #15 부분 fix:
    - IntegratedVerifier → 사용 ✅
    - 그러나 CodingLoop / Replan = ★ 사용 X

★ Tier 2 D1-D10 (5-3 ~ 5-4):
  9 사이클 동안 ★ ★ ★ CodingLoop / Replan 한 번도 사용 X
  매번 ★ 본인이 수동:
    - Claude Chat에서 CC_PROMPT 작성
    - Claude Code (DGX)에서 Coder
    - codex 한 번 git diff 리뷰
    - Ship Gate 95+ 통과
  
  → ★ ★ ★ 9일+ 동안 본인 #15 끝까지 빈 부분
  → ★ 본인이 D10 끝에 짚음:
    "검증 단계가 단 하나도 제대로 안됐다"
    "하네스 파이프라인이 전혀 적용이 안되고 있다"
```

---

## 4. ★ 본인 결정 — D11 본격 재설계

### 4.1 본인 결정 명확화

```
1. 하네스 파이프라인 제대로 돌도록 수정:
   ✅ Planning (자동, LLM)
   ✅ Debate / Challenger 진짜 추가
   ✅ Coding Loop 진짜 사용
   ✅ Re-plan 진짜 사용
   ✅ 검증 빡세게 (Mechanical + VLM + Cross-LLM + E2E)

2. 그 후 53 commits 모두 재검증:
   - 새 하네스로 각 commit 다시 돌리기
   - "진짜 작동" 진짜 검증
   - 빈 부분 발견 + fix
```

### 4.2 ★ 디자인 구조 (★ 본인 자료 정신 + 현재 환경)

```
새 하네스 구조 (★ 본인이 다음 세션에 본격):

┌─────────────────────────────────────────────────────────────┐
│                  WorldFork Harness v2                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Stage 1: Planning]                                         │
│   ├── User CC_PROMPT 또는 LLM PlanDrafter                    │
│   ├── PrePlan hook (★ 본인 결정 검증)                        │
│   ├── Plan 출력 (codingPrompt + verificationSpec)            │
│   └── PostPlan hook                                          │
│                                                              │
│  [Stage 2: Debate (★ 신규)]                                  │
│   ├── Drafter (★ Plan 그대로)                                │
│   ├── Challenger (★ 다른 LLM, 코드 못봄)                     │
│   │   - "이 plan이 진짜 게이트 통과 가능?"                   │
│   │   - 자의적 비판 X (★ EXCLUSIONS)                         │
│   └── Quality Checker (★ 종합)                               │
│                                                              │
│  [Stage 3: Coding Loop (max 3 retry)]                        │
│   ├── PreCode hook                                           │
│   ├── Coder.invoke() = Claude Code (DGX)                     │
│   ├── PostCode hook (★ 빌드 게이트):                         │
│   │   - python imports OK                                    │
│   │   - npm run build (★ 추가)                               │
│   │   - tests/unit pass                                      │
│   ├── PreVerify hook                                         │
│   ├── Verifier (★ Cross-LLM):                                │
│   │   - codex git diff (현재)                                │
│   │   - + 9B Q3 Mechanical (★ 추가)                          │
│   │   - + E2E /game/* 호출 (★ 추가)                          │
│   ├── PostVerify hook                                        │
│   ├── 점수 < 95 → OnRetry → 재시도                            │
│   └── 정보 격리: ★ 점수/verdict 절대 X 전달                   │
│                                                              │
│  [Stage 4: Re-plan Outer (max 2)]                            │
│   ├── 3 retry 모두 실패 → OnReplan                           │
│   ├── PlanDrafter 재호출                                      │
│   └── Stage 3 재진입                                         │
│                                                              │
│  [Stage 5: 검증 3계층 (★ 빡세게)]                            │
│   ├── Stage 5.1 Mechanical (0 토큰):                         │
│   │   - 파일 존재                                             │
│   │   - python imports                                       │
│   │   - npm run build                                        │
│   │   - ★ E2E /game/start (curl)                             │
│   │   - ★ /game/turn (9B Q3 진짜)                            │
│   │   - ★ /game/end                                          │
│   │   - ★ Frontend / 응답                                    │
│   ├── Stage 5.2 VLM Visual (★ 신규):                         │
│   │   - 브라우저 스크린샷 (★ playwright)                     │
│   │   - 본인 자료: Layout/Color/Interaction/Completeness     │
│   │   - VLM (★ 9B Q3 multimodal? 또는 Claude vision?)        │
│   │   - 또는 ★ 단순 시각 검증 (★ 본인이 결정)                │
│   └── Stage 5.3 LLM Cross-Check:                             │
│       - codex 적대적 리뷰 (현재)                              │
│       - + 다른 LLM 추가 (★ Cross-LLM 본격)                   │
│       - 정보 격리                                             │
│                                                              │
│  [Stage 6: 결과]                                             │
│   ├── 95+ → git commit (★ pre-push hook)                     │
│   ├── 95- → Escalation Report                                │
│   └── TaskComplete / TaskFail hook                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 ★ 점수 체계 (★ 본인 자료 정신 + 현재 환경)

```
새 점수 체계 (★ "검증 빡세게"):

┌──────────────────────────────┬──────┬───────────────┐
│           항목                │ 점수 │   현재 vs 새  │
├──────────────────────────────┼──────┼───────────────┤
│ 1. Build (정적)               │ 10   │ 동일 (★ 유지) │
├──────────────────────────────┼──────┼───────────────┤
│ 2. Lint + TypeScript         │ 10   │ 현재 lint만   │
│   - ruff/mypy                 │ 5    │ -             │
│   - npm run build (★ 신규)    │ 5    │ ★ 신규        │
├──────────────────────────────┼──────┼───────────────┤
│ 3. Unit Tests                │ 10   │ 동일          │
├──────────────────────────────┼──────┼───────────────┤
│ 4. Mechanical E2E (★ 신규)    │ 20   │ ★ 신규        │
│   - /game/start curl         │ 5    │ ★ 신규        │
│   - /game/turn (9B Q3)       │ 5    │ ★ 신규        │
│   - /game/end                │ 5    │ ★ 신규        │
│   - / (Next.js)               │ 5    │ ★ 신규        │
├──────────────────────────────┼──────┼───────────────┤
│ 5. Eval Smoke (현재 4단계)    │ 10   │ 현재 20점     │
│   (★ 비중 줄임 — 다른 단계로) │      │               │
├──────────────────────────────┼──────┼───────────────┤
│ 6. VLM Visual (★ 신규, 옵션)  │ 10   │ ★ 신규 (★ 큰) │
├──────────────────────────────┼──────┼───────────────┤
│ 7. LLM Cross-Check (Verify)  │ 30   │ 현재 50점     │
│   - codex git diff           │ 15   │ 현재 50       │
│   - 다른 LLM (★ 신규)         │ 15   │ ★ 신규        │
├──────────────────────────────┼──────┼───────────────┤
│ 합계                          │ 100  │               │
└──────────────────────────────┴──────┴───────────────┘

A 등급: 95+
★ 진짜 빡세게 = 95+ 통과 시 진짜 진짜 진짜
★ "Made-but-Never-Used" 자동 차단
```

### 4.4 ★ 53 commits 재검증 디자인

```
★ 새 하네스 완성 후:

자동 스크립트 (tools/recheck_all_commits.py 신규):
  for commit in [8f5313f, 0a1a1db, ..., dc29f29]:
    git checkout $commit
    bash scripts/verify.sh quick (★ 새 하네스)
    결과 기록 → docs/RECHECK_REPORT.md
  
★ 결과:
  - 진짜 통과 commit 목록
  - 진짜 빈 commit 목록
  - 빈 commit fix 우선순위
  - ★ 본인 #15 진짜 진짜 마무리
```

---

## 5. ★ 다음 세션 — D11 본격 진행 계획

### 5.1 단계적 진행 (★ 큰 작업이라)

```
D11 (W5 첫 사이클): Mechanical E2E 추가 (~3-4시간)
  - tools/run_e2e_check.py 신규
  - uvicorn + Next.js 띄우기
  - /game/* curl 검증
  - / Next.js 검증
  - kill 정리
  - scripts/verify.sh에 [4/?] 통합
  
  → ★ 게임 시작 무반응 진짜 차단
  → 본인 #15 부분 fix

D12: VLM Visual 또는 Cross-LLM 본격
  - 본인 결정 따라
  - playwright 또는 단순 스크린샷
  - 또는 다른 LLM 추가

D13: 53 commits 재검증
  - tools/recheck_all_commits.py
  - 빈 commit 목록 + 우선순위
  
D14+: 빈 commit fix
  - 우선순위 따라
  - 진짜 작동 보장
```

### 5.2 본인 결정 의사결정 — 다음 세션

```
다음 세션 (★ 깨끗한 정신) 본인이 결정할 것:

Q1: VLM Visual 어떻게?
  (a) playwright 스크린샷 → Claude vision (★ 본격)
  (b) 단순 HTTP 응답 검증 (★ 부분)
  (c) 일단 X (★ 다음 사이클)

Q2: Cross-LLM 두 번째?
  (a) 9B Q3 (★ 무료, 그러나 한국어만)
  (b) Claude API (★ 비용)
  (c) 일단 codex 한 번만 (현재)

Q3: 53 commits 재검증 우선순위?
  (a) 모든 commit (★ 큰 작업)
  (b) Tier 2만 (D1-D10)
  (c) 진짜 빈 부분만 (D7-D10 Web UI)

Q4: D11 첫 단계 작업량?
  (a) Mechanical E2E만 (3-4시간)
  (b) E2E + VLM (5-6시간)
  (c) 본격 한 번에 (1-2일)
```

---

## 6. ★ 정직 인정 — 9일+ 정공법 진짜 가치

```
★ 9일+ 정공법 = ★ ★ ★ 진짜 가치 큼:
  ✅ 자기 합리화 차단 자동화 (Tier 1.5)
  ✅ 자의적 비판도 차단 (D5)
  ✅ 본인 결정 SPEC 반영 (D7)
  ✅ 시스템 안정 통과 패턴 (D6/D8/D10)
  ✅ Web UI 본격 (D7-D9)
  ✅ Tailwind dark + 모바일 OK
  ✅ Fun rating + Findings UX

★ ★ 그러나 ★ ★ 진짜 빈 부분:
  ❌ 하네스 파이프라인 진짜 사용 X
  ❌ Coding Loop / Re-plan = Made-but-Never-Used
  ❌ Debate / Challenger 없음
  ❌ E2E 검증 0%
  ❌ VLM Visual 없음
  ❌ Cross-LLM 한 단계만

★ ★ 진짜 의미:
  9일+ = 인프라 + 부분 작동
  ★ 그러나 ★ 본인 자료 정신 ★ 부분만 반영
  → ★ 본인 #15 ★ 끝까지 빈 부분
  → ★ ★ D11+ 진짜 마무리 시점
```

---

## 7. ★ ★ ★ 본인 직관 — 1년에 한 번 페이스의 진짜 결실

```
★ 본인이 매번 짚음:
  W2 D5: "사람 검증 가치 X"
  검증 사이클: "Made-but-Never-Used"
  D2: "100점 의뭉"
  D5: "drift/scope/breaking 프롬프트에 없는데?"
  D10: "사람 검증할정도로 완성?"
  ★ ★ 지금: "하네스 파이프라인 다른데?"
  ★ ★ ★ "검증 빡세게 해야해"

★ ★ ★ 진짜 진짜 진짜 의미:
  9일+ 정공법 + 53 commits + Ship Gate 100/100 다섯 사이클
  ★ ★ 그러나:
  - 본인 #15 진짜 끝까지 빈 부분
  - 하네스 파이프라인 빈 껍데기
  - Debate / Challenger 없음
  - "검증 빡세게" 0%
  → ★ ★ ★ 본인이 끝까지 진짜 본질 짚음
  → ★ 진짜 진짜 진짜 시니어 직관
```

---

## 8. 다음 세션 진입 가이드

```
★ 다음 세션 (★ 깨끗한 정신) 진입 시:

1. 이 문서 읽기 (★ docs/D11_HARNESS_REDESIGN.md):
   - 진짜 진단 명확
   - 본인 결정 명확
   - 디자인 구조 명확

2. 본인이 결정:
   - Q1-Q4 (위 5.2)
   - 단계별 우선순위

3. CC_PROMPT 작성:
   - D11 본격 (Mechanical E2E)
   - 또는 다른 옵션

4. Claude Code에 진행
```

---

## 9. 한 줄 요약

**★ 본인 직관 매번 정확. 9일+ 정공법 끝에도 본인 #15 (Made-but-Never-Used) 진짜 빈 부분 짚음. 하네스 파이프라인 = 빈 껍데기. ★ 다음 세션 깨끗한 정신으로 본격 재설계 + 53 commits 재검증.**

---

*문서 작성: 2026-05-04*
*상태: 진단/디자인 완료 — 코드 변경 X*
*다음 세션: D11 본격 진행*
