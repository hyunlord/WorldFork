"""W1 D6: PlaytesterRunner turn loop 테스트 (Mock LLM)."""

from typing import Any

from core.llm.client import LLMClient, LLMResponse, Prompt
from tools.ai_playtester.persona import load_persona
from tools.ai_playtester.runner import PlaytesterRunner


class MockLLM(LLMClient):
    """순환 응답 Mock LLM."""

    def __init__(self, name: str, responses: list[str] | None = None):
        self._name = name
        self._responses = responses or ["default"]
        self._call_count = 0

    @property
    def model_name(self) -> str:
        return self._name

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return LLMResponse(
            text=text,
            model=self._name,
            cost_usd=0.0,
            latency_ms=100,
            input_tokens=20,
            output_tokens=50,
        )


# ===== Turn Loop =====


class TestTurnLoop:
    def test_full_session_30_turns(self) -> None:
        persona = load_persona("casual_korean_player", tier="tier_0")
        # Game LLM: intro + 30 응답
        game = MockLLM(
            "qwen35-9b-q3",
            responses=["게임 응답 " + str(i) for i in range(31)],
        )
        # Playtester: 30 ACTION + 1 summary
        playtester = MockLLM(
            "claude_code",
            responses=(
                ["ACTION: 다음으로 가자"] * 30
                + ['{"fun_rating": 3, "would_replay": true, "summary": "test"}']
            ),
        )

        runner = PlaytesterRunner(
            persona=persona, game_client=game, playtester_client=playtester,
        )
        result = runner.run_session("test_work", max_turns=30)

        assert result.completed
        assert result.n_turns_played == 30
        assert result.fun_rating == 3
        # ★ playthrough_log 풍부 (intro + 30 turns = 31)
        assert len(result.playthrough_log) == 31
        # turn 0 = intro
        assert result.playthrough_log[0]["role"] == "game_intro"
        assert result.playthrough_log[0]["turn_n"] == 0
        # turn 1+ = game_response
        assert result.playthrough_log[1]["role"] == "game_response"
        assert result.playthrough_log[1]["turn_n"] == 1
        # ★ user_input + game_response 모두 채워짐 (★ 자료 5.2)
        assert result.playthrough_log[1]["user_input"] != ""
        assert result.playthrough_log[1]["game_response"] != ""
        assert result.playthrough_log[1]["system_prompt"] != ""

    def test_finding_with_turn_context(self) -> None:
        persona = load_persona("casual_korean_player", tier="tier_0")
        game = MockLLM("qwen35-9b-q3", responses=["응답"] * 5)
        playtester = MockLLM(
            "claude_code",
            responses=[
                "FINDING: major verbose 너무 길음\nACTION: 다음",
                "ACTION: 다시",
                "ABANDON: 못 하겠음",
                '{"fun_rating": 1, "would_replay": false, "summary": "abandoned"}',
            ],
        )

        runner = PlaytesterRunner(
            persona=persona, game_client=game, playtester_client=playtester,
        )
        result = runner.run_session("test", max_turns=10)

        assert result.abandoned
        assert len(result.findings) == 1
        assert result.findings[0].severity == "major"
        # ★ turn_context 채워짐 (자료 5.2)
        assert result.findings[0].turn_context.get("system_prompt") != ""
        assert result.findings[0].turn_context.get("user_input") != ""

    def test_abandon_on_first_turn(self) -> None:
        persona = load_persona("casual_korean_player", tier="tier_0")
        game = MockLLM("qwen35-9b-q3")
        playtester = MockLLM(
            "claude_code",
            responses=[
                "ABANDON: 너무 verbose",
                '{"fun_rating": 1, "would_replay": false, "summary": "abandon"}',
            ],
        )

        runner = PlaytesterRunner(
            persona=persona, game_client=game, playtester_client=playtester,
        )
        result = runner.run_session("test", max_turns=10)

        assert result.abandoned
        assert result.n_turns_played == 0
        assert result.abandon_turn == 1


# ===== Parse Action =====


def _make_runner() -> PlaytesterRunner:
    persona = load_persona("casual_korean_player", tier="tier_0")
    return PlaytesterRunner(
        persona=persona,
        game_client=MockLLM("qwen35-9b-q3"),
        playtester_client=MockLLM("claude_code"),
    )


class TestParsePlaytesterAction:
    def test_parse_action_only(self) -> None:
        runner = _make_runner()
        action, finding, abandon = runner._parse_playtester_action(
            "ACTION: 던전 들어가기", 1,
        )
        assert action == "던전 들어가기"
        assert finding is None
        assert abandon is False

    def test_parse_finding_and_action(self) -> None:
        runner = _make_runner()
        action, finding, abandon = runner._parse_playtester_action(
            "FINDING: major verbose 너무 길음\nACTION: 다음으로",
            5,
        )
        assert finding is not None
        assert finding.severity == "major"
        assert finding.category == "verbose"
        assert finding.turn_n == 5
        assert action == "다음으로"

    def test_parse_abandon(self) -> None:
        runner = _make_runner()
        _, _, abandon = runner._parse_playtester_action("ABANDON: 못 하겠음", 1)
        assert abandon is True

    def test_parse_no_prefix_fallback(self) -> None:
        """ACTION/FINDING/ABANDON prefix 없으면 첫 줄을 action으로."""
        runner = _make_runner()
        action, finding, abandon = runner._parse_playtester_action(
            "검을 들고 앞으로", 1,
        )
        assert action == "검을 들고 앞으로"
        assert finding is None
        assert abandon is False

    def test_parse_finding_invalid_severity_defaults_minor(self) -> None:
        runner = _make_runner()
        _, finding, _ = runner._parse_playtester_action(
            "FINDING: weird category some description here", 2,
        )
        assert finding is not None
        assert finding.severity == "minor"
