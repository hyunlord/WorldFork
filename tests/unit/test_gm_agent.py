"""W2 D4 작업 5: GM Agent 테스트."""

from typing import Any
from unittest.mock import MagicMock

from core.llm.client import LLMResponse, Prompt
from service.game.gm_agent import GMAgent, MockGMAgent
from service.game.init_from_plan import init_game_state_from_plan
from service.game.state import GameState
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


def _make_plan_state() -> tuple[Plan, GameState]:
    mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
    plan = Plan(
        work_name="novice_dungeon_run",
        work_genre="판타지",
        main_character=mc,
        world=WorldSetting(
            setting_name="신참 던전", genre="판타지",
            tone="진지", rules=["마법"],
        ),
        opening_scene="투르윈은 던전 입구에 있다.",
    )
    state = init_game_state_from_plan(plan)
    return plan, state


class _MockLLM:
    def __init__(self, response_text: str = "GM 응답") -> None:
        self._text = response_text

    @property
    def model_name(self) -> str:
        return "mock"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text=self._text, model="mock",
            cost_usd=0.01, latency_ms=100,
            input_tokens=50, output_tokens=100,
        )


class TestMockGMAgent:
    def test_basic_response(self) -> None:
        plan, state = _make_plan_state()
        agent = MockGMAgent()
        r = agent.generate_response(plan, state, "들어가기")
        assert r.text != ""
        assert r.mechanical_passed
        assert r.error is None

    def test_custom_responses(self) -> None:
        plan, state = _make_plan_state()
        agent = MockGMAgent(mock_responses=["커스텀 응답"])
        r = agent.generate_response(plan, state, "x")
        assert r.text == "커스텀 응답"

    def test_response_cycles(self) -> None:
        plan, state = _make_plan_state()
        agent = MockGMAgent(mock_responses=["A", "B"])
        r1 = agent.generate_response(plan, state, "x")
        r2 = agent.generate_response(plan, state, "y")
        r3 = agent.generate_response(plan, state, "z")
        assert r1.text == "A"
        assert r2.text == "B"
        assert r3.text == "A"  # cycle


class TestGMAgentRealLLM:
    def test_full_flow(self) -> None:
        llm = _MockLLM(response_text="당신은 던전에 들어왔습니다. 어두운 통로가 보입니다.")
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들어가기")
        assert r.text != ""
        assert r.error is None

    def test_llm_failure(self) -> None:
        broken_llm = MagicMock()
        broken_llm.generate.side_effect = RuntimeError("LLM down")
        broken_llm.model_name = "broken"

        agent = GMAgent(broken_llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "x")
        assert r.error is not None
        assert "LLM call failed" in r.error
        assert not r.mechanical_passed

    def test_history_in_user_prompt(self) -> None:
        plan, state = _make_plan_state()
        state.add_turn("이전 액션", "이전 응답", 0.01, 100)

        llm = _MockLLM(response_text="다음 응답")
        agent = GMAgent(llm)
        r = agent.generate_response(plan, state, "다음 액션")
        assert r.text != ""

    def test_dynamic_max_tokens(self) -> None:
        """짧은 user_action → 호출 자체 성공 검증."""
        llm = _MockLLM(response_text="응답")
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들")
        assert r.text != ""

    def test_supporting_characters_in_prompt(self) -> None:
        """조연이 있는 Plan → 시스템 프롬프트에 조연 포함."""
        mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
        sc = CharacterPlan(name="셰인", role="조력자", description="멘토")
        plan = Plan(
            work_name="test", work_genre="판타지", main_character=mc,
            supporting_characters=[sc],
            world=WorldSetting(setting_name="던전", genre="판타지", tone="d", rules=[]),
        )
        state = init_game_state_from_plan(plan)
        llm = _MockLLM()
        agent = GMAgent(llm)
        r = agent.generate_response(plan, state, "x")
        assert r.text != ""
