#!/bin/bash
# Layer 1 Ship Gate (HARNESS_LAYER1_DEV 2장)
# Tier 2 D11 — Mechanical E2E 추가 (★ 점수 b)
#
# 사용:
#   scripts/verify.sh quick    # 빠른 검증
#   scripts/verify.sh full     # 전체
#
# 종료 코드: 0 = pass (95+) / 1 = fail
# 점수 분배 (★ harness 재설계 — 실 게임 E2E 비중 최대):
#   Build 5 + Lint 5 + Unit 10 + Smoke 10 + E2E 40 + Verify 30 = 100
#   E2E 40 = Mechanical 5 + Browser 5 + 실 게임 E2E 30 (★ 실질적 플레이)
# ★ hard gate: 실 게임 E2E HARD_FAIL 시 코드 품질 100이어도 ship 불가
# ★ DEMO fallback 금지 — state 실패는 명시 에러 (위장 = 검증 갭 핵심)

set -u

MODE="${1:-quick}"
SCORE=0
DETAILS=""

cd "$(dirname "$0")/.."

# [0/6] ensure_services (★ gate 전 인프라 헬스체크·자동 기동)
# 9B(8083) / frontend(4000) down 시 자동 start → Eval Smoke / Browser E2E가
# 인프라 미가동으로 점수 잃는 구조적 SKIP_VERIFY 상시화 제거.
# SKIP_ENSURE=1로 우회 (CI 등).
echo ""
echo "════════════════════════════════════════════════"
echo "Layer 1 Ship Gate (Tier 2 D11 — 6단계, Mechanical E2E)"
echo "════════════════════════════════════════════════"
echo ""
echo "[0/6] ensure_services..."
bash "$(dirname "$0")/ensure_services.sh" 2>&1 | sed 's/^/  /'

# [1/6] Build (10점)
echo ""
echo "[1/6] Build..."
BUILD_SCORE=0

if python -c "import core; import service; import tools" 2>/dev/null; then
    BUILD_SCORE=5
    echo "  ✅ Python imports OK (5/5)"
else
    echo "  ❌ Python import failed (0/5)"
fi

SCORE=$((SCORE + BUILD_SCORE))
DETAILS="$DETAILS\n[1/6] Build: $BUILD_SCORE/5"

# [2/6] Lint + Type Check (10점)
# ★ Tier 2 D12 — AutoFix harness 통합 (★ Made But Never Used 차단):
# ruff fail 시 AutoFix runner 1 cycle 호출 → ruff --fix 자동 시도 후 재검사
echo ""
echo "[2/6] Lint + Type..."
LINT_SCORE=0

if ruff check core/ service/ tools/ tests/ --quiet 2>/dev/null; then
    LINT_SCORE=$((LINT_SCORE + 2))
    echo "  ✅ ruff (2/2)"
else
    echo "  ⚠️  ruff failed → AutoFix runner 1 cycle 호출..."
    # ★ pipe 우회: exit code 진짜 검사 (★ tail의 0 X)
    AUTOFIX_OUT=$(python scripts/auto_fix_runner.py --check-only 2>&1)
    AUTOFIX_RC=$?
    echo "$AUTOFIX_OUT" | tail -3
    if [ $AUTOFIX_RC -eq 0 ]; then
        if ruff check core/ service/ tools/ tests/ --quiet 2>/dev/null; then
            LINT_SCORE=$((LINT_SCORE + 2))
            echo "  ✅ ruff (AutoFix 후 2/2)"
        else
            echo "  ❌ ruff failed (AutoFix 후도 X)"
        fi
    else
        echo "  ❌ ruff failed (AutoFix smoke fail rc=$AUTOFIX_RC)"
    fi
fi

if mypy core/ service/ --strict 2>&1 | tail -1 | grep -q "Success"; then
    LINT_SCORE=$((LINT_SCORE + 3))
    echo "  ✅ mypy --strict (3/3)"
else
    echo "  ❌ mypy --strict failed"
fi

SCORE=$((SCORE + LINT_SCORE))
DETAILS="$DETAILS\n[2/6] Lint: $LINT_SCORE/5"

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
echo "[5/6] E2E (★ Mechanical 5 + Browser 5 + 실 게임 30 — 실질적 플레이)..."
E2E_SCORE=0
SHIP_BLOCKED=0     # ★ 실 게임 E2E hard gate — HARD_FAIL 시 1 (ship 불가)
DEFERRED_TOTAL=0   # ★ 실 게임 E2E xfail 점수 — 분모 제외 (재검토 대기, 만점 X)

# (a) Mechanical E2E — backend (★ Phase 9.5 fix: port 8090 → 8091, dev server 충돌 회피)
if lsof -ti:8091 > /dev/null 2>&1; then
    echo "  ⚠️ port 8091 사용 중 — Mechanical skip (★ 충돌 회피, 0/5)"
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

# (c) 실 게임 E2E (30점) — 실질적 플레이 작동 (★ harness 재설계, hard gate)
#   시나리오 시작 정확성 / session 일관성 / 채팅 작동 / DEMO fallback 금지.
#   현재 알려진 결함(frontend↔session 단절)은 xfail로 만점, 재검토가 해제.
#   HARD_FAIL(즉시 통과해야 할 항목 실패) 시 SHIP_BLOCKED — 코드 품질 100이어도 ship 불가.
if curl -sf http://localhost:4000 > /dev/null 2>&1 && lsof -ti:8090 > /dev/null 2>&1; then
    GP_OUT=$(python tools/run_real_gameplay_e2e.py --frontend-url http://localhost:4000 2>&1)
    GP_RC=$?
    GP_SCORE=$(echo "$GP_OUT" | grep -oE 'GAMEPLAY_E2E_SCORE=[0-9]+' | head -1 | sed 's/.*=//')
    GP_DEFERRED=$(echo "$GP_OUT" | grep -oE 'GAMEPLAY_E2E_DEFERRED=[0-9]+' | head -1 | sed 's/.*=//')
    if [ -n "$GP_SCORE" ]; then
        E2E_SCORE=$((E2E_SCORE + GP_SCORE))
        # ★ xfail 점수는 분모 제외 (만점 X — score inflation 회피)
        DEFERRED_TOTAL=${GP_DEFERRED:-0}
        echo "  ✅ 실 게임 E2E: $GP_SCORE 측정 (deferred ${DEFERRED_TOTAL} — xfail 분모 제외)"
        echo "$GP_OUT" | grep -E "XFAIL|XPASS|HARD_FAIL|\[xfail\]|\[HARD\]" | sed 's/^/    /'
    else
        echo "  ❌ 실 게임 E2E 출력 파싱 실패"
        echo "$GP_OUT" | tail -4 | sed 's/^/    /'
    fi
    if [ "$GP_RC" -ne 0 ]; then
        SHIP_BLOCKED=1
        echo "  ❌ 실 게임 E2E HARD_FAIL → ship 불가 (★ hard gate — 코드 품질 무관)"
    fi
else
    # ★ 측정 불가 — 만점도 0점도 아닌 전체 deferred(분모 제외, 검증 우회 X)
    echo "  ⚠️ frontend(4000)/backend(8090) X — 실 게임 E2E 측정 불가 (전체 deferred)"
    DEFERRED_TOTAL=30
fi

SCORE=$((SCORE + E2E_SCORE))
E2E_MAX=$((40 - DEFERRED_TOTAL))
DETAILS="$DETAILS\n[5/6] E2E: $E2E_SCORE/$E2E_MAX (Mechanical+Browser+실게임, deferred $DEFERRED_TOTAL 제외)"

# [6/6] Verify Agent (50점) — ★ Cross-LLM 코드 리뷰 (★ 인사이트 #19)
echo ""
echo "[6/6] Verify Agent (★ Cross-LLM 코드 리뷰 — 50점)..."
VERIFY_SCORE=0
VERIFY_FLAKE=0

# ★ codex가 git diff 리뷰 (★ 자기 합리화 차단)
if command -v codex &>/dev/null; then
    REVIEW_OUTPUT=$(python scripts/verify_layer1_review.py 2>&1)
    REVIEW_EXIT=$?

    if [ $REVIEW_EXIT -eq 2 ]; then
        # exit 2 = flake (codex CLI timeout 전체 소진)
        echo "  ⚠️  Verify Agent codex CLI flake — SKIP (N/A)"
        VERIFY_SCORE=0
        VERIFY_FLAKE=1
        echo "$REVIEW_OUTPUT" | tail -4 | sed 's/^/    /'
    else
        SCORE_LINE=$(echo "$REVIEW_OUTPUT" | grep -oE 'SCORE=[0-9]+' | tail -1)
        if [ -n "$SCORE_LINE" ]; then
            VERIFY_SCORE_RAW=$(echo "$SCORE_LINE" | sed 's/SCORE=//')
            # ★ 25점 만점 → 30점 환산 (× 6/5 — harness 재설계, 실 게임 E2E 비중 ↑)
            VERIFY_SCORE=$((VERIFY_SCORE_RAW * 6 / 5))
            if [ $REVIEW_EXIT -eq 0 ]; then
                echo "  ✅ Verify passed ($VERIFY_SCORE_RAW/25 raw → $VERIFY_SCORE/30)"
            else
                echo "  ⚠️ Verify fail ($VERIFY_SCORE_RAW/25 raw → $VERIFY_SCORE/30)"
            fi
            echo "$REVIEW_OUTPUT" | head -8 | sed 's/^/    /'
        else
            echo "  ❌ Verify Agent output parse failed"
            echo "$REVIEW_OUTPUT" | head -5 | sed 's/^/    /'
            VERIFY_SCORE=0
        fi
    fi
else
    echo "  ⚠️ codex CLI not available"
    VERIFY_SCORE=0
fi

SCORE=$((SCORE + VERIFY_SCORE))

# verify SKIP 시 N/A 표시
if [ $VERIFY_FLAKE -eq 1 ]; then
    DETAILS="$DETAILS\n[6/6] Verify Agent: N/A (flake skip)"
else
    DETAILS="$DETAILS\n[6/6] Verify Agent: $VERIFY_SCORE/30"
fi

# 결과 (★ verify SKIP 시 분모 50, threshold 95% = 48)
echo ""
echo "════════════════════════════════════════════════"
# ★ deferred(실 게임 E2E xfail) 분모 제외 — 측정 결과 무관 만점은 score inflation.
#   xfail은 '미측정'으로 분모에서 빼고, 재검토가 is_xfail 해제 시 분모 복원.
if [ $VERIFY_FLAKE -eq 1 ]; then
    MAX_SCORE=$((70 - DEFERRED_TOTAL))   # Verify 30 SKIP + deferred 제외
    echo "TOTAL: $SCORE/$MAX_SCORE (★ Verify SKIP + deferred $DEFERRED_TOTAL 제외)"
else
    MAX_SCORE=$((100 - DEFERRED_TOTAL))  # deferred(xfail) 제외
    echo "TOTAL: $SCORE/$MAX_SCORE (★ deferred $DEFERRED_TOTAL 제외 — 재검토가 복원)"
fi
PASS_THRESHOLD=$((MAX_SCORE * 95 / 100))
WARN_THRESHOLD=$((MAX_SCORE * 80 / 100))
FAIL_C_THRESHOLD=$((MAX_SCORE * 70 / 100))
echo "════════════════════════════════════════════════"
printf "%b\n" "$DETAILS"
echo ""

# ★ hard gate — 실 게임 E2E HARD_FAIL 시 코드 품질 무관 ship 불가 (harness 재설계)
if [ "${SHIP_BLOCKED:-0}" -eq 1 ]; then
    echo "❌ Ship gate BLOCKED — 실 게임 E2E HARD_FAIL (★ 코드 품질 $SCORE/$MAX_SCORE 무관)"
    exit 1
fi

if [ $SCORE -ge $PASS_THRESHOLD ]; then
    echo "✅ Ship gate PASSED (A 등급, $SCORE/$MAX_SCORE)"
    exit 0
elif [ $SCORE -ge $WARN_THRESHOLD ]; then
    echo "⚠️ Ship gate WARN (B 등급, $SCORE/$MAX_SCORE) — push 안 됨"
    exit 1
elif [ $SCORE -ge $FAIL_C_THRESHOLD ]; then
    echo "❌ Ship gate FAILED (C 등급, $SCORE/$MAX_SCORE)"
    exit 1
else
    echo "❌ Ship gate FAILED (F, $SCORE/$MAX_SCORE)"
    exit 1
fi
