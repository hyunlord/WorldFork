#!/bin/bash
# Layer 1 Ship Gate (HARNESS_LAYER1_DEV 2장)
# Tier 0 미니멀 버전 (5단계 / 100점)
#
# 사용:
#   scripts/verify.sh quick    # 빠른 검증 (~30초)
#   scripts/verify.sh full     # 전체 (~5분)
#
# 종료 코드: 0 = pass (95+) / 1 = fail

set -u

MODE="${1:-quick}"
SCORE=0
DETAILS=""

cd "$(dirname "$0")/.."

# [1/5] Build (20점)
echo ""
echo "════════════════════════════════════════════════"
echo "Layer 1 Ship Gate (Tier 0 미니멀)"
echo "════════════════════════════════════════════════"
echo ""
echo "[1/5] Build..."
BUILD_SCORE=0

if python -c "import core; import service; import tools" 2>/dev/null; then
    BUILD_SCORE=20
    echo "  ✅ Python imports OK (20/20)"
else
    echo "  ❌ Python import failed (0/20)"
fi

SCORE=$((SCORE + BUILD_SCORE))
DETAILS="$DETAILS\n[1/5] Build: $BUILD_SCORE/20"

# [2/5] Lint + Type Check (15점)
echo ""
echo "[2/5] Lint + Type..."
LINT_SCORE=0

if ruff check core/ service/ tools/ tests/ --quiet 2>/dev/null; then
    LINT_SCORE=$((LINT_SCORE + 7))
    echo "  ✅ ruff (7/7)"
else
    echo "  ❌ ruff failed"
fi

if mypy core/ service/ --strict 2>&1 | tail -1 | grep -q "Success"; then
    LINT_SCORE=$((LINT_SCORE + 8))
    echo "  ✅ mypy --strict (8/8)"
else
    echo "  ❌ mypy --strict failed"
fi

SCORE=$((SCORE + LINT_SCORE))
DETAILS="$DETAILS\n[2/5] Lint: $LINT_SCORE/15"

# [3/5] Unit Tests (20점)
echo ""
echo "[3/5] Unit Tests..."
UNIT_SCORE=0

PYTEST_OUT=$(pytest tests/unit/ -m "not slow" --tb=no -q 2>&1)
PYTEST_RC=$?

if [ $PYTEST_RC -eq 0 ]; then
    UNIT_SCORE=20
    PASSED=$(echo "$PYTEST_OUT" | grep -oE "[0-9]+ passed" | head -1)
    echo "  ✅ $PASSED (20/20)"
else
    echo "  ❌ Tests failed (0/20)"
fi

SCORE=$((SCORE + UNIT_SCORE))
DETAILS="$DETAILS\n[3/5] Unit: $UNIT_SCORE/20"

# [4/5] Eval Smoke (20점)
echo ""
echo "[4/5] Eval Smoke (Integration tests)..."
EVAL_SCORE=0

if pytest tests/integration/ -m "not slow" --tb=no -q > /dev/null 2>&1; then
    EVAL_SCORE=20
    echo "  ✅ Eval infrastructure verified (20/20)"
else
    echo "  ❌ Eval infrastructure failed (0/20)"
fi

SCORE=$((SCORE + EVAL_SCORE))
DETAILS="$DETAILS\n[4/5] Eval: $EVAL_SCORE/20"

# [5/5] Verify Agent (25점) — ★ 진짜 LLM 호출 (Tier 1.5 D1)
echo ""
echo "[5/5] Verify Agent (★ Cross-LLM 코드 리뷰)..."
VERIFY_SCORE=0

# ★ codex가 git diff 리뷰 (★ 자기 합리화 차단)
if command -v codex &>/dev/null; then
    REVIEW_OUTPUT=$(python scripts/verify_layer1_review.py 2>&1)
    REVIEW_EXIT=$?

    SCORE_LINE=$(echo "$REVIEW_OUTPUT" | grep -oE 'SCORE=[0-9]+' | tail -1)
    if [ -n "$SCORE_LINE" ]; then
        VERIFY_SCORE=$(echo "$SCORE_LINE" | sed 's/SCORE=//')
        if [ $REVIEW_EXIT -eq 0 ]; then
            echo "  ✅ Verify passed ($VERIFY_SCORE/25)"
        else
            echo "  ⚠️ Verify fail ($VERIFY_SCORE/25)"
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
DETAILS="$DETAILS\n[5/5] Verify Agent: $VERIFY_SCORE/25"

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
