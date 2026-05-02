"""W2 D4 작업 6: Game Loop 테스트."""

from unittest.mock import MagicMock

from service.game.game_loop import GameLoop, classify_action
from service.game.gm_agent import GMResponse, MockGMAgent
from service.game.init_from_plan import init_game_state_from_plan
from service.game.state import GameState
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


def _make_plan_state() -> tuple[Plan, GameState]:
    mc = CharacterPlan(name="투르윈", role="주인공", description="d")
    plan = Plan(
        work_name="t", work_genre="g", main_character=mc,
        world=WorldSetting(setting_name="x", genre="y", tone="z", rules=[]),
    )
    state = init_game_state_from_plan(plan)
    return plan, state


class TestClassifyAction:
    def test_combat(self) -> None:
        assert classify_action("적을 공격한다") == "combat"
        assert classify_action("검을 휘둘러 베다") == "combat"

    def test_explore(self) -> None:
        assert classify_action("주변을 살피다") == "explore"
        assert classify_action("관찰한다") == "explore"

    def test_dialogue(self) -> None:
        assert classify_action("말을 건넨다") == "dialogue"
        assert classify_action("물어본다") == "dialogue"

    def test_movement(self) -> None:
        assert classify_action("들어가기") == "movement"

    def test_other(self) -> None:
        assert classify_action("이상한 행동") == "other"

    def test_empty(self) -> None:
        assert classify_action("") == "empty"


class TestGameLoopBasic:
    def test_simple_action(self) -> None:
        plan, state = _make_plan_state()
        gm = MockGMAgent()
        loop = GameLoop(gm)
        result = loop.process_action(plan, state, "들어가기")

        assert result.mechanical_passed
        assert result.attempts == 1
        assert result.game_state.turn == 1
        assert len(result.game_state.history) == 1


class TestGameLoopRetry:
    def test_retry_on_mechanical_fail(self) -> None:
        """첫 응답 fail → retry → 두 번째 통과."""
        plan, state = _make_plan_state()

        gm = MagicMock()
        gm.generate_response.side_effect = [
            GMResponse(
                text="fail", mechanical_passed=False,
                mechanical_failures=["test fail"],
            ),
            GMResponse(text="pass", mechanical_passed=True),
        ]

        loop = GameLoop(gm)
        result = loop.process_action(plan, state, "x")

        assert result.mechanical_passed
        assert result.attempts == 2
        assert result.response == "pass"

    def test_all_retries_fail_fallback(self) -> None:
        """모든 retry 실패 → fallback message."""
        plan, state = _make_plan_state()

        gm = MagicMock()
        gm.generate_response.return_value = GMResponse(
            text="fail",
            mechanical_passed=False,
            mechanical_failures=["always fail"],
        )

        loop = GameLoop(gm)
        result = loop.process_action(plan, state, "x")

        assert result.fallback_used
        assert not result.mechanical_passed
        assert "응답" in result.response or "오류" in result.response


class TestGameLoopErrors:
    def test_llm_error_triggers_retry(self) -> None:
        plan, state = _make_plan_state()

        gm = MagicMock()
        gm.generate_response.side_effect = [
            GMResponse(text="", error="LLM down", mechanical_passed=False),
            GMResponse(text="recovered", mechanical_passed=True),
        ]

        loop = GameLoop(gm)
        result = loop.process_action(plan, state, "x")

        assert result.mechanical_passed
        assert result.attempts == 2

    def test_state_updated_on_success(self) -> None:
        plan, state = _make_plan_state()
        gm = MockGMAgent(mock_responses=["성공 응답"])
        loop = GameLoop(gm)

        initial_turn = state.turn
        result = loop.process_action(plan, state, "들어가기")

        assert result.game_state.turn == initial_turn + 1
        assert result.game_state.history[-1].user_action == "들어가기"

    def test_multiple_actions_accumulate(self) -> None:
        """연속 행동 → state 누적."""
        plan, state = _make_plan_state()
        gm = MockGMAgent()
        loop = GameLoop(gm)

        loop.process_action(plan, state, "행동1")
        result2 = loop.process_action(plan, state, "행동2")

        assert result2.game_state.turn == 2
        assert len(result2.game_state.history) == 2

    def test_fallback_message_on_error(self) -> None:
        """LLM error → fallback에 적절한 메시지."""
        plan, state = _make_plan_state()

        gm = MagicMock()
        gm.generate_response.return_value = GMResponse(
            text="", error="LLM down", mechanical_passed=False,
        )

        loop = GameLoop(gm)
        result = loop.process_action(plan, state, "x")

        assert result.fallback_used
        assert "어려움" in result.response or "오류" in result.response
