#!/bin/bash
# Layer 1 Ship Gate (HARNESS_LAYER1_DEV 2장)
# Tier 2 D11 — Mechanical E2E 추가 (★ 점수 b)
#
# 사용:
#   scripts/verify.sh quick    # 빠른 검증
#   scripts/verify.sh full     # 전체
#
# 종료 코드: 0 = pass (95+) / 1 = fail
# 점수 분배: Build 10 + Lint 10 + Tests 10 + Smoke 10 + E2E 10 + Verify 50 = 100

set -u

MODE="${1:-quick}"
SCORE=0
DETAILS=""

cd "$(dirname "$0")/.."

# [1/6] Build (10점)
echo ""
echo "════════════════════════════════════════════════"
echo "Layer 1 Ship Gate (Tier 2 D11 — 6단계, Mechanical E2E)"
echo "════════════════════════════════════════════════"
echo ""
echo "[1/6] Build..."
BUILD_SCORE=0

if python -c "import core; import service; import tools" 2>/dev/null; then
    BUILD_SCORE=10
    echo "  ✅ Python imports OK (10/10)"
else
    echo "  ❌ Python import failed (0/10)"
fi

SCORE=$((SCORE + BUILD_SCORE))
DETAILS="$DETAILS\n[1/6] Build: $BUILD_SCORE/10"

# [2/6] Lint + Type Check (10점)
# ★ Tier 2 D12 — AutoFix harness 통합 (★ Made But Never Used 차단):
# ruff fail 시 AutoFix runner 1 cycle 호출 → ruff --fix 자동 시도 후 재검사
echo ""
echo "[2/6] Lint + Type..."
LINT_SCORE=0

if ruff check core/ service/ tools/ tests/ --quiet 2>/dev/null; then
    LINT_SCORE=$((LINT_SCORE + 5))
    echo "  ✅ ruff (5/5)"
else
    echo "  ⚠️  ruff failed → AutoFix runner 1 cycle 호출..."
    # ★ pipe 우회: exit code 진짜 검사 (★ tail의 0 X)
    AUTOFIX_OUT=$(python scripts/auto_fix_runner.py --check-only 2>&1)
    AUTOFIX_RC=$?
    echo "$AUTOFIX_OUT" | tail -3
    if [ $AUTOFIX_RC -eq 0 ]; then
        if ruff check core/ service/ tools/ tests/ --quiet 2>/dev/null; then
            LINT_SCORE=$((LINT_SCORE + 5))
            echo "  ✅ ruff (AutoFix 후 5/5)"
        else
            echo "  ❌ ruff failed (AutoFix 후도 X)"
        fi
    else
        echo "  ❌ ruff failed (AutoFix smoke fail rc=$AUTOFIX_RC)"
    fi
fi

if mypy core/ service/ --strict 2>&1 | tail -1 | grep -q "Success"; then
    LINT_SCORE=$((LINT_SCORE + 5))
    echo "  ✅ mypy --strict (5/5)"
else
    echo "  ❌ mypy --strict failed"
fi

SCORE=$((SCORE + LINT_SCORE))
DETAILS="$DETAILS\n[2/6] Lint: $LINT_SCORE/10"

# [3/6] Unit Tests (10점)
echo ""
echo "[3/6] Unit Tests..."
UNIT_SCORE=0

PYTEST_OUT=$(pytest tests/unit/ -m "not slow" --tb=no -q 2>&1)
PYTEST_RC=$?

if [ $PYTEST_RC -eq 0 ]; then
    UNIT_SCORE=10
    PASSED=$(echo "$PYTEST_OUT" | grep -oE "[0-9]+ passed" | head -1)
    echo "  ✅ $PASSED (10/10)"
else
    echo "  ❌ Tests failed (0/10)"
fi

SCORE=$((SCORE + UNIT_SCORE))
DETAILS="$DETAILS\n[3/6] Unit: $UNIT_SCORE/10"

# [4/6] Eval Smoke (10점) — ★ 9B Q3 실제 LLM 호출 (★ 점수 b: 20→10)
echo ""
echo "[4/6] Eval Smoke (★ 9B Q3 LLM smoke — 95%+ 목표)..."
EVAL_SCORE=0

# ★ 9B Q3 로컬 서버 확인 후 smoke runner 실행
if curl -sf http://localhost:8083/health > /dev/null 2>&1; then
    SMOKE_OUTPUT=$(python scripts/smoke_runner.py 2>&1)
    SMOKE_EXIT=$?

    RATE_LINE=$(echo "$SMOKE_OUTPUT" | grep -oE 'SMOKE_PASS_RATE=[0-9]+' | tail -1)
    if [ -n "$RATE_LINE" ]; then
        SMOKE_RATE=$(echo "$RATE_LINE" | sed 's/SMOKE_PASS_RATE=//')
        # 95%+ → 10점, 80-94% → 5점, <80% → 0점
        if [ "$SMOKE_RATE" -ge 95 ]; then
            EVAL_SCORE=10
            echo "  ✅ Smoke passed ($SMOKE_RATE% ≥ 95%) (10/10)"
        elif [ "$SMOKE_RATE" -ge 80 ]; then
            EVAL_SCORE=5
            echo "  ⚠️ Smoke partial ($SMOKE_RATE% ≥ 80%) (5/10)"
        else
            EVAL_SCORE=0
            echo "  ❌ Smoke failed ($SMOKE_RATE% < 80%) (0/10)"
        fi
        echo "$SMOKE_OUTPUT" | head -5 | sed 's/^/    /'
    else
        echo "  ❌ Smoke output parse failed"
        echo "$SMOKE_OUTPUT" | head -3 | sed 's/^/    /'
    fi
else
    # 9B Q3 서버 없으면 integration 테스트 fallback (5점 상한)
    echo "  ⚠️ 9B Q3 server not available — integration test fallback (5점 상한)"
    if pytest tests/integration/ -m "not slow" --tb=no -q > /dev/null 2>&1; then
        EVAL_SCORE=5
        echo "  ✅ Integration tests OK (5/10)"
    else
        echo "  ❌ Integration tests failed (0/10)"
    fi
fi

SCORE=$((SCORE + EVAL_SCORE))
DETAILS="$DETAILS\n[4/6] Smoke: $EVAL_SCORE/10"

# [5/6] E2E (10점 = Mechanical 5 + Browser 5) — ★ Tier 2 D11+
#   Mechanical (curl): backend endpoint + CORS
#   Browser (playwright): 진짜 사람 클릭 흐름 (★ HMR / fetch 진짜 발생)
echo ""
echo "[5/6] E2E (★ Mechanical curl + Browser playwright)..."
E2E_SCORE=0

# (a) Mechanical E2E — backend
if lsof -ti:8090 > /dev/null 2>&1; then
    echo "  ⚠️ port 8090 사용 중 — Mechanical skip (★ dev 서버 보존, 0/5)"
elif curl -sf http://localhost:8083/health > /dev/null 2>&1 && \
     curl -sf http://localhost:8081/health > /dev/null 2>&1; then
    if python tools/run_e2e_check.py > /tmp/e2e_out.log 2>&1; then
        E2E_SCORE=$((E2E_SCORE + 5))
        echo "  ✅ Mechanical passed — backend + CORS (5/5)"
    else
        echo "  ❌ Mechanical failed (0/5)"
        tail -8 /tmp/e2e_out.log | sed 's/^/    /'
    fi
elif curl -sf http://localhost:8083/health > /dev/null 2>&1; then
    echo "  ⚠️ 27B (8081) X — /game/turn skip"
    if python tools/run_e2e_check.py --skip-turn > /tmp/e2e_out.log 2>&1; then
        E2E_SCORE=$((E2E_SCORE + 3))
        echo "  ✅ Mechanical partial (3/5)"
    else
        echo "  ❌ Mechanical failed (0/5)"
    fi
else
    echo "  ⚠️ LLM 서버 X — --skip-turn (CI 환경)"
    if python tools/run_e2e_check.py --skip-turn > /tmp/e2e_out.log 2>&1; then
        E2E_SCORE=$((E2E_SCORE + 3))
        echo "  ✅ Mechanical partial no-LLM (3/5)"
    else
        echo "  ❌ Mechanical failed (0/5)"
    fi
fi

# (b) Browser E2E — frontend → backend 진짜 사람 흐름
if curl -sf http://localhost:4000 > /dev/null 2>&1 && \
   lsof -ti:8090 > /dev/null 2>&1; then
    if python tools/run_browser_e2e.py --frontend-url http://localhost:4000 \
        > /tmp/browser_e2e_out.log 2>&1; then
        E2E_SCORE=$((E2E_SCORE + 5))
        echo "  ✅ Browser passed — 사람 클릭 흐름 진짜 (5/5)"
    else
        echo "  ❌ Browser failed (0/5)"
        tail -10 /tmp/browser_e2e_out.log | sed 's/^/    /'
    fi
else
    echo "  ⚠️ frontend (4000) 또는 backend (8090) X — Browser skip (CI 환경, 0/5)"
fi

SCORE=$((SCORE + E2E_SCORE))
DETAILS="$DETAILS\n[5/6] E2E: $E2E_SCORE/10"

# [6/6] Verify Agent (50점) — ★ Cross-LLM 코드 리뷰 (★ 인사이트 #19)
echo ""
echo "[6/6] Verify Agent (★ Cross-LLM 코드 리뷰 — 50점)..."
VERIFY_SCORE=0

# ★ codex가 git diff 리뷰 (★ 자기 합리화 차단)
if command -v codex &>/dev/null; then
    REVIEW_OUTPUT=$(python scripts/verify_layer1_review.py 2>&1)
    REVIEW_EXIT=$?

    SCORE_LINE=$(echo "$REVIEW_OUTPUT" | grep -oE 'SCORE=[0-9]+' | tail -1)
    if [ -n "$SCORE_LINE" ]; then
        VERIFY_SCORE_RAW=$(echo "$SCORE_LINE" | sed 's/SCORE=//')
        # ★ 25점 만점 → 50점 환산 (× 2)
        VERIFY_SCORE=$((VERIFY_SCORE_RAW * 2))
        if [ $REVIEW_EXIT -eq 0 ]; then
            echo "  ✅ Verify passed ($VERIFY_SCORE_RAW/25 raw → $VERIFY_SCORE/50)"
        else
            echo "  ⚠️ Verify fail ($VERIFY_SCORE_RAW/25 raw → $VERIFY_SCORE/50)"
        fi
        echo "$REVIEW_OUTPUT" | head -8 | sed 's/^/    /'
    else
        echo "  ❌ Verify Agent output parse failed"
        echo "$REVIEW_OUTPUT" | head -5 | sed 's/^/    /'
        VERIFY_SCORE=0
    fi
else
    echo "  ⚠️ codex CLI not available"
    VERIFY_SCORE=0
fi

SCORE=$((SCORE + VERIFY_SCORE))
DETAILS="$DETAILS\n[6/6] Verify Agent: $VERIFY_SCORE/50"

# 결과
echo ""
echo "════════════════════════════════════════════════"
echo "TOTAL: $SCORE/100"
echo "════════════════════════════════════════════════"
printf "%b\n" "$DETAILS"
echo ""

if [ $SCORE -ge 95 ]; then
    echo "✅ Ship gate PASSED (A 등급, $SCORE/100)"
    exit 0
elif [ $SCORE -ge 80 ]; then
    echo "⚠️ Ship gate WARN (B 등급, $SCORE/100) — push 안 됨"
    exit 1
elif [ $SCORE -ge 70 ]; then
    echo "❌ Ship gate FAILED (C 등급, $SCORE/100)"
    exit 1
else
    echo "❌ Ship gate FAILED (F, $SCORE/100)"
    exit 1
fi
