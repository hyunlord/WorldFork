"""PlayerAgent 단위 테스트 (★ 1차 commit, mock만)."""

from __future__ import annotations

from service.sim.player_agent import MockPlayerAgent, PlayerAgentResponse
from service.sim.types import PlayerAction, PlayerActionType


def test_mock_player_agent_default() -> None:
    """기본 mock action 반환."""
    agent = MockPlayerAgent()
    response = agent.generate_action("비요른", {})

    assert isinstance(response, PlayerAgentResponse)
    assert response.action.actor_name == "비요른"
    assert response.action.action_type == PlayerActionType.WAIT


def test_mock_player_agent_custom_actions() -> None:
    """custom mock actions 회전."""
    actions = [
        PlayerAction(
            action_type=PlayerActionType.ACTIVATE_LIGHT,
            actor_name="X",
            target="횃불",
        ),
        PlayerAction(
            action_type=PlayerActionType.MOVE,
            actor_name="X",
            target="북쪽 통로",
        ),
    ]
    agent = MockPlayerAgent(mock_actions=actions)

    r1 = agent.generate_action("비요른", {})
    assert r1.action.action_type == PlayerActionType.ACTIVATE_LIGHT

    r2 = agent.generate_action("비요른", {})
    assert r2.action.action_type == PlayerActionType.MOVE

    # 회전 — 3번째는 다시 첫 번째
    r3 = agent.generate_action("비요른", {})
    assert r3.action.action_type == PlayerActionType.ACTIVATE_LIGHT


def test_mock_player_agent_actor_name_mapping() -> None:
    """actor_name 진짜 매핑 — caller가 전달한 actor."""
    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="원본"),
    ]
    agent = MockPlayerAgent(mock_actions=actions)

    response = agent.generate_action("실제_actor", {})
    # 호출 시 actor_name이 실제 actor로 변경
    assert response.action.actor_name == "실제_actor"
