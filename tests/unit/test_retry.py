"""Day 4: Retry + Information Isolation + Ablation 단위 테스트."""

from typing import Any

import pytest

from core.llm.client import LLMClient, LLMResponse, Prompt
from core.verify.retry import (
    FeedbackMode,
    InformationLeakError,
    RetryAttempt,
    RetryFeedback,
    RetryResult,
    RetryRunner,
    validate_information_isolation,
)


# ─── 순차 응답 Mock 클라이언트 ────────────────────────────────


class MockClient(LLMClient):
    """순차 응답 mock: 호출 순서대로 responses 리스트에서 반환."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._call_count = 0

    @property
    def model_name(self) -> str:
        return "mock"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:  # type: ignore[override]
        text = self._responses[min(self._call_count, len(self._responses) - 1)]
        self._call_count += 1
        return LLMResponse(
            text=text,
            model="mock",
            cost_usd=0.0,
            latency_ms=1,
            input_tokens=0,
            output_tokens=0,
        )


# ─── FeedbackMode ─────────────────────────────────────────────


class TestFeedbackMode:
    def test_modes_exist(self) -> None:
        assert FeedbackMode.A_SCORE_EXPOSED.value == "a"
        assert FeedbackMode.B_ISSUES_ONLY.value == "b"
        assert FeedbackMode.C_ANONYMIZED.value == "c"


# ─── RetryFeedback.to_dict() ──────────────────────────────────


class TestRetryFeedbackToDict:
    def test_mode_b_default_excludes_score_and_verdict(self) -> None:
        fb = RetryFeedback(issues=["x"], mode=FeedbackMode.B_ISSUES_ONLY)
        d = fb.to_dict()
        assert "score" not in d
        assert "verdict" not in d

    def test_mode_b_includes_issues_and_suggestions(self) -> None:
        fb = RetryFeedback(
            issues=["bad korean"],
            suggestions=["use formal"],
            mode=FeedbackMode.B_ISSUES_ONLY,
        )
        d = fb.to_dict()
        assert d["issues"] == ["bad korean"]
        assert d["suggestions"] == ["use formal"]

    def test_mode_a_includes_score_and_verdict(self) -> None:
        fb = RetryFeedback(
            issues=["x"],
            score=70.0,
            verdict="warn",
            mode=FeedbackMode.A_SCORE_EXPOSED,
        )
        d = fb.to_dict()
        assert d["score"] == 70.0
        assert d["verdict"] == "warn"

    def test_mode_a_without_score_omits_score_key(self) -> None:
        fb = RetryFeedback(issues=[], mode=FeedbackMode.A_SCORE_EXPOSED)
        d = fb.to_dict()
        assert "score" not in d

    def test_mode_c_includes_confidence_band(self) -> None:
        fb = RetryFeedback(
            issues=["x"],
            confidence_band="medium",
            mode=FeedbackMode.C_ANONYMIZED,
        )
        d = fb.to_dict()
        assert d["confidence_band"] == "medium"
        assert "score" not in d
        assert "verdict" not in d

    def test_mode_c_without_band_omits_key(self) -> None:
        fb = RetryFeedback(issues=[], mode=FeedbackMode.C_ANONYMIZED)
        d = fb.to_dict()
        assert "confidence_band" not in d

    def test_default_mode_is_b(self) -> None:
        fb = RetryFeedback(issues=["x"])
        assert fb.mode == FeedbackMode.B_ISSUES_ONLY


# ─── RetryFeedback.to_prompt_section() ───────────────────────


class TestRetryFeedbackToPromptSection:
    def test_mode_b_includes_issues(self) -> None:
        fb = RetryFeedback(
            issues=["bad korean", "too long"],
            suggestions=["use formal"],
            mode=FeedbackMode.B_ISSUES_ONLY,
        )
        text = fb.to_prompt_section()
        assert "bad korean" in text
        assert "too long" in text
        assert "use formal" in text

    def test_mode_b_excludes_score_text(self) -> None:
        fb = RetryFeedback(
            issues=["x"],
            score=70.0,
            verdict="warn",
            mode=FeedbackMode.B_ISSUES_ONLY,
        )
        text = fb.to_prompt_section()
        assert "Score:" not in text
        assert "70" not in text

    def test_mode_a_includes_score_line(self) -> None:
        fb = RetryFeedback(
            issues=["x"],
            score=65.0,
            verdict="fail",
            mode=FeedbackMode.A_SCORE_EXPOSED,
        )
        text = fb.to_prompt_section()
        assert "65" in text
        assert "fail" in text

    def test_mode_c_includes_confidence_band(self) -> None:
        fb = RetryFeedback(
            issues=["x"],
            confidence_band="low",
            mode=FeedbackMode.C_ANONYMIZED,
        )
        text = fb.to_prompt_section()
        assert "low" in text

    def test_previous_attempt_header_always_present(self) -> None:
        fb = RetryFeedback(issues=[], mode=FeedbackMode.B_ISSUES_ONLY)
        text = fb.to_prompt_section()
        assert "Previous attempt" in text

    def test_empty_issues_no_issues_section(self) -> None:
        fb = RetryFeedback(issues=[], suggestions=[], mode=FeedbackMode.B_ISSUES_ONLY)
        text = fb.to_prompt_section()
        assert "Issues:" not in text


# ─── validate_information_isolation ──────────────────────────


class TestValidateInformationIsolation:
    def test_mode_b_clean_feedback_passes(self) -> None:
        fb = RetryFeedback(issues=["x"], mode=FeedbackMode.B_ISSUES_ONLY)
        # raises nothing
        validate_information_isolation(fb)

    def test_mode_a_skips_validation(self) -> None:
        # Mode A는 점수 노출이 의도적 → 검증 스킵
        fb = RetryFeedback(
            issues=["x"],
            score=70.0,
            verdict="warn",
            mode=FeedbackMode.A_SCORE_EXPOSED,
        )
        validate_information_isolation(fb)  # should not raise

    def test_mode_c_skips_validation(self) -> None:
        fb = RetryFeedback(
            issues=["x"],
            confidence_band="medium",
            mode=FeedbackMode.C_ANONYMIZED,
        )
        validate_information_isolation(fb)  # should not raise

    def test_mode_b_empty_issues_passes(self) -> None:
        fb = RetryFeedback(issues=[], mode=FeedbackMode.B_ISSUES_ONLY)
        validate_information_isolation(fb)


# ─── RetryAttempt ─────────────────────────────────────────────


class TestRetryAttempt:
    def test_fields_accessible(self) -> None:
        a = RetryAttempt(attempt_n=0, response_text="text", passed=True)
        assert a.attempt_n == 0
        assert a.response_text == "text"
        assert a.passed is True
        assert a.score is None

    def test_score_optional(self) -> None:
        a = RetryAttempt(attempt_n=1, response_text="text", passed=False, score=55.0)
        assert a.score == 55.0


# ─── RetryResult ──────────────────────────────────────────────


class TestRetryResult:
    def test_total_attempts_counts_all(self) -> None:
        attempts = [
            RetryAttempt(0, "bad", False),
            RetryAttempt(1, "good", True),
        ]
        result = RetryResult(final_response="good", attempts=attempts, succeeded=True)
        assert result.total_attempts() == 2

    def test_summary_pass(self) -> None:
        result = RetryResult(
            final_response="ok",
            attempts=[RetryAttempt(0, "ok", True)],
            succeeded=True,
        )
        assert "✅" in result.summary()
        assert "1" in result.summary()

    def test_summary_fail(self) -> None:
        result = RetryResult(
            final_response="bad",
            attempts=[RetryAttempt(0, "bad", False)],
            succeeded=False,
        )
        assert "❌" in result.summary()


# ─── RetryRunner ──────────────────────────────────────────────


class TestRetryRunner:
    def test_first_attempt_passes_immediately(self) -> None:
        client = MockClient(["good response"])

        def verify(text: str, ctx: dict[str, Any]) -> tuple[bool, RetryFeedback]:
            return (True, RetryFeedback())

        runner = RetryRunner(client=client, verify_fn=verify, max_retries=0)
        result = runner.run(Prompt(system="s", user="u"))

        assert result.succeeded
        assert result.total_attempts() == 1
        assert result.final_response == "good response"

    def test_retry_succeeds_on_second_attempt(self) -> None:
        client = MockClient(["bad", "good"])

        def verify(text: str, ctx: dict[str, Any]) -> tuple[bool, RetryFeedback]:
            passed = text == "good"
            fb = RetryFeedback(issues=["not good"]) if not passed else RetryFeedback()
            return (passed, fb)

        runner = RetryRunner(client=client, verify_fn=verify, max_retries=1)
        result = runner.run(Prompt(system="s", user="u"))

        assert result.succeeded
        assert result.total_attempts() == 2
        assert result.final_response == "good"

    def test_retry_succeeds_on_third_attempt(self) -> None:
        client = MockClient(["bad", "still bad", "good"])

        def verify(text: str, ctx: dict[str, Any]) -> tuple[bool, RetryFeedback]:
            passed = text == "good"
            fb = RetryFeedback(issues=["fail"]) if not passed else RetryFeedback()
            return (passed, fb)

        runner = RetryRunner(client=client, verify_fn=verify, max_retries=2)
        result = runner.run(Prompt(system="s", user="u"))

        assert result.succeeded
        assert result.total_attempts() == 3

    def test_max_retries_exhausted_returns_failure(self) -> None:
        client = MockClient(["bad", "bad", "bad"])

        def verify(text: str, ctx: dict[str, Any]) -> tuple[bool, RetryFeedback]:
            return (False, RetryFeedback(issues=["always bad"]))

        runner = RetryRunner(client=client, verify_fn=verify, max_retries=2)
        result = runner.run(Prompt(system="s", user="u"))

        assert not result.succeeded
        assert result.total_attempts() == 3

    def test_max_retries_zero_calls_generate_exactly_once(self) -> None:
        """Layer 1 정책: max_retries=0 → 1회만 호출."""
        client = MockClient(["bad"])

        def verify(text: str, ctx: dict[str, Any]) -> tuple[bool, RetryFeedback]:
            return (False, RetryFeedback(issues=["x"]))

        runner = RetryRunner(client=client, verify_fn=verify, max_retries=0)
        result = runner.run(Prompt(system="s", user="u"))

        assert not result.succeeded
        assert result.total_attempts() == 1
        assert client._call_count == 1

    def test_feedback_appended_to_retry_prompt(self) -> None:
        """재시도 시 feedback 내용이 prompt user 텍스트에 포함되는지 확인."""
        received_prompts: list[str] = []

        class RecordingClient(LLMClient):
            @property
            def model_name(self) -> str:
                return "recorder"

            def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
                received_prompts.append(prompt.user)
                text = "bad" if len(received_prompts) == 1 else "good"
                return LLMResponse(
                    text=text,
                    model="recorder",
                    cost_usd=0.0,
                    latency_ms=1,
                    input_tokens=0,
                    output_tokens=0,
                )

        def verify(text: str, ctx: dict[str, Any]) -> tuple[bool, RetryFeedback]:
            passed = text == "good"
            fb = RetryFeedback(
                issues=["quality too low"],
                mode=FeedbackMode.B_ISSUES_ONLY,
            ) if not passed else RetryFeedback()
            return (passed, fb)

        runner = RetryRunner(
            client=RecordingClient(),
            verify_fn=verify,
            max_retries=1,
        )
        result = runner.run(Prompt(system="s", user="original user message"))

        assert result.succeeded
        # 두 번째 프롬프트에 피드백 포함
        assert "quality too low" in received_prompts[1]
        assert "original user message" in received_prompts[1]

    def test_context_passed_to_verify_fn(self) -> None:
        """verify_fn에 context dict가 그대로 전달되는지 확인."""
        received_ctx: list[dict[str, Any]] = []

        client = MockClient(["any"])

        def verify(text: str, ctx: dict[str, Any]) -> tuple[bool, RetryFeedback]:
            received_ctx.append(ctx)
            return (True, RetryFeedback())

        runner = RetryRunner(client=client, verify_fn=verify, max_retries=0)
        runner.run(Prompt(system="s", user="u"), context={"key": "value"})

        assert received_ctx[0]["key"] == "value"
