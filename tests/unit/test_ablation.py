"""Day 6: Ablation Runner 단위 테스트."""

from typing import Any
from unittest.mock import patch

from core.llm.client import LLMClient, LLMResponse, Prompt
from core.verify.integrated import IntegratedVerifier
from core.verify.mechanical import MechanicalChecker
from core.verify.retry import FeedbackMode
from tools.ablation.runner import (
    AblationModeResult,
    AblationRunner,
    AblationRunResult,
)


class MockLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "mock"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text="정상 응답입니다.", model="mock",
            cost_usd=0.0, latency_ms=10,
            input_tokens=0, output_tokens=0,
        )


class TestAblationRunner:
    def test_init(self) -> None:
        client = MockLLM()
        verifier = IntegratedVerifier(mechanical=MechanicalChecker())
        runner = AblationRunner(client=client, verifier=verifier)
        assert runner.client.model_name == "mock"

    def test_run_ablation_3_modes(self) -> None:
        client = MockLLM()
        verifier = IntegratedVerifier(mechanical=MechanicalChecker())
        runner = AblationRunner(client=client, verifier=verifier)

        result = runner.run_category_ablation(
            "persona_consistency",
            n=2,
            modes=[
                FeedbackMode.A_SCORE_EXPOSED,
                FeedbackMode.B_ISSUES_ONLY,
                FeedbackMode.C_ANONYMIZED,
            ],
        )

        assert len(result.mode_results) == 3
        assert "a" in result.mode_results
        assert "b" in result.mode_results
        assert "c" in result.mode_results

        for mode_result in result.mode_results.values():
            assert mode_result.total_count == 2

    def test_save(self, tmp_path: Any) -> None:
        from tools.ablation import runner as runner_module

        with patch.object(runner_module, "ABLATION_DIR", tmp_path):
            client = MockLLM()
            verifier = IntegratedVerifier(mechanical=MechanicalChecker())
            r = AblationRunner(client=client, verifier=verifier)

            result = r.run_category_ablation(
                "persona_consistency",
                n=1,
                modes=[FeedbackMode.B_ISSUES_ONLY],
            )
            out_dir = r.save(result)

            assert (out_dir / "result.json").exists()
            assert (out_dir / "summary.md").exists()


class TestAblationResult:
    def test_best_mode(self) -> None:
        result = AblationRunResult(
            run_id="t", timestamp="t", category="c", n_items=10,
            mode_results={
                "a": AblationModeResult("a", 10, 5, 50.0, 0.0),
                "b": AblationModeResult("b", 10, 8, 80.0, 0.0),
                "c": AblationModeResult("c", 10, 6, 60.0, 0.0),
            },
        )
        assert result.best_mode() == "b"

    def test_best_mode_empty(self) -> None:
        result = AblationRunResult(
            run_id="t", timestamp="t", category="c", n_items=0,
        )
        assert result.best_mode() == ""
