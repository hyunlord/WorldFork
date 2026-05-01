"""Tier 1 W1 D3: PlaytesterRunner 단위 테스트 (Mock 기반)."""

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


VALID_JSON_RESPONSE = """
```json
{
  "completed": true,
  "n_turns_played": 30,
  "fun_rating": 3,
  "would_replay": true,
  "abandoned": false,
  "abandon_reason": null,
  "abandon_turn": null,
  "findings": [
    {
      "severity": "minor",
      "category": "verbose",
      "turn_n": 5,
      "description": "응답이 좀 길었음"
    }
  ],
  "summary": "재미있는 세션이었음"
}
```
"""

ABANDONED_JSON_RESPONSE = """
```json
{
  "completed": false,
  "n_turns_played": 3,
  "fun_rating": 1,
  "would_replay": false,
  "abandoned": true,
  "abandon_reason": "너무 지루함",
  "abandon_turn": 3,
  "findings": [],
  "summary": "이탈"
}
```
"""


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


class TestPlaytesterRunSession:
    def test_session_with_valid_json(self) -> None:
        persona = load_persona("casual_korean_player", tier="tier_0")
        game = MockLLM("qwen35-9b-q3", "게임 시작 응답")
        playtester = MockLLM("claude_code", VALID_JSON_RESPONSE)

        runner = PlaytesterRunner(
            persona=persona, game_client=game, playtester_client=playtester
        )
        result = runner.run_session(work_name="test_work", max_turns=30)

        assert result.persona_id == "casual_korean_player"
        assert result.work_name == "test_work"
        assert result.completed is True
        assert result.n_turns_played == 30
        assert result.fun_rating == 3
        assert result.would_replay is True
        assert result.abandoned is False
        assert len(result.findings) == 1
        assert result.findings[0].severity == "minor"
        assert result.findings[0].category == "verbose"

    def test_session_abandoned(self) -> None:
        persona = load_persona("casual_korean_player", tier="tier_0")
        game = MockLLM("qwen35-9b-q3", "게임 시작")
        playtester = MockLLM("claude_code", ABANDONED_JSON_RESPONSE)

        runner = PlaytesterRunner(
            persona=persona, game_client=game, playtester_client=playtester
        )
        result = runner.run_session(work_name="test", max_turns=30)

        assert result.abandoned is True
        assert result.n_turns_played == 3
        assert result.abandon_reason == "너무 지루함"
        assert result.abandon_turn == 3

    def test_session_with_invalid_json_returns_abandoned(self) -> None:
        persona = load_persona("casual_korean_player", tier="tier_0")
        game = MockLLM("qwen35-9b-q3", "게임 시작")
        playtester = MockLLM("claude_code", "JSON 없는 응답입니다")

        runner = PlaytesterRunner(
            persona=persona, game_client=game, playtester_client=playtester
        )
        result = runner.run_session(work_name="test", max_turns=30)

        assert result.abandoned is True
        assert result.abandon_reason is not None
        assert "JSON parse failed" in result.abandon_reason

    def test_game_llm_failure_returns_abandoned(self) -> None:
        class FailLLM(MockLLM):
            def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
                raise RuntimeError("connection refused")

        persona = load_persona("casual_korean_player", tier="tier_0")
        runner = PlaytesterRunner(
            persona=persona,
            game_client=FailLLM("qwen35-9b-q3"),
            playtester_client=MockLLM("claude_code"),
        )
        result = runner.run_session(work_name="test", max_turns=30)

        assert result.abandoned is True
        assert "Game LLM intro failed" in (result.abandon_reason or "")

    def test_playtester_llm_failure_returns_abandoned(self) -> None:
        class FailLLM(MockLLM):
            def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
                raise RuntimeError("timeout")

        persona = load_persona("casual_korean_player", tier="tier_0")
        runner = PlaytesterRunner(
            persona=persona,
            game_client=MockLLM("qwen35-9b-q3", "게임 시작"),
            playtester_client=FailLLM("claude_code"),
        )
        result = runner.run_session(work_name="test", max_turns=30)

        assert result.abandoned is True
        assert "Playtester CLI failed" in (result.abandon_reason or "")


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
