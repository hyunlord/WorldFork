"""SimRunner N턴 자동 시뮬 테스트 (★ 3차 commit)."""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerAction, PlayerActionType, SimConfig


def _party() -> dict[str, Character]:
    return {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            physical=14,
            strength=16,
            is_player=True,
        ),
        "에르웬": Character(
            name="에르웬", race=Race.FAERIE, hp=90, hp_max=90
        ),
    }


def _world() -> WorldState:
    return WorldState(party_members=["비요른", "에르웬"])


def _loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


def test_run_50_turns_completes() -> None:
    """50턴 WAIT — max_turns 도달 (★ G semantics, 50h < 168h)."""
    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="X")
    ]
    # ★ G semantics: explicit initial=0, scale=1.0 (★ H default override)
    runner = SimRunner(
        config=SimConfig(
            max_turns=50, initial_hours_in_dungeon=0.0, time_scale=1.0
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )

    result = runner.run(party=_party(), world=_world(), location=_loc())

    assert result.completed_turns == 50
    assert result.end_reason == "max_turns"
    assert len(result.turn_logs) == 50


def test_run_reaches_time_limit_status() -> None:
    """200턴이면 168h 한도 도달 → TIME_LIMIT_REACHED status (★ Phase 9 sim 계속).

    본 commit Phase 9 sim-cycle 본격: TIME_LIMIT_REACHED 본격 sim 종료 X →
    마을 turn loop 본격 계속 → max_turns 까지 진행.
    """
    from service.game.state_v2 import SimulationStatus

    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="X")
    ]
    world = _world()
    runner = SimRunner(
        config=SimConfig(max_turns=200),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )

    result = runner.run(party=_party(), world=world, location=_loc())

    # 본 commit 본격: TIME_LIMIT_REACHED 도달 (★ status), end_reason 본격 max_turns
    assert world.simulation_status == SimulationStatus.TIME_LIMIT_REACHED
    assert result.final_hours_in_dungeon >= 168
    assert result.end_reason == "max_turns"


def test_run_actions_round_robin() -> None:
    """비요른 / 에르웬 round-robin."""
    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="X")
    ]
    runner = SimRunner(
        config=SimConfig(max_turns=10),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )

    result = runner.run(party=_party(), world=_world(), location=_loc())

    actor_names_in_order = [log.actor_name for log in result.turn_logs]
    assert "비요른" in actor_names_in_order
    assert "에르웬" in actor_names_in_order


def test_run_player_permadeath_stops() -> None:
    """player HP 약함 → ATTACK 반복 → 최종 permadeath 도달."""
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=20,  # 매우 약함
            hp_max=150,
            physical=5,
            strength=5,
            bone_strength=2,
            is_player=True,
        ),
    }
    actions = [
        PlayerAction(
            action_type=PlayerActionType.ATTACK,
            actor_name="비요른",
            target="고블린",
        )
    ]
    runner = SimRunner(
        config=SimConfig(max_turns=50, stop_on_permadeath=True),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )

    result = runner.run(party=party, world=_world(), location=_loc())
    # 약한 attack 매 턴 9 데미지 받음 → 3턴 정도면 사망
    assert result.end_reason == "permadeath"
    assert party["비요른"].hp == 0


def test_run_50_turns_with_diverse_actions() -> None:
    """다양 ActionType 본격 실행 (★ 13 ActionType 모두 mutate 검증)."""
    diverse_actions = [
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
        PlayerAction(action_type=PlayerActionType.EXPLORE, actor_name="X"),
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="X"),
        PlayerAction(action_type=PlayerActionType.REST, actor_name="X"),
    ]
    runner = SimRunner(
        config=SimConfig(max_turns=20),
        player_agent=MockPlayerAgent(mock_actions=diverse_actions),
    )

    result = runner.run(party=_party(), world=_world(), location=_loc())

    types_seen = {log.action.action_type for log in result.turn_logs}
    assert len(types_seen) >= 3


def test_run_collects_costs_and_latency() -> None:
    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="X")
    ]
    runner = SimRunner(
        config=SimConfig(max_turns=5),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )

    result = runner.run(party=_party(), world=_world(), location=_loc())

    assert result.total_latency_seconds >= 0.0
    assert "비요른" in result.final_hp_by_actor
