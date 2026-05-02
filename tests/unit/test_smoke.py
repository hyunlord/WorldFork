"""Eval Smoke 테스트 (Mock LLM — LLM 호출 0회)."""

from unittest.mock import MagicMock

from core.eval.smoke import (
    PASS_RATE_THRESHOLD,
    SAMPLES_PER_CATEGORY,
    SmokeResult,
    _sample_items,
    run_smoke,
)
from core.llm.client import LLMResponse


def _mock_llm(text: str) -> MagicMock:
    """항상 같은 텍스트를 반환하는 Mock LLM."""
    llm = MagicMock()
    resp = MagicMock(spec=LLMResponse)
    resp.text = text
    llm.generate.return_value = resp
    return llm


class TestSampleItems:
    def test_samples_per_category(self) -> None:
        items = _sample_items(["korean_quality", "ai_breakout"], n=2)
        assert len(items) == 4

    def test_respects_n(self) -> None:
        items = _sample_items(["korean_quality"], n=1)
        assert len(items) == 1

    def test_unknown_category_skipped(self) -> None:
        items = _sample_items(["unknown_category_xyz"])
        assert len(items) == 0

    def test_all_categories(self) -> None:
        items = _sample_items(
            ["korean_quality", "ai_breakout", "ip_leakage",
             "persona_consistency", "world_consistency"],
            n=SAMPLES_PER_CATEGORY,
        )
        assert len(items) == 5 * SAMPLES_PER_CATEGORY


class TestRunSmoke:
    def test_pass_with_good_response(self) -> None:
        # 한국어 자연스러운 응답 — MechanicalChecker 통과
        good_text = (
            "동굴 안은 어두컴컴하고 차가운 공기가 감돌았습니다. "
            "모험가는 횃불을 들고 앞으로 나아갔습니다."
        )
        llm = _mock_llm(good_text)
        result = run_smoke(
            llm,
            categories=["korean_quality"],
            n=2,
        )
        assert result.total == 2
        assert result.passed >= 1

    def test_llm_error_marked_failed(self) -> None:
        llm = MagicMock()
        llm.generate.side_effect = RuntimeError("connection refused")
        result = run_smoke(llm, categories=["korean_quality"], n=1)
        assert result.total == 1
        assert result.passed == 0
        assert not result.attempts[0].mechanical_passed

    def test_pass_rate_calculation(self) -> None:
        result = SmokeResult()
        result.total = 10
        result.passed = 10
        assert result.pass_rate == 1.0
        assert result.succeeded is True

    def test_fail_rate_below_threshold(self) -> None:
        result = SmokeResult()
        result.total = 10
        result.passed = 9  # 90% < 95%
        assert result.pass_rate == 0.9
        assert result.succeeded is False

    def test_pass_rate_threshold_constant(self) -> None:
        assert PASS_RATE_THRESHOLD == 0.95

    def test_empty_result_not_succeeded(self) -> None:
        result = SmokeResult()
        assert result.pass_rate == 0.0
        assert result.succeeded is False
