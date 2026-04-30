"""Day 6: EvalRunner 단위 테스트 (Mock LLM 활용)."""

from typing import Any
from unittest.mock import patch

import pytest

from core.eval.runner import (
    EvalAttempt,
    EvalRunner,
    EvalRunResult,
)
from core.eval.spec import EvalItem
from core.llm.client import LLMClient, LLMResponse, Prompt
from core.verify.integrated import IntegratedVerifier
from core.verify.mechanical import MechanicalChecker


class MockLLMOK(LLMClient):
    """정상 응답 mock."""

    @property
    def model_name(self) -> str:
        return "mock-ok"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text="정상적인 한국어 응답입니다.",
            model="mock-ok",
            cost_usd=0.0,
            latency_ms=10,
            input_tokens=0,
            output_tokens=0,
        )


class MockLLMFail(LLMClient):
    """예외 던지는 mock."""

    @property
    def model_name(self) -> str:
        return "mock-fail"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        raise RuntimeError("LLM call failed")


def _make_item(item_id: str = "test_001") -> EvalItem:
    return EvalItem(
        id=item_id,
        category="persona_consistency",
        version="v1",
        prompt={"system": "당신은 셰인.", "user": "안녕"},
        expected_behavior={"in_character": True},
        criteria="persona_consistency",
        context={"language": "ko", "character_response": True},
    )


class TestEvalRunner:
    def test_run_item_success(self) -> None:
        client = MockLLMOK()
        verifier = IntegratedVerifier(mechanical=MechanicalChecker())
        runner = EvalRunner(client=client, verifier=verifier)

        item = _make_item()
        attempt = runner.run_item(item)

        assert attempt.item_id == "test_001"
        assert attempt.category == "persona_consistency"
        assert attempt.response_text == "정상적인 한국어 응답입니다."
        assert attempt.mechanical_passed
        assert attempt.final_passed

    def test_run_item_generation_fails(self) -> None:
        client = MockLLMFail()
        verifier = IntegratedVerifier(mechanical=MechanicalChecker())
        runner = EvalRunner(client=client, verifier=verifier)

        item = _make_item()
        attempt = runner.run_item(item)

        assert "ERROR" in attempt.response_text
        assert not attempt.final_passed
        assert any("Generation failed" in i for i in attempt.issues)

    def test_run_category_real_eval_set(self) -> None:
        client = MockLLMOK()
        verifier = IntegratedVerifier(mechanical=MechanicalChecker())
        runner = EvalRunner(client=client, verifier=verifier)

        result = runner.run_category("persona_consistency", n=3)

        assert result.total_count() == 3
        assert result.passed_count() == 3
        assert result.score is not None
        assert result.score.total > 0

    def test_run_category_unknown(self) -> None:
        client = MockLLMOK()
        verifier = IntegratedVerifier(mechanical=MechanicalChecker())
        runner = EvalRunner(client=client, verifier=verifier)

        with pytest.raises(FileNotFoundError):
            runner.run_category("does_not_exist")

    def test_save_creates_files(self, tmp_path: Any) -> None:
        from core.eval import runner as runner_module
        with patch.object(runner_module, "RUNS_DIR", tmp_path):
            client = MockLLMOK()
            verifier = IntegratedVerifier(mechanical=MechanicalChecker())
            r = EvalRunner(client=client, verifier=verifier)

            result = r.run_category("persona_consistency", n=1)
            out_dir = r.save(result)

            assert (out_dir / "config.yaml").exists()
            assert (out_dir / "eval_results.json").exists()
            assert (out_dir / "summary.md").exists()

            summary = (out_dir / "summary.md").read_text(encoding="utf-8")
            assert "Eval Run" in summary
            assert "결과" in summary


class TestEvalRunResult:
    def test_pass_rate(self) -> None:
        attempts = [
            EvalAttempt(
                item_id=f"a{i}", category="t", response_text="r",
                mechanical_passed=True, mechanical_score=100.0,
                judge_score=None, judge_verdict=None,
                final_passed=(i % 2 == 0),
            )
            for i in range(4)
        ]
        result = EvalRunResult(
            run_id="test", timestamp="t", git_sha="x",
            config={}, attempts=attempts,
        )
        assert result.pass_rate() == 0.5
