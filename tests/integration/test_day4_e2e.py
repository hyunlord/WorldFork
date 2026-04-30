"""Day 4 통합 테스트.

1. (fast) Mock으로 IntegratedVerifier 작동 확인
2. (fast) Cross-Model enforcer 강제 확인
3. (slow) 실제 codex CLI로 Judge 1번 호출

실행:
  pytest tests/integration/test_day4_e2e.py -v -m "not slow"
  pytest tests/integration/test_day4_e2e.py -v -m slow -s
"""

from typing import Any

import pytest

from core.llm.client import JSONLLMResponse, LLMClient, LLMResponse, Prompt
from core.verify.cross_model import CrossModelEnforcer, CrossModelError
from core.verify.integrated import IntegratedVerifier, make_retry_feedback
from core.verify.llm_judge import JudgeCriteria, LLMJudge
from core.verify.mechanical import MechanicalChecker
from core.verify.retry import FeedbackMode

# ─── Mock Judge 클라이언트 ────────────────────────────────────


class MockJudgeClient(LLMClient):
    """고정 JSON 응답 반환 mock."""

    def __init__(self, parsed: dict[str, Any], model: str = "mock-judge") -> None:
        self._parsed = parsed
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:  # type: ignore[override]
        raise NotImplementedError

    def generate_json(
        self,
        prompt: Prompt,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> JSONLLMResponse:
        return JSONLLMResponse(
            parsed=self._parsed,
            text=str(self._parsed),
            model=self._model,
            cost_usd=0.0,
            latency_ms=10,
            input_tokens=100,
            output_tokens=50,
        )


# ─── IntegratedVerifier: mechanical only ─────────────────────


def test_integrated_verifier_mechanical_only_clean_response() -> None:
    """judge 없이 mechanical만 사용. 정상 응답 → passed=True."""
    verifier = IntegratedVerifier(mechanical=MechanicalChecker())
    ctx = {"language": "ko", "character_response": True}

    result = verifier.verify("정상적인 한국어 응답입니다.", ctx)

    assert result.passed
    assert result.judge is None
    assert result.total_score() == 100.0


def test_integrated_verifier_mechanical_only_ip_leak_fails() -> None:
    """judge 없이 mechanical만. IP 누출 → passed=False."""
    verifier = IntegratedVerifier(mechanical=MechanicalChecker())
    ctx = {
        "language": "ko",
        "character_response": True,
        "ip_forbidden_terms": ["비요른"],
    }

    result = verifier.verify("비요른이 등장한다.", ctx)

    assert not result.passed
    assert result.judge is None
    assert result.mechanical.critical_count() >= 1


# ─── IntegratedVerifier: with mock judge ─────────────────────


def test_integrated_verifier_judge_fail_overrides_mechanical_pass() -> None:
    """mechanical pass + judge fail → 전체 passed=False."""
    judge_client = MockJudgeClient({
        "score": 60,
        "verdict": "fail",
        "issues": ["weak persona"],
        "suggestions": ["be more in-character"],
    })
    verifier = IntegratedVerifier(
        mechanical=MechanicalChecker(),
        judge=LLMJudge(judge_client),
    )
    ctx = {"language": "ko", "character_response": True}
    criteria = JudgeCriteria(name="persona", description="x", dimensions=[])

    result = verifier.verify("정상 한국어.", ctx, criteria=criteria)

    assert result.mechanical.passed
    assert result.judge is not None
    assert result.judge.verdict == "fail"
    assert not result.passed


def test_integrated_verifier_judge_pass_with_mechanical_pass() -> None:
    """mechanical pass + judge pass → 전체 passed=True."""
    judge_client = MockJudgeClient({
        "score": 92,
        "verdict": "pass",
        "issues": [],
        "suggestions": [],
    })
    verifier = IntegratedVerifier(
        mechanical=MechanicalChecker(),
        judge=LLMJudge(judge_client),
    )
    ctx = {"language": "ko", "character_response": True}
    criteria = JudgeCriteria(name="quality", description="d", dimensions=[])

    result = verifier.verify("좋은 한국어 응답입니다.", ctx, criteria=criteria)

    assert result.mechanical.passed
    assert result.judge is not None
    assert result.judge.verdict == "pass"
    assert result.passed


def test_integrated_verifier_no_criteria_skips_judge() -> None:
    """criteria=None이면 judge client가 있어도 judge 스킵."""
    judge_client = MockJudgeClient({
        "score": 100,
        "verdict": "pass",
        "issues": [],
        "suggestions": [],
    })
    verifier = IntegratedVerifier(
        mechanical=MechanicalChecker(),
        judge=LLMJudge(judge_client),
    )
    ctx = {"language": "ko", "character_response": True}

    result = verifier.verify("정상 응답.", ctx, criteria=None)

    assert result.judge is None


def test_integrated_skips_judge_on_critical_failure() -> None:
    """critical mechanical failure → judge 스킵 (토큰 절약)."""
    judge_client = MockJudgeClient({
        "score": 100,
        "verdict": "pass",
        "issues": [],
        "suggestions": [],
    })
    verifier = IntegratedVerifier(
        mechanical=MechanicalChecker(),
        judge=LLMJudge(judge_client),
        skip_judge_on_critical=True,
    )
    ctx = {
        "language": "ko",
        "character_response": True,
        "ip_forbidden_terms": ["비요른"],
    }
    criteria = JudgeCriteria(name="t", description="d", dimensions=[])

    result = verifier.verify("비요른이 등장한다.", ctx, criteria=criteria)

    assert not result.passed
    assert result.judge is None  # critical이므로 judge 스킵


def test_integrated_does_not_skip_judge_when_flag_false() -> None:
    """skip_judge_on_critical=False면 critical 있어도 judge 호출."""
    judge_client = MockJudgeClient({
        "score": 100,
        "verdict": "pass",
        "issues": [],
        "suggestions": [],
    })
    verifier = IntegratedVerifier(
        mechanical=MechanicalChecker(),
        judge=LLMJudge(judge_client),
        skip_judge_on_critical=False,
    )
    ctx = {
        "language": "ko",
        "character_response": True,
        "ip_forbidden_terms": ["비요른"],
    }
    criteria = JudgeCriteria(name="t", description="d", dimensions=[])

    result = verifier.verify("비요른이 등장한다.", ctx, criteria=criteria)

    # judge는 호출됐지만 mechanical critical로 passed=False
    assert result.judge is not None
    assert not result.passed


def test_integrated_total_score_average_with_judge() -> None:
    """total_score = (mechanical.score + judge.score) / 2."""
    judge_client = MockJudgeClient({
        "score": 80,
        "verdict": "warn",
        "issues": [],
        "suggestions": [],
    })
    verifier = IntegratedVerifier(
        mechanical=MechanicalChecker(),
        judge=LLMJudge(judge_client),
    )
    ctx = {"language": "ko", "character_response": True}
    criteria = JudgeCriteria(name="t", description="d", dimensions=[])

    result = verifier.verify("정상 응답.", ctx, criteria=criteria)

    # mechanical=100, judge=80 → (100+80)/2 = 90
    assert result.total_score() == pytest.approx(90.0)


# ─── make_retry_feedback ──────────────────────────────────────


def test_make_retry_feedback_mode_b_excludes_score() -> None:
    """Mode B: score/verdict 누설 없음."""
    verifier = IntegratedVerifier(mechanical=MechanicalChecker())
    ctx = {
        "language": "ko",
        "character_response": True,
        "ip_forbidden_terms": ["비요른"],
    }
    result = verifier.verify("비요른 등장.", ctx)

    fb = make_retry_feedback(result, mode=FeedbackMode.B_ISSUES_ONLY)
    d = fb.to_dict()

    assert "score" not in d
    assert "verdict" not in d
    assert len(fb.issues) > 0


def test_make_retry_feedback_mode_a_includes_score() -> None:
    """Mode A: score + verdict 노출."""
    verifier = IntegratedVerifier(mechanical=MechanicalChecker())
    ctx = {
        "language": "ko",
        "character_response": True,
        "ip_forbidden_terms": ["비요른"],
    }
    result = verifier.verify("비요른 등장.", ctx)

    fb = make_retry_feedback(result, mode=FeedbackMode.A_SCORE_EXPOSED)

    assert fb.score is not None
    assert fb.verdict in ("pass", "warn", "fail")


def test_make_retry_feedback_mode_c_confidence_band() -> None:
    """Mode C: confidence_band 반환."""
    verifier = IntegratedVerifier(mechanical=MechanicalChecker())
    ctx = {
        "language": "ko",
        "character_response": True,
        "ip_forbidden_terms": ["비요른"],
    }
    result = verifier.verify("비요른 등장.", ctx)

    fb = make_retry_feedback(result, mode=FeedbackMode.C_ANONYMIZED)

    assert fb.confidence_band in ("low", "medium", "high")


def test_make_retry_feedback_judge_issues_included() -> None:
    """judge issues가 feedback.issues에 포함되는지 확인."""
    judge_client = MockJudgeClient({
        "score": 55,
        "verdict": "fail",
        "issues": ["judge_issue_1"],
        "suggestions": ["judge_suggestion_1"],
    })
    verifier = IntegratedVerifier(
        mechanical=MechanicalChecker(),
        judge=LLMJudge(judge_client),
    )
    ctx = {"language": "ko", "character_response": True}
    criteria = JudgeCriteria(name="t", description="d", dimensions=[])

    result = verifier.verify("정상 응답.", ctx, criteria=criteria)
    fb = make_retry_feedback(result, mode=FeedbackMode.B_ISSUES_ONLY)

    assert "judge_issue_1" in fb.issues
    assert "judge_suggestion_1" in fb.suggestions


def test_make_retry_feedback_default_mode_is_b() -> None:
    """make_retry_feedback 기본 mode = B."""
    verifier = IntegratedVerifier(mechanical=MechanicalChecker())
    ctx = {
        "language": "ko",
        "character_response": True,
        "ip_forbidden_terms": ["비요른"],
    }
    result = verifier.verify("비요른 등장.", ctx)

    fb = make_retry_feedback(result)

    assert fb.mode == FeedbackMode.B_ISSUES_ONLY


# ─── Cross-Model enforcer 통합 ────────────────────────────────


def test_cross_model_enforcer_real_config_loaded() -> None:
    enforcer = CrossModelEnforcer()
    assert enforcer.is_enabled()


def test_cross_model_rejects_same_model_for_game_response() -> None:
    enforcer = CrossModelEnforcer()
    with pytest.raises(CrossModelError):
        enforcer.check_pair("game_response", "claude_code", "claude_code")


def test_cross_model_accepts_claude_codex_pair() -> None:
    enforcer = CrossModelEnforcer()
    enforcer.check_pair("game_response", "claude_code", "codex")


def test_cross_model_get_verifier_excludes_generator() -> None:
    enforcer = CrossModelEnforcer()
    v = enforcer.get_verifier_for("game_response", "claude_code")
    assert v != "claude_code"
    assert v in ("codex", "gemini")


# ─── IntegratedResult.summary_line ───────────────────────────


def test_integrated_result_summary_line_pass() -> None:
    verifier = IntegratedVerifier(mechanical=MechanicalChecker())
    ctx = {"language": "ko", "character_response": True}

    result = verifier.verify("좋은 응답입니다.", ctx)
    line = result.summary_line()

    assert "Mechanical:" in line
    assert "✅" in line


def test_integrated_result_summary_line_fail() -> None:
    verifier = IntegratedVerifier(mechanical=MechanicalChecker())
    ctx = {
        "language": "ko",
        "character_response": True,
        "ip_forbidden_terms": ["비요른"],
    }

    result = verifier.verify("비요른 등장.", ctx)
    line = result.summary_line()

    assert "❌" in line


# ─── 실제 codex Judge 호출 (slow) ─────────────────────────────


@pytest.mark.slow
def test_real_codex_judge() -> None:
    """실제 codex CLI로 Judge 1번 호출 (~20초).

    -m slow 옵션으로만 실행.
    """
    from core.llm.cli_client import CLIClient

    print("\n" + "=" * 60)
    print("  실제 codex Judge 호출")
    print("=" * 60)

    judge_client = CLIClient(model_key="codex")
    judge = LLMJudge(judge_client)

    test_response = '셰인이 환하게 웃으며 손을 마주 든다. "투르윈, 오셨군요."'

    criteria = JudgeCriteria(
        name="korean_quality",
        description="Korean speech naturalness and persona consistency",
        dimensions=[
            "Natural Korean (no translation feel)",
            "Formal speech consistency (셰인 = formal)",
            "Character voice (mage personality)",
        ],
    )

    result = judge.evaluate(test_response, criteria, context={"character": "셰인"})

    print(f"  Judge: {judge_client.model_name}")
    print(f"  Score: {result.score}/100")
    print(f"  Verdict: {result.verdict}")
    print(f"  Issues: {result.issues}")
    print(f"  Suggestions: {result.suggestions}")
    print(f"  Latency: {result.latency_ms}ms")
    print("=" * 60)

    assert 0 <= result.score <= 100
    assert result.verdict in ("pass", "warn", "fail")
    assert isinstance(result.issues, list)
    assert isinstance(result.suggestions, list)
    assert result.judge_model == judge_client.model_name
