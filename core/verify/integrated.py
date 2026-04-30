"""통합 Verifier — Mechanical + LLM Judge (HARNESS_CORE 1장 4층위).

Day 4: 두 검증을 순차 적용 (mechanical 먼저 → judge).
mechanical critical 실패 시 judge 스킵 (토큰 절약).
"""

from dataclasses import dataclass
from typing import Any

from core.verify.cross_model import CrossModelEnforcer
from core.verify.llm_judge import JudgeCriteria, JudgeScore, LLMJudge
from core.verify.mechanical import MechanicalChecker
from core.verify.retry import FeedbackMode, RetryFeedback
from core.verify.rule import MechanicalResult


@dataclass
class IntegratedResult:
    """Mechanical + LLM Judge 통합 결과."""

    mechanical: MechanicalResult
    judge: JudgeScore | None
    passed: bool

    def total_score(self) -> float:
        if self.judge is None:
            return self.mechanical.score
        return (self.mechanical.score + self.judge.score) / 2

    def summary_line(self) -> str:
        parts = [self.mechanical.summary_line()]
        if self.judge is not None:
            parts.append(self.judge.summary_line())
        parts.append("→ 최종: ✅" if self.passed else "→ 최종: ❌")
        return " | ".join(parts)


class IntegratedVerifier:
    """Mechanical Checker + LLM Judge 통합.

    Cross-Model 정책: judge_client는 generator와 다른 family여야 함.
    cross_model 인자가 있으면 enforcer로 매번 검증.
    """

    def __init__(
        self,
        mechanical: MechanicalChecker,
        judge: LLMJudge | None = None,
        cross_model: CrossModelEnforcer | None = None,
        skip_judge_on_critical: bool = True,
    ) -> None:
        self.mechanical = mechanical
        self.judge = judge
        self.cross_model = cross_model
        self.skip_judge_on_critical = skip_judge_on_critical

    def verify(
        self,
        response: str,
        context: dict[str, Any],
        criteria: JudgeCriteria | None = None,
    ) -> IntegratedResult:
        """통합 검증.

        Steps:
          1) Mechanical check (LLM 0회)
          2) critical 있으면 judge 스킵 (옵션)
          3) Judge로 LLM 평가
          4) 양쪽 모두 통과해야 passed
        """
        mech_result = self.mechanical.check(response, context)

        if self.skip_judge_on_critical and mech_result.critical_count() > 0:
            return IntegratedResult(
                mechanical=mech_result,
                judge=None,
                passed=False,
            )

        judge_score: JudgeScore | None = None
        if self.judge is not None and criteria is not None:
            judge_score = self.judge.evaluate(response, criteria, context)

        passed = mech_result.passed
        if judge_score is not None:
            passed = passed and judge_score.verdict == "pass"

        return IntegratedResult(
            mechanical=mech_result,
            judge=judge_score,
            passed=passed,
        )


def make_retry_feedback(
    result: IntegratedResult,
    mode: FeedbackMode = FeedbackMode.B_ISSUES_ONLY,
) -> RetryFeedback:
    """IntegratedResult → RetryFeedback 변환.

    Mode B (default): 점수 / verdict 누설 X, issues + suggestions만 노출.
    Mode A: 점수 + verdict 노출 (Ablation 비교용).
    Mode C: confidence_band 익명화.
    """
    issues: list[str] = []
    suggestions: list[str] = []

    for f in result.mechanical.failures:
        issues.append(f"[{f.rule}] {f.detail}")
        if f.suggestion:
            suggestions.append(f.suggestion)

    if result.judge is not None:
        issues.extend(result.judge.issues)
        suggestions.extend(result.judge.suggestions)

    feedback = RetryFeedback(
        issues=issues,
        suggestions=suggestions,
        mode=mode,
    )

    if mode == FeedbackMode.A_SCORE_EXPOSED:
        score = result.total_score()
        feedback.score = score
        feedback.verdict = (
            "fail" if score < 70 else "warn" if score < 85 else "pass"
        )
    elif mode == FeedbackMode.C_ANONYMIZED:
        score = result.total_score()
        feedback.confidence_band = (
            "low" if score < 50 else "medium" if score < 80 else "high"
        )

    return feedback
