"""Tier 1.5 D1 작업 6: Layer1 Review Agent 테스트."""

import subprocess
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.llm.client import LLMResponse, Prompt
from core.verify.layer1_review import (
    Layer1ReviewAgent,
    Layer1ReviewResult,
)


class _MockClaudeLLM:
    """Mock Claude (★ 자기 합리화 차단 테스트용)."""

    @property
    def model_name(self) -> str:
        return "claude_code"  # ★ forbidden

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text="x", model="claude_code", cost_usd=0, latency_ms=0,
            input_tokens=0, output_tokens=0,
        )


class _MockCodexLLM:
    """Mock Codex (★ Cross-Model OK)."""

    def __init__(self, response_text: str = "") -> None:
        self._text = response_text

    @property
    def model_name(self) -> str:
        return "codex"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text=self._text, model="codex",
            cost_usd=0.005, latency_ms=2000,
            input_tokens=500, output_tokens=200,
        )


VALID_REVIEW_JSON = """{
    "score": 22,
    "verdict": "pass",
    "issues": [
        {
            "severity": "minor",
            "file": "test.py",
            "line": 10,
            "description": "minor style",
            "category": "other"
        }
    ],
    "summary": "Mostly OK"
}"""


class TestCrossModelEnforcement:
    def test_claude_reviewer_rejected(self) -> None:
        """★ claude로 자기 합리화 시도 → 즉시 reject."""
        with pytest.raises(ValueError, match="forbidden"):
            Layer1ReviewAgent(reviewer=_MockClaudeLLM())  # type: ignore[arg-type]

    def test_codex_reviewer_ok(self) -> None:
        """codex는 OK (다른 family)."""
        agent = Layer1ReviewAgent(reviewer=_MockCodexLLM())  # type: ignore[arg-type]
        assert agent is not None

    def test_custom_forbidden_list(self) -> None:
        """커스텀 forbidden list."""
        with pytest.raises(ValueError):
            Layer1ReviewAgent(
                reviewer=_MockCodexLLM(),  # type: ignore[arg-type]
                forbidden_reviewers=("codex",),
            )


class TestReviewWithMockedDiff:
    def test_no_diff_returns_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """git diff 비어 → pass 25/25."""

        def fake_run(*args: Any, **kwargs: Any) -> Any:
            mock = MagicMock()
            mock.stdout = ""
            return mock

        monkeypatch.setattr(subprocess, "run", fake_run)

        agent = Layer1ReviewAgent(reviewer=_MockCodexLLM())  # type: ignore[arg-type]
        result = agent.review()
        assert result.verdict == "pass"
        assert result.score == 25

    def test_diff_with_valid_review(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(*args: Any, **kwargs: Any) -> Any:
            mock = MagicMock()
            mock.stdout = "+ some code change\n"
            return mock

        monkeypatch.setattr(subprocess, "run", fake_run)

        agent = Layer1ReviewAgent(reviewer=_MockCodexLLM(VALID_REVIEW_JSON))  # type: ignore[arg-type]
        result = agent.review()
        assert result.score == 22
        assert result.verdict == "pass"
        assert result.passed
        assert len(result.issues) == 1

    def test_diff_with_invalid_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(*args: Any, **kwargs: Any) -> Any:
            mock = MagicMock()
            mock.stdout = "+ some code\n"
            return mock

        monkeypatch.setattr(subprocess, "run", fake_run)

        agent = Layer1ReviewAgent(reviewer=_MockCodexLLM("이건 JSON이 아냐"))  # type: ignore[arg-type]
        result = agent.review()
        assert result.verdict == "fail"
        assert result.error is not None

    def test_git_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(*args: Any, **kwargs: Any) -> None:
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(subprocess, "run", fake_run)

        agent = Layer1ReviewAgent(reviewer=_MockCodexLLM())  # type: ignore[arg-type]
        result = agent.review()
        assert result.verdict == "fail"
        assert result.error is not None


class TestPassedThreshold:
    def test_score_18_passed(self) -> None:
        result = Layer1ReviewResult(score=18, verdict="pass", reviewer_model="codex")
        assert result.passed

    def test_score_25_passed(self) -> None:
        result = Layer1ReviewResult(score=25, verdict="pass", reviewer_model="codex")
        assert result.passed

    def test_score_17_not_passed(self) -> None:
        """자료 cutoff 18+ — 17은 미달."""
        result = Layer1ReviewResult(score=17, verdict="pass", reviewer_model="codex")
        assert not result.passed

    def test_warn_not_passed(self) -> None:
        result = Layer1ReviewResult(score=20, verdict="warn", reviewer_model="codex")
        assert not result.passed

    def test_fail_with_error(self) -> None:
        result = Layer1ReviewResult(
            score=20, verdict="pass", reviewer_model="codex", error="some error"
        )
        assert not result.passed
