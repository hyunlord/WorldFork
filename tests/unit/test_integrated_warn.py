"""IntegratedVerifier verdict='warn' 통과 (★ Tier 2 D11+ A fix)."""

from typing import Any
from unittest.mock import MagicMock

from core.verify.integrated import IntegratedVerifier
from core.verify.llm_judge import JudgeCriteria, JudgeScore
from core.verify.mechanical import MechanicalChecker


class TestIntegratedVerifierWarnPasses:
    """A: verdict='warn'은 통과 (★ 30턴 진짜 데이터로 발견)."""

    @staticmethod
    def _make_judge(verdict: str, score: float = 80.0) -> MagicMock:
        mock = MagicMock()
        mock.evaluate.return_value = JudgeScore(
            score=score,
            verdict=verdict,  # type: ignore[arg-type]
            issues=["test issue"] if verdict != "pass" else [],
            suggestions=[],
            judge_model="test",
            cost_usd=0.0,
            latency_ms=100,
        )
        return mock

    @staticmethod
    def _criteria() -> JudgeCriteria:
        return JudgeCriteria(
            name="test",
            description="test",
            dimensions=["한국어"],
        )

    def _verify(self, verdict: str) -> Any:
        verifier = IntegratedVerifier(
            mechanical=MechanicalChecker(),
            judge=self._make_judge(verdict),
        )
        return verifier.verify(
            "정상 한국어 응답입니다.",
            {"language": "ko"},
            criteria=self._criteria(),
        )

    def test_warn_passes(self) -> None:
        """warn은 통과 (★ A fix)."""
        result = self._verify("warn")
        assert result.passed is True

    def test_pass_passes(self) -> None:
        """pass는 통과 (★ 기존 동작 유지)."""
        result = self._verify("pass")
        assert result.passed is True

    def test_fail_blocks(self) -> None:
        """fail은 차단 (★ A fix가 fail은 그대로 차단)."""
        result = self._verify("fail")
        assert result.passed is False
