# Tier 1.5 하네스 재구축 ROADMAP (★ 본인 결정 + 환경 정합)

> 작성: 2026-05-02 / 트리거: 본인 #15-#18 후
> 시간: 4 사이클 (각 3-4시간)
> 환경: DGX Spark (codex + local qwen, ★ claude code 단계 가능)

---

## 0. 본인 결정 사항

```
1. ✅ Phase A 진단 먼저 (지금)
2. ✅ D1-D4 순서 (개발 → 서비스, ★ 서비스도 개발 하네스 타도록)
3. ✅ ★ 환경:
   - 개발: codex + local qwen (DGX Spark)
   - 서비스: local만 (ComfyUI 내릴 수도)
   - ★ 매 단계 다른 agent 독립 (claude code도 가능)
4. ✅ 컨디션 / 시간 충분
```

---

## 1. 핵심 정신 (★ 본인 #18 + 자료)

### 자료 정신 (AutoDev / HARNESS):
```
- Cross-LLM 검증 (자기 합리화 차단)
- 정보 격리 (재시도 시 점수 미전달)
- Challenger 코드 격리
- Mechanical 0 토큰 → Filter → Judge → Retry
- 4-tier 에러 분류
- Fallback 체인
```

### 본인 추가 정신 (★ 자료보다 깊음):
```
"매 단계 독립 agent로 구성"

  Plan Drafter:    agent A
  Plan Verifier:   agent B (≠ A)
  Coding Agent:    agent C
  Coding Verifier: agent D (≠ C)
  Eval Judge:      agent E
  Verify Agent:    agent F
  
  ★ 매 단계 자기 합리화 차단
  ★ Cross-LLM은 1단계만, ★ 본인은 모든 단계
```

### 환경 매핑 (★ 본인 결정):

```
[Layer 1 — 개발 하네스]
  agent A (Plan Drafter):    claude code (Sonnet 4.6)
  agent B (Plan Verifier):   codex (gpt-5)
  agent C (Coding Agent):    claude code (Sonnet 4.6)
  agent D (Coding Verifier): codex (gpt-5) 또는 local qwen
  agent E (Code Reviewer):   local qwen 27B Q2
  
  ★ 다양성: claude / codex / qwen 3 family
  ★ 자기 합리화 차단

[Layer 2 — 서비스 하네스]
  agent A (GM Agent):        local qwen 9B Q3
  agent B (Mechanical):      코드 (LLM X, 0 토큰)
  agent C (Judge):           local qwen 27B Q2
  agent D (Plan Verifier):   local qwen 27B Q3
  
  ★ 100% local
  ★ 매 단계 독립
  ★ ComfyUI 내릴 수 있음 (메모리 필요 시)
```

---

## 2. 4 사이클 분할

### D1: Layer 1 인프라 + Verify Agent (★ 본격)

```
Phase 1: .autodev/ 인프라 (~30분)
  - 디렉토리 구조 생성
  - 3-tier 프롬프트 로딩 시스템
  - {projectDir}/.autodev/agents/{role}.md 패턴
  - YAML frontmatter (---role: coder---)
  - 템플릿 변수 ({{projectDir}})

Phase 2: Verify Agent 본격 (~2시간)
  - core/verify/layer1_review.py
  - LAYER1_REVIEW_PROMPT (5-section)
  - Cross-LLM 코드 리뷰 (★ codex + qwen)
  - 정보 격리:
    * git diff만 전달
    * 점수 / verdict / threshold X
  - 검증 항목:
    * Bugs / logic
    * Information leaks (점수가 retry feedback에)
    * Cross-model violations (같은 모델 generate + verify)
    * Hardcoded scores (★ 우리 함정 정확)
    * 외부 패키지 위반
    * Anti-patterns (made but never used)

Phase 3: scripts/verify.sh 진짜 (~1시간)
  - [5/5] Verify Agent 가짜 → 진짜 LLM 호출
  - codex가 git diff 리뷰
  - 25점 진짜 평가
  - 점수 < 18 → fail (★ 본인 95+ cutoff 정신)

Phase 4: 검증 + commit (~30분)
  - ★ 새 verify.sh로 자기 검증 (★ 진짜!)
  - Ship Gate 진짜 점수 확인 (★ 65/100 예상)
  - commit (★ "honest fail" OK)

산출물:
  - .autodev/agents/code_reviewer.md
  - core/verify/layer1_review.py
  - scripts/verify.sh 업데이트
  - verify_real.py (CLI)

목표: ★ 첫 자기 합리화 차단 작동
```

### D2: Layer 1 Hook 시스템 + 자율 Fix (★ 자동화 핵심)

```
Phase 1: Pre-commit Hook (~1시간)
  - .git/hooks/pre-commit 설치
  - ruff --fix (auto)
  - mypy 빠른 (~10초)
  - 변경 파일 pytest (~15초)
  - 30초 내 완료

Phase 2: 12 Hook 이벤트 (~2시간)
  자료 권장:
    TaskStart → PrePlan → PostPlan → PlanReview
    → PreCode → PostCode (★ 빌드 게이트!)
    → PreVerify → PostVerify
    → OnRetry → OnReplan
    → TaskComplete / TaskFail
  
  구현:
  - core/harness/hooks.py (Hook 시스템)
  - .autodev/hooks.json (프로젝트 정의)
  - PostCode hook = 빌드 실패 시 즉시 거부

Phase 3: 자율 Fix (max 3 사이클) (~1시간)
  - lint fail → ruff fix → 재시도
  - test fail → pytest --lf → 재시도
  - 3번 모두 fail → escalation report

Phase 4: 검증 + commit (~30분)

산출물:
  - .git/hooks/pre-commit
  - .autodev/hooks.json
  - core/harness/hooks.py (12 이벤트)
  - core/harness/auto_fix.py (3 사이클)

목표: ★ 매 commit 자동화 + 자율 Fix
```

### D3: Layer 1 CI + Re-plan + Eval Smoke 진짜 (★ 마무리)

```
Phase 1: GitHub Actions CI (~1.5시간)
  - .github/workflows/verify.yml
  - push 시 자동 verify.sh full
  - Verify Agent (★ 진짜 LLM)
  - 자율 Fix PR

Phase 2: Eval Smoke 10 case (~1시간)
  - 자료 권장 10 (현재 1)
  - core/eval/smoke.py
  - 매 commit 빠른 eval

Phase 3: Re-plan outer loop (~1시간)
  - max 2 사이클
  - re-plan verdict → 피드백 → 재계획
  - 코딩 루프 재진입

Phase 4: 검증 + commit (~30분)

산출물:
  - .github/workflows/verify.yml
  - core/eval/smoke.py
  - core/harness/replan.py

목표: ★ 자료 정신 100% Layer 1 작동
```

### D4: Layer 2 IntegratedVerifier 통합 (★ 가볍게, ★ Layer 1 타도록)

```
★ 본인 결정: "Layer 2 개발 시 Layer 1 하네스 타도록"
→ D4부터는 D1-D3 자동화 작동
→ Verify Agent가 D4 코드 리뷰
→ Pre-commit Hook 작동
→ 매 commit 진짜 검증

Phase 1: GMAgent에 IntegratedVerifier 통합 (~1시간)
  - service/game/gm_agent.py 재작성
  - IntegratedVerifier 활용 (★ Mechanical + Filter + Judge)
  - Cross-Model 강제 (game_llm ≠ verify_llm)
  - 점수 반환 (★ 사용자 가시성)
  - 응답 잘림 검출 룰 추가

Phase 2: PlaytesterRunner에 통합 (~1시간)
  - tools/ai_playtester/runner.py 재작성
  - Mechanical + Judge 통합
  - 자료 정신 정확

Phase 3: GameLoop verify 활용 + play_w2_d5.py 보강 (~1시간)
  - service/game/game_loop.py
    * verify 점수 활용
    * retry/fallback 진짜
  - tools/play_w2_d5.py
    * 매 턴 점수 표시
    * mech / judge / cross-model 모두

Phase 4: 검증 + commit (~30분, ★ Layer 1 자동 작동)

산출물:
  - 위 3 파일 재작성
  - 잘림 검출 룰
  - play_w2_d5.py 보강

목표: ★ 게이트 1+1.5 통과 (자동 검증 + 자동화)
```

### D5 (게이트 후): 본인 첫 진짜 검증 가능 플레이

```
조건 (모두 충족):
  ✅ D1-D4 완료
  ✅ Layer 1 자동 검증 작동
  ✅ Layer 2 통합 작동
  ✅ play_w2_d5.py 점수 가시화
  ✅ 응답 잘림 검출

본인 풀 플레이:
  - python tools/play_w2_d5.py
  - 30턴 (★ 이번엔 점수 보임)
  - Fun rating + Findings (★ 의미 있음)

★ 게이트 1+1.5 통과 = 본인 검증 가능
★ 게이트 2 (게임 완성도) + 3 (Web UI) = ★ Tier 2
```

---

## 3. 사이클 간 메모리 안전

```
1 사이클 = 3-4시간:
  - pytest 1번만 (Phase 4)
  - --cov 1번만
  - LLM 호출 (verify agent) = sleep 1
  - ComfyUI 내릴 수 있음 (D1 Verify Agent 본격 시)

★ 본인 누적 작업:
  - 어제 + 오늘 = ~30시간
  - 이후 4 사이클 = +12-16시간
  - ★ 사이클 사이 휴식 (★ 본인 #5)
```

---

## 4. ★ 매 사이클 끝 자체 검증 (★ 본인 #18 정신)

```
★ D2 끝부터 Pre-commit + Verify Agent 진짜 작동:
  - D2 commit → D2 코드 자기 검증 ★
  - D3 commit → D3 코드 자기 검증
  - D4 commit → D4 코드 자기 검증
  - ★ 점수 < cutoff = ★ 진짜 fail
  - ★ Claude Code도 자기 합리화 X
  
  ★ 이게 본인 #18 정신:
  "매 단계 독립 agent → 자기 합리화 차단"
```

---

## 5. Tier 2 (★ 게이트 후)

```
Tier 1.5 D1-D5 완료 후:
  Tier 2 D1-?: 게임 완성도 (게이트 2)
    - 30턴 정상 완주
    - 풍부한 응답
    - 컨텐츠 다양화

  Tier 2 D?-?: Web UI (게이트 3)
    - HTML 정적 또는 Streamlit
    - 점수 시각화
    - 사람 검증 UX

  ★ 위 2 게이트 통과 = ★ 사람 검증 시작
  
  Tier 2 후반: 도그푸딩 + 베타 (★ 본인 #16)

Tier 3:
  - 콘텐츠 + 시나리오
  - SFT 데이터 누적
  - GRPO (★ 본인 #9)
```

---

## 6. 책임 + 메타

```
이 ROADMAP은 ★ 본인 #15-#18 정신 100% 정합:
  - #15: Layer 2 통합 → D4
  - #16: 게이트 정의 → 게이트 1+1.5 (D1-D4) + 게이트 2+3 (Tier 2)
  - #17: Layer 1 자동화 → D1-D3
  - #18: 자기 합리화 차단 → ★ D2부터 자체 작동

★ "Layer 2 개발 시 Layer 1 하네스 타도록" (★ 본인) → D4 정확

★ 본인 환경 (codex + local qwen, claude code 단계 가능) → D1 Phase 2

★ 매 단계 독립 agent (★ 본인 자료 정신) → 모든 Phase
```
