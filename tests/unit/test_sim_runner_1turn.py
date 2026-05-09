"""SimRunner 1턴 진짜 실행 테스트 (★ 2차 commit)."""

from __future__ import annotations

import pytest

from service.game.state_v2 import Character, Location, Race, Realm, WorldState
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerAction, PlayerActionType, SimConfig


def _make_party() -> dict[str, Character]:
    return {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            is_player=True,
        ),
        "에르웬": Character(
            name="에르웬", race=Race.FAERIE, hp=90, hp_max=90
        ),
    }


def _make_world() -> WorldState:
    return WorldState(
        current_round=1,
        hours_in_dungeon=0,
        is_dark_zone=True,
        party_members=["비요른", "에르웬"],
    )


def _make_location() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


def test_sim_runner_run_single_turn_wait() -> None:
    """WAIT action — advance_time 진짜 호출."""
    config = SimConfig()
    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="비요른")
    ]
    runner = SimRunner(
        config=config,
        player_agent=MockPlayerAgent(mock_actions=actions),
    )

    party = _make_party()
    world = _make_world()

    log = runner.run_single_turn(
        turn_number=1,
        actor_name="비요른",
        party=party,
        world=world,
        location=_make_location(),
    )

    assert log.turn_number == 1
    assert log.actor_name == "비요른"
    assert log.action.action_type == PlayerActionType.WAIT
    assert log.success
    # advance_time 진짜 호출 → world.hours_in_dungeon 증가
    assert world.hours_in_dungeon == 1
    assert log.hours_in_dungeon == 1


def test_sim_runner_run_single_turn_move_real_mutate() -> None:
    """MOVE action — 3차 commit이 진짜 mutate."""
    actions = [
        PlayerAction(
            action_type=PlayerActionType.MOVE,
            actor_name="비요른",
            target="북쪽 통로",
        )
    ]
    runner = SimRunner(
        config=SimConfig(),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )

    log = runner.run_single_turn(
        turn_number=1,
        actor_name="비요른",
        party=_make_party(),
        world=_make_world(),
        location=_make_location(),
    )

    assert log.action.action_type == PlayerActionType.MOVE
    assert log.success
    assert "북쪽 통로" in log.message


def test_sim_runner_run_invalid_actor() -> None:
    runner = SimRunner(config=SimConfig())

    with pytest.raises(ValueError, match="actor_name not in party"):
        runner.run_single_turn(
            turn_number=1,
            actor_name="없는_actor",
            party=_make_party(),
            world=_make_world(),
            location=_make_location(),
        )


def test_sim_runner_run_with_party_and_world() -> None:
    """run() N턴 진짜 실행 (★ 3차 commit max_turns 도달)."""
    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="비요른")
    ]
    runner = SimRunner(
        config=SimConfig(max_turns=5),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )

    party = _make_party()
    world = _make_world()

    result = runner.run(party=party, world=world, location=_make_location())

    assert result.completed_turns == 5
    assert len(result.turn_logs) == 5
    assert result.end_reason == "max_turns"
    assert result.final_hp_by_actor["비요른"] == 150
    # ★ G commit: WAIT delta=2h × 5 turn = 10h (★ A.5의 advance_time 1h overridden)
    assert result.final_hours_in_dungeon == 10


def test_sim_runner_run_no_party_returns_empty() -> None:
    """party None — 빈 결과."""
    runner = SimRunner(config=SimConfig())
    result = runner.run()

    assert result.completed_turns == 0
    assert "no_party_or_world_or_location" in result.end_reason


def test_sim_runner_run_empty_party() -> None:
    """빈 party."""
    runner = SimRunner(config=SimConfig())
    result = runner.run(
        party={}, world=_make_world(), location=_make_location()
    )

    assert result.completed_turns == 0
    assert "empty_party" in result.end_reason
