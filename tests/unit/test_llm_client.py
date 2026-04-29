"""Day 1: LLMClient + CLIClient 단위 테스트."""

from unittest.mock import MagicMock, patch

import pytest

from core.llm.cli_client import CLIClient, _load_registry
from core.llm.client import LLMError, LLMResponse, Prompt


class TestPrompt:
    def test_to_text_includes_both_sections(self) -> None:
        p = Prompt(system="hello", user="world")
        text = p.to_text()
        assert "hello" in text
        assert "world" in text
        assert "[SYSTEM]" in text
        assert "[USER]" in text


class TestLLMResponse:
    def test_default_raw(self) -> None:
        r = LLMResponse(
            text="hi",
            model="test",
            cost_usd=0.0,
            latency_ms=100,
            input_tokens=0,
            output_tokens=0,
        )
        assert r.raw == {}

    def test_custom_raw(self) -> None:
        r = LLMResponse(
            text="hi",
            model="test",
            cost_usd=0.0,
            latency_ms=100,
            input_tokens=0,
            output_tokens=0,
            raw={"stdout": "abc"},
        )
        assert r.raw["stdout"] == "abc"


# Mock registry for testing (avoids real CLI calls)
MOCK_REGISTRY: dict = {
    "models": {
        "test_cli": {
            "type": "cli",
            "command": "echo",
            "args": ["{prompt_text}"],
            "model_id": "test-echo",
            "family": "test",
        },
        "not_cli": {
            "type": "api",
            "command": "n/a",
            "args": [],
            "model_id": "fake-api",
            "family": "test",
        },
    }
}


class TestCLIClient:
    def test_init_with_explicit_registry(self) -> None:
        client = CLIClient(model_key="test_cli", registry=MOCK_REGISTRY)
        assert client.model_name == "test-echo"
        assert client.family == "test"

    def test_init_unknown_model(self) -> None:
        with pytest.raises(LLMError, match="not found in registry"):
            CLIClient(model_key="does_not_exist", registry=MOCK_REGISTRY)

    def test_init_non_cli_type(self) -> None:
        with pytest.raises(LLMError, match="not a CLI model"):
            CLIClient(model_key="not_cli", registry=MOCK_REGISTRY)

    def test_generate_with_echo(self) -> None:
        """echo 명령어로 실제 subprocess 호출 (mock 없이)."""
        client = CLIClient(model_key="test_cli", registry=MOCK_REGISTRY)
        prompt = Prompt(system="sys", user="hello world")
        response = client.generate(prompt)

        assert response.model == "test-echo"
        assert response.cost_usd == 0.0
        assert response.latency_ms >= 0
        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert "[SYSTEM]" in response.text
        assert "hello world" in response.text
        assert response.raw["returncode"] == 0

    @patch("core.llm.cli_client.subprocess.run")
    def test_generate_handles_failure(self, mock_run: MagicMock) -> None:
        """returncode != 0 시 LLMError."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error message"
        mock_run.return_value = mock_result

        client = CLIClient(model_key="test_cli", registry=MOCK_REGISTRY)
        with pytest.raises(LLMError, match="CLI failed"):
            client.generate(Prompt(system="s", user="u"))

    @patch("core.llm.cli_client.subprocess.run")
    def test_generate_handles_timeout(self, mock_run: MagicMock) -> None:
        """timeout 시 LLMError."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)

        client = CLIClient(model_key="test_cli", registry=MOCK_REGISTRY, timeout_seconds=5)
        with pytest.raises(LLMError, match="timeout"):
            client.generate(Prompt(system="s", user="u"))

    @patch("core.llm.cli_client.subprocess.run")
    def test_generate_handles_empty_response(self, mock_run: MagicMock) -> None:
        """stdout 비어있으면 LLMError."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        client = CLIClient(model_key="test_cli", registry=MOCK_REGISTRY)
        with pytest.raises(LLMError, match="Empty response"):
            client.generate(Prompt(system="s", user="u"))

    @patch("core.llm.cli_client.subprocess.run")
    def test_generate_cost_is_zero(self, mock_run: MagicMock) -> None:
        """정액제 = cost_usd 0."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "responseText"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        client = CLIClient(model_key="test_cli", registry=MOCK_REGISTRY)
        response = client.generate(Prompt(system="s", user="u"))

        assert response.cost_usd == 0.0
        assert response.text == "responseText"


def test_real_registry_loads() -> None:
    """실제 config/llm_registry.yaml 로드 가능."""
    registry = _load_registry()
    assert "claude_code" in registry["models"]
    assert "codex" in registry["models"]
    assert "gemini" in registry["models"]
    assert all(
        registry["models"][k]["type"] == "cli"
        for k in ["claude_code", "codex", "gemini"]
    )
