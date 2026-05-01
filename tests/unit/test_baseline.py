"""Tier 1 W1 D2: BaselineRunner 단위 테스트 (Mock 기반)."""

from typing import Any
from unittest.mock import MagicMock, patch

from core.eval.spec import EvalItem
from core.llm.client import LLMClient, LLMResponse, Prompt
from tools.tier_1.baseline_runner import (
    BaselineAttempt,
    BaselineRunner,
)


class MockLLM(LLMClient):
    def __init__(self, name: str = "mock") -> None:
        self._name = name

    @property
    def model_name(self) -> str:
        return self._name

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text="안녕하세요, 셰인입니다.",
            model=self._name,
            cost_usd=0.0,
            latency_ms=100,
            input_tokens=20,
            output_tokens=10,
        )


def _make_item() -> EvalItem:
    return EvalItem(
        id="test_001",
        category="persona_consistency",
        version="v1",
        prompt={"system": "셰인", "user": "안녕"},
        expected_behavior={},
        criteria="persona_consistency",
        context={"language": "ko", "character_response": True},
    )


class TestBaselineRunnerInit:
    def test_generators_stored(self) -> None:
        gens: dict[str, LLMClient] = {"q1": MockLLM("q1"), "q2": MockLLM("q2")}
        runner = BaselineRunner(
            generators=gens,
            cm_verifier=MockLLM("cm"),
            local_verifier=MockLLM("local"),
        )
        assert "q1" in runner.generators
        assert "q2" in runner.generators

    def test_verifiers_stored(self) -> None:
        runner = BaselineRunner(
            generators={"q": MockLLM("q")},
            cm_verifier=MockLLM("cm"),
            local_verifier=MockLLM("local"),
        )
        assert runner.cm_verifier.model_name == "cm"
        assert runner.local_verifier.model_name == "local"


class TestBaselineRunnerRunItem:
    def test_run_item_returns_attempt(self) -> None:
        mock_score = MagicMock()
        mock_score.score = 85.0
        mock_score.verdict = "pass"

        with patch.object(
            BaselineRunner, "run_item", return_value=BaselineAttempt(
                item_id="test_001",
                category="persona_consistency",
                generator="qmock",
                mechanical_passed=True,
                mechanical_score=100.0,
                judge_cm_score=85.0,
                judge_cm_verdict="pass",
                judge_cm_model="cm",
                judge_local_score=80.0,
                judge_local_verdict="pass",
                judge_local_model="local",
                response_text="안녕하세요, 셰인입니다.",
                response_latency_ms=100,
                response_tokens_out=10,
            )
        ):
            runner = BaselineRunner(
                generators={"qmock": MockLLM("qmock")},
                cm_verifier=MockLLM("cm"),
                local_verifier=MockLLM("local"),
            )
            attempt = runner.run_item("qmock", _make_item())

        assert attempt.item_id == "test_001"
        assert attempt.generator == "qmock"
        assert attempt.response_text == "안녕하세요, 셰인입니다."

    def test_generation_failure_captured(self) -> None:
        class FailLLM(MockLLM):
            def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
                raise RuntimeError("connection refused")

        runner = BaselineRunner(
            generators={"fail": FailLLM("fail")},
            cm_verifier=MockLLM("cm"),
            local_verifier=MockLLM("local"),
        )
        attempt = runner.run_item("fail", _make_item())

        assert attempt.mechanical_passed is False
        assert "Generation failed" in attempt.issues[0]
        assert attempt.response_latency_ms == 0


class TestBaselineAttempt:
    def test_dataclass_fields(self) -> None:
        a = BaselineAttempt(
            item_id="x",
            category="c",
            generator="g",
            mechanical_passed=True,
            mechanical_score=100.0,
            judge_cm_score=90.0,
            judge_cm_verdict="pass",
            judge_cm_model="cm",
            judge_local_score=85.0,
            judge_local_verdict="pass",
            judge_local_model="local",
            response_text="text",
            response_latency_ms=100,
            response_tokens_out=10,
        )
        assert a.judge_cm_score == 90.0
        assert a.judge_local_score == 85.0
        assert a.issues == []

    def test_issues_default_empty(self) -> None:
        a = BaselineAttempt(
            item_id="x",
            category="c",
            generator="g",
            mechanical_passed=False,
            mechanical_score=0.0,
            judge_cm_score=None,
            judge_cm_verdict=None,
            judge_cm_model=None,
            judge_local_score=None,
            judge_local_verdict=None,
            judge_local_model=None,
            response_text="",
            response_latency_ms=0,
            response_tokens_out=0,
        )
        assert a.issues == []
