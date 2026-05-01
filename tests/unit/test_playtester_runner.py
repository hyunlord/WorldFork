"""Tier 1 W1 D3: PlaytesterRunner 단위 테스트 (Init/Persona).

★ W1 D6: run_session() 본격 turn loop는 test_runner_turnloop.py 로 분리.
이 파일은 init/compat/persona 검증만 유지.
"""

from typing import Any

import pytest

from core.llm.client import LLMClient, LLMResponse, Prompt
from tools.ai_playtester.persona import load_persona
from tools.ai_playtester.runner import (
    PlaytesterError,
    PlaytesterFinding,
    PlaytesterRunner,
)


class MockLLM(LLMClient):
    def __init__(self, name: str, response_text: str = "default") -> None:
        self._name = name
        self._response_text = response_text

    @property
    def model_name(self) -> str:
        return self._name

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text=self._response_text,
            model=self._name,
            cost_usd=0.0,
            latency_ms=100,
            input_tokens=20,
            output_tokens=50,
        )


class TestPlaytesterRunnerInit:
    def test_compatible_persona_ok(self) -> None:
        persona = load_persona("casual_korean_player", tier="tier_0")
        # casual의 forbidden = ['claude_code']. qwen은 OK.
        game = MockLLM("qwen35-9b-q3")
        playtester = MockLLM("claude_code")
        runner = PlaytesterRunner(
            persona=persona, game_client=game, playtester_client=playtester
        )
        assert runner.persona.id == "casual_korean_player"
        assert runner.game_client.model_name == "qwen35-9b-q3"

    def test_incompatible_game_llm_raises(self) -> None:
        persona = load_persona("casual_korean_player", tier="tier_0")
        # Game = claude_code = persona의 forbidden
        game = MockLLM("claude_code")
        playtester = MockLLM("codex")
        with pytest.raises(PlaytesterError, match="incompatible"):
            PlaytesterRunner(
                persona=persona, game_client=game, playtester_client=playtester
            )

    def test_tier1_persona_compatible(self) -> None:
        persona = load_persona("hardcore_lore_fan", tier="tier_1")
        # forbidden = ['codex']. qwen OK.
        game = MockLLM("qwen35-9b-q3")
        playtester = MockLLM("codex")
        runner = PlaytesterRunner(
            persona=persona, game_client=game, playtester_client=playtester
        )
        assert runner.persona.id == "hardcore_lore_fan"

    def test_tier1_persona_incompatible_raises(self) -> None:
        persona = load_persona("hardcore_lore_fan", tier="tier_1")
        # forbidden = ['codex']. codex as game = error.
        game = MockLLM("codex")
        playtester = MockLLM("claude_code")
        with pytest.raises(PlaytesterError, match="incompatible"):
            PlaytesterRunner(
                persona=persona, game_client=game, playtester_client=playtester
            )


class TestPlaytesterFinding:
    def test_fields(self) -> None:
        f = PlaytesterFinding(
            severity="critical",
            category="ip_leakage",
            turn_n=3,
            description="원작 캐릭터 이름 노출",
        )
        assert f.severity == "critical"
        assert f.reproduction_input == ""


class TestTier1Personas:
    def test_hardcore_lore_fan_loaded(self) -> None:
        p = load_persona("hardcore_lore_fan", tier="tier_1")
        assert p.cli_to_use == "codex"
        assert "codex" in p.forbidden_game_llms
        assert "원작" in p.demographic

    def test_speed_runner_loaded(self) -> None:
        p = load_persona("speed_runner", tier="tier_1")
        assert p.cli_to_use == "claude-code"
        assert p.behavior.patience == "low"
        assert "claude_code" in p.forbidden_game_llms

    def test_roleplayer_loaded(self) -> None:
        p = load_persona("roleplayer", tier="tier_1")
        assert p.cli_to_use == "codex"
        assert p.behavior.response_length == "long"
        assert "codex" in p.forbidden_game_llms
