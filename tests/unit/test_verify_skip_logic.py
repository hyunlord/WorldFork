"""verify_layer1_review retry / flake skip logic 단위 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.verify.layer1_review import Layer1ReviewResult
from scripts.verify_layer1_review import (
    CODEX_MAX_RETRIES,
    CODEX_TIMEOUT_SECONDS,
    _is_timeout_error,
    run_review_with_retry,
)


def _timeout_result() -> Layer1ReviewResult:
    return Layer1ReviewResult(
        score=0,
        verdict="fail",
        error="LLM call failed: CLI timeout after 600.0s for codex: ...",
        reviewer_model="gpt-5.5",
    )


def _pass_result() -> Layer1ReviewResult:
    return Layer1ReviewResult(
        score=22,
        verdict="pass",
        reviewer_model="gpt-5.5",
    )


def test_timeout_constant_is_600() -> None:
    """CODEX_TIMEOUT_SECONDS 600s 정합."""
    assert CODEX_TIMEOUT_SECONDS == 600.0


def test_retry_constant_is_1() -> None:
    """CODEX_MAX_RETRIES == 1."""
    assert CODEX_MAX_RETRIES == 1


def test_is_timeout_error_true() -> None:
    """CLI timeout 에러 탐지."""
    r = _timeout_result()
    assert _is_timeout_error(r) is True


def test_is_timeout_error_false_no_error() -> None:
    """에러 없음 → False."""
    r = _pass_result()
    assert _is_timeout_error(r) is False


def test_is_timeout_error_false_other_error() -> None:
    """다른 에러 → False."""
    r = Layer1ReviewResult(score=0, verdict="fail", error="JSON parsing failed")
    assert _is_timeout_error(r) is False


def test_run_with_retry_success_first_attempt() -> None:
    """첫 시도 성공 → is_flake=False."""
    agent = MagicMock()
    agent.review.return_value = _pass_result()

    result, is_flake = run_review_with_retry(agent, max_attempts=2)
    assert is_flake is False
    assert result is not None
    assert result.score == 22
    assert agent.review.call_count == 1


def test_run_with_retry_success_after_timeout() -> None:
    """1회 timeout 후 재시도 성공 → is_flake=False."""
    agent = MagicMock()
    agent.review.side_effect = [_timeout_result(), _pass_result()]

    result, is_flake = run_review_with_retry(agent, max_attempts=2)
    assert is_flake is False
    assert result is not None
    assert result.score == 22
    assert agent.review.call_count == 2


def test_run_with_retry_all_timeout_is_flake() -> None:
    """모든 시도 timeout → is_flake=True."""
    agent = MagicMock()
    agent.review.return_value = _timeout_result()

    result, is_flake = run_review_with_retry(agent, max_attempts=2)
    assert is_flake is True
    assert result is None
    assert agent.review.call_count == 2
