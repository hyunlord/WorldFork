"""W1 D5 작업 1: BatchRunner backup_cli fallback 테스트."""

from typing import Any
from unittest.mock import patch

import pytest

from core.llm.client import LLMClient, LLMResponse, Prompt
from tools.ai_playtester.batch import BatchRunner
from tools.ai_playtester.persona import Persona, PersonaBehavior, PersonaPreferences
from tools.ai_playtester.runner import PlaytesterError


class MockGameLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "qwen35-9b-q3"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text="x", model="qwen35-9b-q3",
            cost_usd=0, latency_ms=0,
            input_tokens=0, output_tokens=0,
        )


def _make_persona(
    pid: str = "test",
    cli_to_use: str = "gemini",
    backup_cli: str | None = "claude-code",
    forbidden: list[str] | None = None,
) -> Persona:
    return Persona(
        id=pid,
        version=1,
        language="ko",
        status="active",
        demographic="test",
        behavior=PersonaBehavior(),
        preferences=PersonaPreferences(),
        expected_findings=[],
        cli_to_use=cli_to_use,
        backup_cli=backup_cli,
        forbidden_game_llms=forbidden or [],
        prompt_template="test",
    )


class TestIsCliAvailable:
    def test_returns_bool_for_known_key(self) -> None:
        result = BatchRunner._is_cli_available("claude_code")
        assert isinstance(result, bool)

    def test_unknown_key_returns_false(self) -> None:
        result = BatchRunner._is_cli_available("nonexistent_cli_xyz_123")
        assert result is False

    def test_gemini_not_available(self) -> None:
        result = BatchRunner._is_cli_available("gemini")
        assert result is False

    def test_codex_available(self) -> None:
        result = BatchRunner._is_cli_available("codex")
        assert result is True


class TestBackupCliFallback:
    @patch.object(BatchRunner, "_is_cli_available")
    def test_primary_available_returns_primary(self, mock_avail: Any) -> None:
        mock_avail.return_value = True
        runner = BatchRunner(game_client=MockGameLLM())
        persona = _make_persona(cli_to_use="codex")
        client = runner._create_playtester_with_fallback(persona)
        assert client.model_name == "gpt-5.5"

    @patch.object(BatchRunner, "_is_cli_available")
    def test_fallback_to_backup_when_primary_unavailable(
        self, mock_avail: Any
    ) -> None:
        # gemini unavailable, claude_code available
        mock_avail.side_effect = lambda key: key == "claude_code"
        runner = BatchRunner(game_client=MockGameLLM())
        persona = _make_persona(
            cli_to_use="gemini",
            backup_cli="claude-code",
            forbidden=["qwen35-9b-q3"],
        )
        client = runner._create_playtester_with_fallback(persona)
        assert client.model_name == "claude-code"

    @patch.object(BatchRunner, "_is_cli_available")
    def test_no_backup_raises(self, mock_avail: Any) -> None:
        mock_avail.return_value = False
        runner = BatchRunner(game_client=MockGameLLM())
        persona = _make_persona(cli_to_use="gemini", backup_cli=None)
        with pytest.raises(PlaytesterError, match="no backup_cli"):
            runner._create_playtester_with_fallback(persona)

    @patch.object(BatchRunner, "_is_cli_available")
    def test_backup_in_forbidden_raises(self, mock_avail: Any) -> None:
        # backup_key "claude_code" is in forbidden_game_llms
        mock_avail.side_effect = lambda key: key == "claude_code"
        runner = BatchRunner(game_client=MockGameLLM())
        persona = _make_persona(
            cli_to_use="gemini",
            backup_cli="claude-code",
            forbidden=["claude_code"],
        )
        with pytest.raises(PlaytesterError, match="forbidden_game_llms"):
            runner._create_playtester_with_fallback(persona)

    @patch.object(BatchRunner, "_is_cli_available")
    def test_both_unavailable_raises(self, mock_avail: Any) -> None:
        mock_avail.return_value = False
        runner = BatchRunner(game_client=MockGameLLM())
        persona = _make_persona(cli_to_use="gemini", backup_cli="gemini")
        with pytest.raises(PlaytesterError):
            runner._create_playtester_with_fallback(persona)
