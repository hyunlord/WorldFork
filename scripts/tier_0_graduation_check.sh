#!/bin/bash
# Tier 0 졸업 체크리스트 (자동 검증 가능 항목)
# ★ 메모리 안전 (v2): pytest / verify.sh 호출 X. import 확인만.
#
# 사용: scripts/tier_0_graduation_check.sh

set -u

cd "$(dirname "$0")/.."

PASSED=0
TOTAL=0

check() {
    local description="$1"
    local result="$2"
    TOTAL=$((TOTAL + 1))
    if [ "$result" = "yes" ]; then
        PASSED=$((PASSED + 1))
        echo "  ✅ $description"
    else
        echo "  ❌ $description"
    fi
}

echo ""
echo "════════════════════════════════════════════════"
echo "Tier 0 졸업 체크 (자동 검증 가능 항목)"
echo "════════════════════════════════════════════════"
echo ""

echo "[1] 하네스 모듈 작동"
echo ""

# Mechanical Checker 7룰
RULE_COUNT=$(source .venv/bin/activate 2>/dev/null; python -c "
from core.verify.mechanical import MechanicalChecker
print(len(MechanicalChecker().rules))
" 2>/dev/null)
[ "${RULE_COUNT:-0}" -ge 7 ] && check "Mechanical Checker 7+ 룰 (현재: ${RULE_COUNT})" "yes" \
    || check "Mechanical Checker 7+ 룰 (현재: ${RULE_COUNT:-0})" "no"

# LLM Judge
source .venv/bin/activate 2>/dev/null; python -c "from core.verify.llm_judge import LLMJudge, JudgeScore" 2>/dev/null \
    && check "LLM Judge 모듈 OK" "yes" || check "LLM Judge 모듈 OK" "no"

# Cross-Model
ENABLED=$(source .venv/bin/activate 2>/dev/null; python -c "
from core.verify.cross_model import CrossModelEnforcer
print('yes' if CrossModelEnforcer().is_enabled() else 'no')
" 2>/dev/null)
check "Cross-Model 매트릭스 활성화" "${ENABLED:-no}"

# Retry + Ablation
source .venv/bin/activate 2>/dev/null; python -c "from core.verify.retry import FeedbackMode, RetryRunner" 2>/dev/null \
    && check "Retry + Ablation 인프라" "yes" || check "Retry + Ablation 인프라" "no"

echo ""
echo "[2] Eval Set"
echo ""

# 5 카테고리
CAT_COUNT=$(source .venv/bin/activate 2>/dev/null; python -c "
from core.eval.spec import list_categories
print(len(list_categories()))
" 2>/dev/null)
[ "${CAT_COUNT:-0}" -ge 5 ] && check "Eval Set 5+ 카테고리 (현재: ${CAT_COUNT})" "yes" \
    || check "Eval Set 5+ 카테고리 (현재: ${CAT_COUNT:-0})" "no"

# 50 케이스 (v1.jsonl 실제 존재하는 파일만 합산)
CASE_COUNT=$(source .venv/bin/activate 2>/dev/null; python -c "
import pathlib
from core.eval.spec import EvalSpec
total = sum(EvalSpec.load(f.parent.name, 'v1').total_count() for f in sorted(pathlib.Path('evals').glob('*/v1.jsonl')))
print(total)
" 2>/dev/null)
[ "${CASE_COUNT:-0}" -ge 50 ] && check "Eval 50+ 케이스 (현재: ${CASE_COUNT})" "yes" \
    || check "Eval 50+ 케이스 (현재: ${CASE_COUNT:-0})" "no"

# Filter Pipeline
source .venv/bin/activate 2>/dev/null; python -c "
from core.eval.filter_pipeline import STANDARD_FILTER_PIPELINE
assert len(STANDARD_FILTER_PIPELINE.filters) >= 3
" 2>/dev/null \
    && check "Filter Pipeline 3+ 필터" "yes" || check "Filter Pipeline 3+ 필터" "no"

echo ""
echo "[3] AI Playtester"
echo ""

# 3 페르소나
PERSONA_COUNT=$(source .venv/bin/activate 2>/dev/null; python -c "
from tools.ai_playtester.persona import list_personas
print(len(list_personas('tier_0')))
" 2>/dev/null)
[ "${PERSONA_COUNT:-0}" -ge 3 ] && check "Tier 0 페르소나 3+ (현재: ${PERSONA_COUNT})" "yes" \
    || check "Tier 0 페르소나 3+ (현재: ${PERSONA_COUNT:-0})" "no"

# Cross-Model 정합 (다른 CLI 사용)
DIFF_CLIS=$(source .venv/bin/activate 2>/dev/null; python -c "
from tools.ai_playtester.persona import load_persona, list_personas
clis = {load_persona(p).cli_to_use for p in list_personas('tier_0')}
print(len(clis))
" 2>/dev/null)
[ "${DIFF_CLIS:-0}" -ge 3 ] && check "페르소나 3종 다른 CLI 사용 (Cross-Model)" "yes" \
    || check "페르소나 3종 다른 CLI 사용 (현재: ${DIFF_CLIS:-0}종)" "no"

echo ""
echo "[4] 비용 추적 인프라"
echo ""

source .venv/bin/activate 2>/dev/null; python -c "
from core.llm.client import LLMResponse
r = LLMResponse(text='', model='', cost_usd=0.0, latency_ms=0, input_tokens=0, output_tokens=0)
assert hasattr(r, 'cost_usd')
assert hasattr(r, 'latency_ms')
" 2>/dev/null && check "LLMResponse cost_usd / latency_ms 필드" "yes" \
    || check "LLMResponse cost_usd / latency_ms 필드" "no"

echo ""
echo "[5] 자동 검증 불가 항목 (Tier 1+ 후로 미룸)"
echo ""
echo "  ⏭  30분 시나리오 완주 가능 — Tier 1+ DGX 진입 후"
echo "  ⏭  본인 5회 + 친구 3-5명 플레이 — Tier 1+ DGX 진입 후"
echo "  ⏭  친구 3명 끝까지 완주 — Tier 1+"
echo "  ⏭  정성 피드백 평균 \"재미있다\" — Tier 1+"
echo "  ⏭  Mechanical 통과율 80%+ baseline — Tier 1+ 본격 측정 시"
echo "  ⏭  Persona consistency baseline — Tier 1+ 본격 측정 시"
echo ""
echo "  (claude -p latency 14-33초 구조적 한계 → DGX Local LLM 1-3초에서 본격)"

echo ""
echo "════════════════════════════════════════════════"
echo "자동 체크 결과: $PASSED/$TOTAL 통과"
echo "════════════════════════════════════════════════"
echo ""

if [ "$PASSED" -eq "$TOTAL" ]; then
    echo "🎉 Tier 0 자동 검증 가능 항목 모두 통과"
    echo ""
    echo "다음 단계:"
    echo "  - docs/RETROSPECTIVE_TIER_0.md 확인"
    echo "  - Tier 1 진입 결정 (본인 + DGX Spark 셋업)"
    exit 0
else
    FAILED=$((TOTAL - PASSED))
    echo "❌ ${FAILED}개 항목 미통과. 위 ❌ 항목 점검."
    exit 1
fi
