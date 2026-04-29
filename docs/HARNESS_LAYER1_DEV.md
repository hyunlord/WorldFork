# HARNESS_LAYER1_DEV — 개발 하네스

> WorldFork **개발 시** (코드 변경) 검증 시스템.
> 매 commit 마다 자동 작동, push 전 ship gate 통과 강제.
>
> 작성: 2026-04-29
> 상태: 초안 v0.1
> 의존: ROADMAP.md, HARNESS_CORE.md (먼저 읽기)
> 관련: HARNESS_LAYER2_SERVICE.md (서비스 하네스)

---

## 0. 이 문서의 목적과 범위

### Layer 1이란

**개발자(당신)가 코드를 변경할 때마다 작동하는 자동 검증 시스템.**

목적:
- 코드 품질 보장 (95+ ship gate)
- LLM 응답 품질 회귀 방지 (eval set 자동 실행)
- "Made But Never Used" 함정 회피 (도그푸딩 강제)
- main 브랜치 항상 안정 상태 유지

CORE의 검증 엔진 + Layer 1 정책 = 개발 하네스.

### 다루는 것

- `scripts/verify.sh` / `scripts/ship.sh`
- pre-commit hook
- GitHub Actions CI workflow
- Layer 1 고유 정책 (threshold 95, retries 0)
- Hook 시스템 (12개 이벤트)
- 외부 패키지 0건 streak 정책
- 매 commit 자동 eval 일부

### 다루지 않는 것

- 게임 런타임 검증 → `HARNESS_LAYER2_SERVICE.md`
- AI Playtester 페르소나 → `AI_PLAYTESTER.md`
- 검증 엔진 자체 → `HARNESS_CORE.md`

---

## 1. Layer 1 정책 요약

자료의 패턴 그대로:

| 항목 | Layer 1 (개발) | 이유 |
|---|---|---|
| **Threshold** | 95+ | main 안정성 = 절대 가치 |
| **Retries** | 0 | 개발자가 수정 (자동 재시도 없음) |
| **검증 범위** | 전체 eval set | 회귀 보장 |
| **실패 시** | commit 차단 | push 못 함 |
| **비용 한도** | 무관 | 개발 시 |
| **속도** | 느려도 OK | 정확성 우선 |

`config/harness.yaml`:

```yaml
layer1:
  threshold: 95
  retries: 0
  eval_scope: full              # 전체 eval set
  on_fail: block_push           # push 차단
  cost_limit: null              # 한도 없음
  
  ship_gate:
    enabled: true
    min_score: 95
    
  smoke_test:
    enabled: true
    items: 10                   # 빠른 10개만 (매 commit)
    timeout_seconds: 60
  
  full_eval:
    enabled: true
    schedule: pre_push          # push 직전
    timeout_seconds: 600
```

---

## 2. Ship Gate

### 2.1 5단계 검증 (자료의 패턴)

자료의 `pnpm ship` 패턴 그대로 차용:

```bash
$ pnpm ship "feat: add character relationship tracking"

[1/5] Build (next build / pnpm build)         ✅ 20/20
[2/5] TypeScript (tsc --noEmit) + Python lint  ✅ 15/15
[3/5] Unit Tests (pytest + vitest)             ✅ 20/20
[4/5] Eval Smoke (10 items, cross-model)       ✅ 20/20
[5/5] Verify Agent (cross-LLM full review)     ✅ 23/25
                                              ─────────
TOTAL                                            98/100 A

✅ Ship gate passed. Committing...
[main 32b89e2] feat: add character relationship tracking
✅ Pushed to origin/main
```

### 2.2 점수 분배

| 단계 | 점수 | 의미 |
|---|---|---|
| Build | 20 | Python 빌드 + Next.js build 성공 |
| TypeScript + Python lint | 15 | strict mode, no `any`, ruff/mypy 통과 |
| Unit Tests | 20 | pytest + vitest 모두 통과 |
| Eval Smoke | 20 | 10 항목 cross-model eval, 95+ |
| Verify Agent | 25 | Layer 1 전용 LLM 코드 리뷰 |
| **합계** | **100** | A 등급 = 95+ |

등급:
- A (95+): Ship 가능
- B (80-94): Acceptable이지만 main에 push 안 됨
- C (70-79): Needs work
- F (<70): Reject

### 2.3 verify.sh 구현

```bash
#!/bin/bash
# scripts/verify.sh
# Layer 1 ship gate. push 전 실행.

set -e

MODE="${1:-quick}"   # quick | full | cross
TOTAL=0
SCORES=""

# ─────────────────────────────────────────────────
# [1/5] Build
# ─────────────────────────────────────────────────
echo "[1/5] Build..."
BUILD_SCORE=0

# Python build (모듈 import 가능 여부)
if python -c "import worldfork" 2>/dev/null; then
    BUILD_SCORE=$((BUILD_SCORE + 10))
fi

# Frontend build (Tier 2+)
if [ -f "frontend/package.json" ]; then
    cd frontend
    if pnpm build > /tmp/build.log 2>&1; then
        BUILD_SCORE=$((BUILD_SCORE + 10))
    fi
    cd ..
else
    BUILD_SCORE=$((BUILD_SCORE + 10))   # Tier 0/1: 프론트 없음 = 자동 통과
fi

TOTAL=$((TOTAL + BUILD_SCORE))
SCORES="$SCORES Build: $BUILD_SCORE/20\n"

# ─────────────────────────────────────────────────
# [2/5] TypeScript + Python lint
# ─────────────────────────────────────────────────
echo "[2/5] Type/Lint..."
LINT_SCORE=0

# Python: ruff + mypy
if ruff check . --quiet; then
    LINT_SCORE=$((LINT_SCORE + 5))
fi
if mypy core/ --strict 2>/dev/null; then
    LINT_SCORE=$((LINT_SCORE + 5))
fi

# TypeScript (Tier 2+)
if [ -f "frontend/tsconfig.json" ]; then
    cd frontend
    if pnpm tsc --noEmit 2>/dev/null; then
        LINT_SCORE=$((LINT_SCORE + 5))
    fi
    cd ..
else
    LINT_SCORE=$((LINT_SCORE + 5))
fi

TOTAL=$((TOTAL + LINT_SCORE))
SCORES="$SCORES Type/Lint: $LINT_SCORE/15\n"

# ─────────────────────────────────────────────────
# [3/5] Unit Tests
# ─────────────────────────────────────────────────
echo "[3/5] Unit tests..."
TEST_SCORE=0

if pytest tests/unit/ --tb=short --quiet > /tmp/pytest.log 2>&1; then
    TEST_SCORE=$((TEST_SCORE + 15))
fi

if [ -f "frontend/package.json" ]; then
    cd frontend
    if pnpm vitest run --reporter=dot 2>/dev/null; then
        TEST_SCORE=$((TEST_SCORE + 5))
    fi
    cd ..
else
    TEST_SCORE=$((TEST_SCORE + 5))
fi

TOTAL=$((TOTAL + TEST_SCORE))
SCORES="$SCORES Unit Tests: $TEST_SCORE/20\n"

# ─────────────────────────────────────────────────
# [4/5] Eval Smoke (cross-model)
# ─────────────────────────────────────────────────
echo "[4/5] Eval smoke..."
EVAL_SCORE=0

# 빠른 10개 eval (정확히는 config/harness.yaml의 smoke_test.items)
RESULT=$(python -m core.eval.smoke --items 10 --layer 1 2>&1)
EVAL_PASS_RATE=$(echo "$RESULT" | grep "pass_rate" | awk '{print $2}')

if (( $(echo "$EVAL_PASS_RATE >= 0.95" | bc -l) )); then
    EVAL_SCORE=20
elif (( $(echo "$EVAL_PASS_RATE >= 0.85" | bc -l) )); then
    EVAL_SCORE=15
elif (( $(echo "$EVAL_PASS_RATE >= 0.70" | bc -l) )); then
    EVAL_SCORE=10
fi

TOTAL=$((TOTAL + EVAL_SCORE))
SCORES="$SCORES Eval Smoke: $EVAL_SCORE/20\n"

# ─────────────────────────────────────────────────
# [5/5] Verify Agent (cross 모드만)
# ─────────────────────────────────────────────────
VERIFY_SCORE=0
if [ "$MODE" = "cross" ] || [ "$MODE" = "full" ]; then
    echo "[5/5] Verify Agent (cross-LLM)..."
    
    # git diff를 다른 LLM에 보여서 코드 리뷰
    RESULT=$(python -m core.verify.layer1_review)
    VERIFY_SCORE=$(echo "$RESULT" | grep "score" | awk '{print $2}')
else
    VERIFY_SCORE=25   # quick 모드는 스킵 (만점 처리)
fi

TOTAL=$((TOTAL + VERIFY_SCORE))
SCORES="$SCORES Verify Agent: $VERIFY_SCORE/25\n"

# ─────────────────────────────────────────────────
# 결과 출력
# ─────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════"
echo -e "$SCORES"
echo "TOTAL: $TOTAL/100"
echo ""

# 등급 판정
if [ $TOTAL -ge 95 ]; then
    echo "✅ A grade. Ship it!"
    exit 0
elif [ $TOTAL -ge 80 ]; then
    echo "⚠️  B grade. Acceptable but not main-ready."
    exit 1
elif [ $TOTAL -ge 70 ]; then
    echo "⚠️  C grade. Needs work."
    exit 1
else
    echo "❌ F grade. Reject."
    exit 1
fi
```

### 2.4 ship.sh — 통합 명령

```bash
#!/bin/bash
# scripts/ship.sh
# verify.sh 통과 시에만 commit + push

set -e

COMMIT_MSG="$1"
if [ -z "$COMMIT_MSG" ]; then
    echo "Usage: ./scripts/ship.sh \"commit message\""
    exit 1
fi

# 1. verify.sh cross 모드 실행
./scripts/verify.sh cross
if [ $? -ne 0 ]; then
    echo "❌ Ship gate failed. Not committing."
    exit 1
fi

# 2. commit + push
git add -A
git commit -m "$COMMIT_MSG"
git push origin main

echo "✅ Pushed to origin/main"
```

### 2.5 사용

```bash
# 매일 작업 중
./scripts/verify.sh quick     # ~30초, 핵심만

# push 전
./scripts/verify.sh cross     # ~3-5분, 전체

# 또는 한 번에
./scripts/ship.sh "feat: add character relationship tracking"
```

---

## 3. Verify Agent (Layer 1 LLM 코드 리뷰)

### 3.1 구조

CORE의 LLM-as-Judge를 활용하지만 Layer 1 specific 프롬프트:

```python
# core/verify/layer1_review.py

class Layer1ReviewAgent:
    """git diff를 cross-model로 리뷰"""
    
    def __init__(self, registry: LLMRegistry, matrix: CrossModelMatrix):
        self.registry = registry
        self.matrix = matrix
    
    def review(self) -> Layer1ReviewResult:
        # 1. git diff 가져오기
        diff = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout
        
        if not diff:
            return Layer1ReviewResult(score=25, message="No changes to review")
        
        # 2. 변경 파일 리스트
        files_changed = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.split("\n")
        
        # 3. Cross-model 강제: WorldFork 개발에 사용한 모델 ≠ 리뷰어
        # 예: 본인이 Claude Code로 작업했으면 → Codex CLI나 Gemini가 리뷰
        reviewer = self._select_reviewer()
        
        # 4. 5-section prompt로 리뷰
        prompt = self._build_review_prompt(diff, files_changed)
        result = reviewer.generate_json(prompt, schema=REVIEW_SCHEMA)
        
        return Layer1ReviewResult(
            score=result["score"],   # 0-25
            issues=result["issues"],
            suggestions=result["suggestions"],
            reviewer_model=reviewer.model_name,
        )
    
    def _select_reviewer(self) -> LLMClient:
        """현재 작업 모델과 다른 reviewer 선택"""
        # ~/.worldfork/last_dev_model 같은 파일에서 마지막 사용 모델 읽기
        # 또는 환경변수 WORLDFORK_DEV_MODEL
        dev_model = os.environ.get("WORLDFORK_DEV_MODEL", "claude-code")
        
        candidates = ["codex-cli", "gemini-cli", "claude-code"]
        candidates = [c for c in candidates if c != dev_model]
        
        return self.registry.get_client(candidates[0])
```

### 3.2 리뷰 프롬프트 (5-section)

```python
LAYER1_REVIEW_PROMPT = """
# IDENTITY
You are a senior code reviewer for the WorldFork project.
Another LLM wrote this code. Your job is to find issues, not to approve.

# TASK
Review the git diff below. Score 0-25.
Focus on:
- Bugs / logic errors
- Information leaks (especially: scores in retry feedback)
- Cross-model violations (using same model for generate + verify)
- Security issues
- WorldFork-specific anti-patterns

# SPEC
WorldFork rules to verify:

**Information Isolation (CRITICAL)**
- Retry feedback MUST NOT contain: score, verdict, threshold, passed
- Challenger MUST NOT see Drafter's reasoning
- Detect: any code that passes these to LLM

**Cross-Model Verification**
- Generator and Verifier must be different models
- Detect: same model used for both roles

**Hardcoded Scores (CRITICAL)**
- All scores must come from real evaluation
- Detect: `return score=70` or similar magic numbers

**YAGNI Violations**
- New features without clear use
- "Future-proofing" code that's not needed

# OUTPUT FORMAT
JSON only:
{
  "score": <0-25>,
  "verdict": "pass" | "warn" | "fail",
  "issues": [
    {
      "severity": "critical" | "major" | "minor",
      "file": "path/to/file.py",
      "line": 42,
      "description": "...",
      "category": "info_leak" | "cross_model" | "hardcode" | "other"
    }
  ],
  "suggestions": [...]
}

Score guide:
- 25: No issues, ship-ready
- 20-24: Minor issues only
- 15-19: 1-2 major issues
- 10-14: Multiple major or 1 critical
- 0-9: Critical issues, reject

# EXAMPLES
{few_shot_examples}

# DIFF TO REVIEW
{diff}

# CHANGED FILES
{files_changed}
"""
```

### 3.3 자체 안전 패턴 검증

리뷰어가 우리 anti-pattern을 자동 감지:

```python
# core/verify/anti_pattern_check.py

class AntiPatternChecker:
    """코드에서 알려진 anti-pattern 검출 (Layer 1 추가 게이트)"""
    
    PATTERNS = [
        AntiPattern(
            id="hardcoded_score",
            severity="critical",
            regex=r"return\s+(?:.*?)?score\s*=\s*(?:70|80|85|90|95)",
            message="Hardcoded score detected. All scores must come from real evaluation."
        ),
        AntiPattern(
            id="info_leak_in_feedback",
            severity="critical",
            regex=r"feedback.*?(?:score|verdict|threshold|passed)\s*[=:]",
            message="Score/verdict leaking to LLM feedback. Use issues+suggestions only."
        ),
        AntiPattern(
            id="single_model_verify",
            severity="major",
            regex=r"generator\s*=\s*verifier|same model",
            message="Generator and Verifier should be different (Cross-Model)."
        ),
    ]
    
    def check_diff(self, diff: str) -> list[AntiPatternMatch]:
        matches = []
        for pattern in self.PATTERNS:
            for match in re.finditer(pattern.regex, diff, re.IGNORECASE):
                matches.append(AntiPatternMatch(
                    pattern=pattern,
                    line=self._extract_line(diff, match),
                    matched_text=match.group(0),
                ))
        return matches
```

이게 LLM 리뷰 전 1차 필터. 빠르고 비용 0.

---

## 4. Pre-commit Hook

### 4.1 설치

```bash
# .git/hooks/pre-commit (실행 권한 필요)
#!/bin/bash
# WorldFork pre-commit hook
# verify.sh quick 모드 자동 실행

set -e

# 빠른 검증 (commit 차단)
./scripts/verify.sh quick

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Pre-commit verify failed."
    echo "   Run: ./scripts/verify.sh quick"
    echo "   Fix issues and try again."
    echo ""
    echo "   To bypass (NOT recommended): git commit --no-verify"
    exit 1
fi
```

### 4.2 빠른 검증 항목 (~30초)

pre-commit에서 도는 빠른 항목:

```
[1/3] Lint (ruff + tsc --noEmit)         ~5초
[2/3] Unit tests 핵심만 (--lf 마지막 실패)   ~10초
[3/3] Anti-pattern check (regex)         ~3초

총: ~20-30초
```

LLM 호출 없는 항목만. 비용 0.

### 4.3 push 전 cross 검증

pre-push hook (선택):

```bash
# .git/hooks/pre-push
#!/bin/bash
./scripts/verify.sh cross   # ~3-5분, push 차단
```

또는 GitHub Actions가 잡음 (다음 섹션).

---

## 5. GitHub Actions CI

### 5.1 workflow

```yaml
# .github/workflows/ci.yml

name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ship-gate:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2  # diff 위해
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Python deps
        run: |
          pip install -e .[dev]
      
      - name: Install Node deps (if frontend exists)
        if: hashFiles('frontend/package.json') != ''
        run: |
          cd frontend
          pnpm install
      
      - name: Build
        run: ./scripts/verify.sh quick
      
      - name: Anti-pattern check
        run: python -m core.verify.anti_pattern_check
      
      - name: Cross-LLM review (if API key available)
        if: ${{ secrets.ANTHROPIC_API_KEY != '' }}
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: ./scripts/verify.sh cross
      
      - name: Eval regression check
        if: ${{ secrets.ANTHROPIC_API_KEY != '' }}
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python -m core.eval.regression \
            --baseline runs/baseline_latest.json \
            --threshold 0.05  # 5% 이상 회귀하면 fail
      
      - name: Upload eval results
        uses: actions/upload-artifact@v4
        with:
          name: eval-results
          path: runs/
```

### 5.2 자율 Fix (max 3 사이클)

자료의 패턴 ("Anti-Pattern: CI 17일 깨진 채로 운영" 회피):

```python
# tools/ci_autofix.py
# 사용: 본인이 직접 호출 (Claude Code에서)

def auto_fix_ci(max_cycles: int = 3):
    """CI 깨졌을 때 자동 fix 시도"""
    
    for cycle in range(max_cycles):
        # 1. 최신 CI 실행 확인
        run_id = get_latest_failed_run()
        if not run_id:
            print("✅ CI already passing")
            return
        
        # 2. 실패 로그 분석
        log = subprocess.run(
            ["gh", "run", "view", str(run_id), "--log-failed"],
            capture_output=True,
            text=True,
        ).stdout
        
        # 3. 안전 가드 — 다음에는 자동 fix 안 함
        if any(blocker in log for blocker in [
            "Schema migration",     # DB 변경
            "package.json modified", # 의존성 변경
            "ANTHROPIC_API_KEY",     # 비밀 변경
        ]):
            print(f"⚠️ Cycle {cycle}: Manual intervention required")
            return
        
        # 4. 수정 시도 (Claude Code 등으로)
        fix_proposal = analyze_and_propose_fix(log)
        apply_fix(fix_proposal)
        
        # 5. push + 결과 대기
        subprocess.run(["./scripts/ship.sh", f"fix(ci): cycle {cycle+1}"])
        wait_for_ci()
    
    print(f"❌ Failed after {max_cycles} cycles. Manual fix required.")
```

자동 fix 안 하는 경우:
- 코드 변경 (의외 동작 위험)
- 외부 패키지 추가 (streak 보호)
- DB schema 변경 (migration 위험)
- 같은 종류 fix 재실패

---

## 6. Hook 시스템 (12개 이벤트)

자료의 패턴 그대로. Layer 1 + Layer 2 양쪽에서 사용 가능.

### 6.1 Hook 이벤트 목록

```
TaskStart           — 작업 시작
PrePlan             — 계획 수립 전
PostPlan            — 계획 수립 후
PlanReview          — 사용자 검토 (Layer 2만)
PreCode             — 코드 작성 전
PostCode            — 코드 작성 후 (★ 빌드 게이트!)
PreVerify           — 검증 전
PostVerify          — 검증 후
OnRetry             — 재시도 발생
OnReplan            — 재계획 발생
TaskComplete        — 성공 종료
TaskFail            — 실패 종료
```

### 6.2 Hook 정의

```python
# core/hooks/types.py

@dataclass
class HookContext:
    event: str
    layer: Literal["1", "2"]
    timestamp: datetime
    payload: dict
    
    # Hook이 수정할 수 있는 것
    abort: bool = False           # True 시 작업 중단
    modifications: dict = None    # payload 수정


class Hook(Protocol):
    """Hook 인터페이스"""
    
    def __call__(self, ctx: HookContext) -> HookContext:
        ...


class HookRegistry:
    """등록된 hook 관리"""
    
    def __init__(self):
        self._hooks: dict[str, list[Hook]] = defaultdict(list)
    
    def register(self, event: str, hook: Hook, priority: int = 0):
        self._hooks[event].append((priority, hook))
        self._hooks[event].sort(key=lambda x: x[0])  # priority 순
    
    def trigger(self, event: str, ctx: HookContext) -> HookContext:
        for _, hook in self._hooks.get(event, []):
            ctx = hook(ctx)
            if ctx.abort:
                return ctx
        return ctx
```

### 6.3 우선순위 머지

자료의 패턴: 내장 < 글로벌 < 프로젝트

```python
# core/hooks/loader.py

def load_hooks() -> HookRegistry:
    registry = HookRegistry()
    
    # 1. 내장 기본값 (priority 0)
    register_builtin_hooks(registry)
    
    # 2. 글로벌 ~/.worldfork/hooks.json (priority 50)
    global_hooks_path = Path.home() / ".worldfork" / "hooks.json"
    if global_hooks_path.exists():
        load_hooks_from_file(registry, global_hooks_path, priority=50)
    
    # 3. 프로젝트 .worldfork/hooks.json (priority 100, 최우선)
    project_hooks_path = Path(".worldfork/hooks.json")
    if project_hooks_path.exists():
        load_hooks_from_file(registry, project_hooks_path, priority=100)
    
    return registry
```

### 6.4 Layer 1 표준 Hooks

```python
# core/hooks/layer1_builtin.py

def hook_pre_code_build_check(ctx: HookContext) -> HookContext:
    """PostCode hook: 빌드 실패 시 즉시 거부 (자료의 PostCode 게이트)"""
    if ctx.event != "PostCode":
        return ctx
    
    result = subprocess.run(
        ["./scripts/verify.sh", "quick"],
        capture_output=True,
    )
    
    if result.returncode != 0:
        ctx.abort = True
        ctx.payload["abort_reason"] = "PostCode build check failed"
    
    return ctx


def hook_pre_verify_anti_pattern(ctx: HookContext) -> HookContext:
    """PreVerify hook: anti-pattern 자동 검사"""
    if ctx.event != "PreVerify":
        return ctx
    
    diff = get_current_diff()
    matches = AntiPatternChecker().check_diff(diff)
    critical = [m for m in matches if m.pattern.severity == "critical"]
    
    if critical:
        ctx.abort = True
        ctx.payload["anti_patterns_found"] = critical
    
    return ctx


def hook_task_complete_log(ctx: HookContext) -> HookContext:
    """TaskComplete: 작업 완료 시 기록"""
    if ctx.event != "TaskComplete":
        return ctx
    
    log_completion(
        task_id=ctx.payload.get("task_id"),
        score=ctx.payload.get("final_score"),
        duration=ctx.payload.get("duration"),
        layer=ctx.layer,
    )
    return ctx
```

### 6.5 사용자 정의 Hook 예시

```json
// .worldfork/hooks.json (프로젝트 우선순위)
{
  "hooks": [
    {
      "event": "PostCode",
      "command": "pnpm test:fast",
      "blocking": true,
      "description": "빌드 후 빠른 테스트 강제"
    },
    {
      "event": "TaskComplete",
      "command": "scripts/notify_slack.sh",
      "blocking": false,
      "description": "Slack 알림 (선택)"
    },
    {
      "event": "OnRetry",
      "command": "echo 'Retry detected, log analysis...'",
      "blocking": false
    }
  ]
}
```

---

## 7. 외부 패키지 0건 Streak

자료의 핵심 정책:

### 7.1 정책

```yaml
# .worldfork/policies/external_packages.yaml

external_packages:
  policy: zero_streak           # 새 패키지 추가 0건
  
  exceptions:
    # 의식적으로 허용한 핵심 의존성
    python:
      # LLM
      - llama-cpp-python        # 로컬 LLM
      - anthropic               # Claude API
      - openai                  # GPT API (Tier 1+)
      - google-generativeai     # Gemini API (Tier 1+)
      
      # 인프라
      - httpx                   # HTTP 클라이언트 (DGX 서빙 호출 등)
      - python-dotenv           # 환경변수 로드
      - pydantic                # 스키마
      - pyyaml                  # 설정
      - sqlalchemy              # DB ORM (Tier 2+ Save/Load)
      
      # 테스트
      - pytest
      - pytest-asyncio
      - pytest-cov
      - pytest-mock
      - hypothesis              # property-based testing
    
    typescript:                 # Tier 2+ frontend
      - next
      - react
      - vitest
      - playwright
      - msw                     # API 모킹
  
  forbidden_categories:
    # 추가 금지
    - alternative_test_runners  # pytest 대신 nose/unittest 등
    - orm                       # raw SQL + 단순 sqlite3
    - http_clients              # httpx 하나만
    - dsl_builders              # 자체 작성
```

### 7.2 자동 감지

```python
# scripts/check_external_streak.py

def check_streak() -> StreakResult:
    """매 commit 외부 패키지 streak 검증"""
    # 1. requirements.txt / pyproject.toml diff
    diff = get_dependency_diff()
    
    new_packages = extract_new_packages(diff)
    
    # 2. exception 리스트와 대조
    allowed = load_exceptions()
    
    unauthorized = [p for p in new_packages if p not in allowed]
    
    if unauthorized:
        return StreakResult(
            broken=True,
            new_packages=unauthorized,
            message="External package addition not in allowlist"
        )
    
    # 3. streak 카운트 업데이트
    update_streak_counter()
    
    return StreakResult(broken=False, streak=get_current_streak())
```

매 commit 후 출력:
```
📦 External package streak: 23 commits
```

자료의 효과:
- 의존성 폭증 방지
- 보안 vulnerability 노출 최소
- 다음 프로젝트에 그대로 가져가기 가능

---

## 8. 매 Commit 자동 Eval

### 8.1 Smoke Eval

```python
# core/eval/smoke.py

def run_smoke_eval(items: int = 10, layer: str = "1") -> SmokeResult:
    """매 commit 빠른 회귀 검증"""
    
    # 1. 각 카테고리에서 빠른 N개 샘플
    eval_set = load_smoke_subset(items)
    
    # 2. 현재 prompt + 모델로 실행
    config = load_config()
    runner = EvalRunner(
        eval_set=eval_set,
        target=registry.get_client(config.layer1.test_model),
        judge=registry.get_client(config.layer1.judge_model),
    )
    
    # 3. baseline과 비교
    current = runner.run()
    baseline = load_baseline()
    
    regression = compare_runs(baseline, current)
    
    if regression.has_regression(threshold=0.05):  # 5% 이상 회귀
        return SmokeResult(
            passed=False,
            score=current.aggregate_score,
            regressions=regression.regressions,
        )
    
    return SmokeResult(passed=True, score=current.aggregate_score)
```

### 8.2 Full Eval (push 전)

```python
# core/eval/full.py

def run_full_eval() -> FullResult:
    """push 전 전체 eval set 실행"""
    
    # 모든 카테고리, 모든 항목
    full_set = load_full_eval_set()
    
    # 각 카테고리별 결과
    category_results = {}
    for category in full_set.categories:
        result = run_category_eval(category)
        category_results[category] = result
    
    # 전체 점수
    final_score = compute_aggregate_score(category_results)
    
    return FullResult(
        category_results=category_results,
        final_score=final_score,
        passed=final_score >= 95,
    )
```

### 8.3 회귀 비교

baseline과 현재 비교:

```python
# core/eval/regression.py

def check_regression(
    current: EvalResult,
    baseline: EvalResult,
    threshold: float = 0.05,
) -> RegressionReport:
    """회귀 발생 항목 찾기"""
    
    # eval set 버전이 다르면 비교 불가
    if current.eval_set_version != baseline.eval_set_version:
        raise IncompatibleEvalSetError(
            f"Cannot compare: baseline={baseline.eval_set_version}, "
            f"current={current.eval_set_version}"
        )
    
    regressions = []
    for category in current.scores:
        delta = current.scores[category] - baseline.scores[category]
        if delta < -threshold:
            regressions.append(Regression(
                category=category,
                baseline_score=baseline.scores[category],
                current_score=current.scores[category],
                delta=delta,
            ))
    
    return RegressionReport(
        regressions=regressions,
        improvements=[...],  # 동일하게
    )
```

---

## 9. 도그푸딩 강제

자료의 함정 1 ("Made But Never Used") 회피.

### 9.1 매 Tier 끝 체크리스트

```python
# scripts/tier_dogfood.py

def tier_dogfood_check(tier: int) -> DogfoodResult:
    """Tier 졸업 시 도그푸딩 강제"""
    
    requirements = {
        0: {
            "self_play_count": 5,
            "friend_play_count": 3,
            "ai_playtester_personas": 3,
        },
        1: {
            "self_play_count": 3,
            "friend_play_count": 2,
            "external_user_count": 1,
            "ai_playtester_personas": 6,
        },
        2: {
            "self_play_count": 5,
            "beta_count": 5,
            "ai_playtester_personas": 12,
        },
        3: {
            "self_play_count": 5,
            "external_beta_count": 20,
            "ai_playtester_personas": "all",
        },
    }
    
    req = requirements[tier]
    actual = load_actual_dogfood_logs()
    
    failures = []
    for key, expected in req.items():
        actual_value = actual.get(key, 0)
        if isinstance(expected, int) and actual_value < expected:
            failures.append(f"{key}: {actual_value} < {expected}")
    
    return DogfoodResult(
        tier=tier,
        passed=len(failures) == 0,
        failures=failures,
    )
```

### 9.2 도그푸딩 로그

```yaml
# logs/dogfood/2026-04-30_session.yaml
session_id: dogfood_2026_04_30_01
date: 2026-04-30
tier: 0
type: self_play              # self_play | friend | external | ai_playtester

duration_minutes: 35
scenario: kings_death

playthrough:
  - turn: 1
    user_input: "왕비를 심문한다"
    response_quality: 4
    notes: "왕비 캐릭터 일관성 좋음"
  
  - turn: 8
    user_input: "정원사 의심"
    response_quality: 2
    notes: "정원사가 갑자기 친절해짐, 일관성 깨짐"
    issue_filed: true
    issue_id: char_consistency_001

verdict:
  fun_factor: 4
  would_replay: true
  ended_naturally: true
  
findings:
  - "캐릭터 5턴 후 일관성 약화 — eval에 추가 필요"
  - "단서 발견 시 묘사가 너무 짧음"

next_eval_seeds:
  - id: persona_long_session_001
    based_on: char_consistency_001
```

매 도그푸딩 = YAML 1개. eval 시드로 전환.

---

## 10. 비용 / 시간 추적 (Layer 1)

### 10.1 추적 항목

```python
# core/tracking/layer1_metrics.py

@dataclass
class Layer1Metrics:
    # 시간
    verify_quick_avg_seconds: float
    verify_cross_avg_seconds: float
    eval_smoke_avg_seconds: float
    eval_full_avg_seconds: float
    
    # 비용 (cross 모드의 LLM 호출)
    verify_cross_cost_per_run: float
    eval_smoke_cost_per_run: float
    eval_full_cost_per_run: float
    
    # 빈도
    commits_per_day: int
    ship_attempts_per_day: int
    ship_success_rate: float
    
    # streak
    external_package_streak: int
    a_grade_streak: int           # 95+ 연속


def daily_layer1_report() -> str:
    """매일 작업 끝 리포트"""
    metrics = compute_today_metrics()
    return f"""
    📊 Layer 1 Daily Report ({date.today()})
    ─────────────────────────────────────────
    Commits:           {metrics.commits_per_day}
    Ship attempts:     {metrics.ship_attempts_per_day}
    Ship success:      {metrics.ship_success_rate:.0%}
    
    Avg verify time:   {metrics.verify_cross_avg_seconds:.1f}s
    Avg verify cost:   ${metrics.verify_cross_cost_per_run:.3f}
    
    Streaks:
      External pkg:    {metrics.external_package_streak} commits
      A grade:         {metrics.a_grade_streak} commits
    """
```

### 10.2 비용 한도

```yaml
# config/harness.yaml
layer1:
  cost_alerts:
    daily_warning: 5.00       # $5/일 도달 시 경고
    daily_hard_stop: 20.00    # $20/일 도달 시 LLM 호출 차단
```

자료의 비용 추적 패턴: **모든 호출 = 비용 추적, 사용자 인지**.

---

## 11. Layer 1 사용 흐름 (전체)

### 11.1 일상 작업

```bash
# 1. Claude Code로 작업
# (자동으로 PreCode → PostCode hook 작동)

# 2. 빠른 검증 (수시)
./scripts/verify.sh quick     # ~30초

# 3. push 전 cross 검증
./scripts/verify.sh cross     # ~3-5분

# 4. ship (95+ 통과 시)
./scripts/ship.sh "feat: ..."
```

### 11.2 Tier 졸업 시

```bash
# 1. Full eval
./scripts/verify.sh full

# 2. 도그푸딩 검증
python scripts/tier_dogfood.py --tier 1

# 3. AI Playtester 전체
python -m ai_playtester.run --tier 1 --personas all

# 4. 외부 사용자 시뮬
python scripts/external_user_simulation.py
```

### 11.3 Tier 졸업 조건 (Layer 1 측면)

각 Tier별 Layer 1 졸업 조건:

```
Tier 0:
  ✅ ship gate 95+ 매 commit
  ✅ 외부 패키지 streak 끊김 0회
  ✅ pre-commit hook 작동
  ✅ verify.sh quick 30초 이내

Tier 1:
  ✅ Tier 0 조건 + 
  ✅ verify.sh cross 5분 이내
  ✅ Eval smoke 매 commit 통과
  ✅ Layer 1 LLM 코드 리뷰 작동

Tier 2:
  ✅ Tier 1 조건 +
  ✅ Frontend build 통합
  ✅ Playwright E2E ship gate 통합
  ✅ 외부 사용자 시뮬레이션 통과

Tier 3:
  ✅ Tier 2 조건 +
  ✅ Mutation testing 1회 실행
  ✅ 외부 도구 (lm-eval-harness) 1회 검증
  ✅ A grade streak 50+ commits
```

---

## 12. Layer 1 안티패턴

자료의 함정 그대로 + WorldFork specific:

### 12.1 절대 하면 안 되는 것

```
❌ ship gate 통과 안 한 commit이 main에 들어감
   → pre-commit hook + GitHub Actions 강제

❌ 임시로 threshold 낮추기 (95 → 80)
   → harness.yaml diff에서 감지

❌ 점수 hardcode
   → AntiPatternChecker 자동 감지

❌ 같은 모델로 generate + verify
   → CrossModelEnforcer가 런타임 에러

❌ Eval set 임의 삭제 (회귀 비교 깨짐)
   → 보존만, 새 버전은 추가만

❌ "임시로" 외부 패키지 추가
   → streak 자동 끊김, 알람

❌ 마케팅 메시지 vs 실제 동작 불일치
   → README/docs 변경 시 demo 강제

❌ CI 깨진 채로 운영
   → 자료의 17일 함정. 매 push 후 확인.
```

### 12.2 의식적 회피 패턴

```python
# 매주 자기 점검 (자료의 self-check 패턴)

WEEKLY_SELF_CHECK = """
Layer 1 자기 점검 (매주 일요일):

1. CI 상태?
   - 마지막 7일 GitHub Actions 결과 확인
   - 깨진 채로 있으면 즉시 fix

2. 외부 패키지 streak?
   - 끊겼으면 이유 검토 (의식적이었나?)

3. Ship 통과율?
   - 95% 이하면 verify.sh 너무 빡센지 또는 코드 품질 저하 신호

4. 도그푸딩 빈도?
   - 매 Tier 끝 외 추가 도그푸딩 했나
   - "Made But Never Used" 신호 없나

5. 비용 트렌드?
   - 비용 폭증 = 비효율 신호

6. Anti-pattern 감지 빈도?
   - 자주 잡히면 자동화 더 강화 필요
"""
```

---

## 13. 다음 작업

Layer 1 완료. 다음:

- **HARNESS_LAYER2_SERVICE.md** — 서비스 하네스 (런타임)
  - Game pipeline (Interview → Plan → Verify → Loop)
  - Retry policy (max 3) + Information Isolation
  - Fallback chain (Local → API)
  - Error 4-tier 분류

---

## 부록 A: scripts/ 디렉토리 구조

```
scripts/
├── verify.sh              # Layer 1 ship gate
├── ship.sh                # verify + commit + push
├── tier_dogfood.py        # Tier 졸업 도그푸딩 검증
├── ci_autofix.py          # CI 자율 fix (max 3 사이클)
├── check_external_streak.py
├── external_user_simulation.py
└── notify_slack.sh        # 선택 hook
```

## 부록 B: 환경 변수

```bash
# Layer 1 작업 시 필요한 환경 변수
WORLDFORK_DEV_MODEL=claude-code     # 본인 작업 모델 (Cross-Model 매핑용)
ANTHROPIC_API_KEY=...               # Claude API
OPENAI_API_KEY=...                  # GPT API (Cross-Model 검증용)
GOOGLE_API_KEY=...                  # Gemini API (Tier 1+)

# 비용 한도
WORLDFORK_DAILY_LIMIT_USD=5.00

# 디버그
WORLDFORK_DEBUG=true                # verify.sh 상세 출력
```

## 부록 C: GitHub Actions 비밀

```
필수 (Layer 1 cross 모드):
  ANTHROPIC_API_KEY
  OPENAI_API_KEY (또는 다른 cross-verify 모델)

선택:
  GOOGLE_API_KEY
  SLACK_WEBHOOK
```

---

*문서 끝. v0.1 초안.*
