"""Day 6: AI Playtester Persona 단위 테스트."""

import pytest

from tools.ai_playtester.persona import (
    is_compatible,
    list_personas,
    load_persona,
)


class TestPersona:
    def test_load_casual(self) -> None:
        p = load_persona("casual_korean_player")
        assert p.id == "casual_korean_player"
        assert p.cli_to_use == "claude-code"
        assert p.behavior.patience == "low"
        assert p.preferences.fun_factor == "high"

    def test_load_troll(self) -> None:
        p = load_persona("troll")
        assert p.id == "troll"
        assert p.cli_to_use == "codex"
        assert "AI 본능 누설" in p.expected_findings[0]

    def test_load_confused_beginner(self) -> None:
        p = load_persona("confused_beginner")
        assert p.cli_to_use == "gemini"
        assert p.behavior.exploration == "shallow"

    def test_load_unknown(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_persona("nonexistent")


class TestListPersonas:
    def test_tier_0(self) -> None:
        personas = list_personas("tier_0")
        assert "casual_korean_player" in personas
        assert "troll" in personas
        assert "confused_beginner" in personas

    def test_tier_unknown(self) -> None:
        personas = list_personas("tier_99")
        assert personas == []


class TestIsCompatible:
    def test_compatible(self) -> None:
        p = load_persona("casual_korean_player")
        assert not is_compatible(p, "claude_code")
        assert is_compatible(p, "codex")
        assert is_compatible(p, "gemini")

    def test_troll_compatibility(self) -> None:
        p = load_persona("troll")
        assert is_compatible(p, "claude_code")
        assert not is_compatible(p, "codex")
        assert is_compatible(p, "gemini")
