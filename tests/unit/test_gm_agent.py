"""W2 D4 작업 5 + Tier 1.5 D4: GM Agent 테스트."""

from typing import Any
from unittest.mock import MagicMock

import pytest

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

    def test_mock_gm_returns_score(self) -> None:
        """MockGMAgent도 total_score / verify_passed 반환."""
        plan, state = _make_plan_state()
        agent = MockGMAgent()
        r = agent.generate_response(plan, state, "x")
        assert r.total_score == 100.0
        assert r.verify_passed is True

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


class TestGMAgentD4:
    """★ Tier 1.5 D4 신규 테스트."""

    def test_cross_model_violation_raises(self) -> None:
        """같은 model_name → ValueError."""
        game_llm = _MockLLM(response_text="응답")
        verify_llm = _MockLLM(response_text="검증")  # 같은 model_name="mock"

        with pytest.raises(ValueError, match="Cross-Model violation"):
            GMAgent(game_llm, verify_llm=verify_llm)

    def test_cross_model_different_models_ok(self) -> None:
        """다른 model_name → 정상."""
        class VerifyLLM:
            @property
            def model_name(self) -> str:
                return "different_model"
            def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
                return LLMResponse(
                    text="검증", model="different_model",
                    cost_usd=0.0, latency_ms=10,
                    input_tokens=10, output_tokens=10,
                )

        game_llm = _MockLLM()
        verify_llm = VerifyLLM()
        agent = GMAgent(game_llm, verify_llm=verify_llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "x")
        assert r.text != ""

    def test_response_has_total_score(self) -> None:
        """성공 응답 → total_score > 0."""
        llm = _MockLLM(response_text="당신은 던전에 들어왔습니다. 어두운 통로가 보입니다.")
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들어가기")
        assert r.total_score >= 0.0
        assert r.total_score <= 100.0

    def test_truncated_response_fails_mechanical(self) -> None:
        """잘린 응답 → mechanical_passed=False (TruncationDetectionRule)."""
        truncated = "당신의 뒤에는 조력자 셰"
        llm = _MockLLM(response_text=truncated)
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들어가기")
        assert not r.mechanical_passed
        assert any("truncat" in f.lower() or "korean_truncation" in f.lower()
                   for f in r.mechanical_failures)

    def test_verify_passed_on_good_response(self) -> None:
        """정상 응답 → verify_passed=True."""
        llm = _MockLLM(response_text="어두운 던전 안으로 들어갔습니다. 무엇을 하시겠습니까?")
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들어가기")
        assert r.verify_passed is True
