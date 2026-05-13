"""Phase 8 C / R3+R4 E2E — generic 인접 층 진입 + 최초 진입 보너스 scripted trace.

검증 본질 (★ LLM 무관 결정적):
- SimRunner 본격 ENTER_NEXT_FLOOR action 본격 실행 → status FLOOR_TRANSITION
- 본 sim 본격 최초 진입 → 전 alive 멤버 +500 exp + level up marker
- 전체 cycle: ENTER_NEXT_FLOOR → EXIT_TO_PREV_FLOOR 왕복
- trace snapshot 본격 floor_states dict + first_entry_parties 노출
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
    level_for_exp,
)
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerAction, PlayerActionType, SimConfig


def _party() -> dict[str, Character]:
    return {
        "투르윈": Character(
            name="투르윈",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            is_player=True,
        ),
        "셰인": Character(
            name="셰인",
            race=Race.HUMAN,
            hp=120,
            hp_max=120,
        ),
    }


def _loc(sub_area: str = "비석 공동") -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area=sub_area)


# ─── 1. SimRunner 본격 ENTER_NEXT_FLOOR ───


def test_scripted_enter_next_floor_marks_state_no_terminate() -> None:
    """portal sub_area 본격 ENTER_NEXT_FLOOR → sim 본격 종료 X (★ 왕복 본격).

    FLOOR_TRANSITION = 위치 marker (★ 1층 vs 2층). EXIT_TO_PREV_FLOOR 본격
    복귀 가능. 본인 답: "2층 ↔ 1층 왕복 가능".
    """
    party = _party()
    world = WorldState(party_members=list(party.keys()))
    loc = _loc("동쪽 포탈 통로")

    actions = [
        PlayerAction(
            action_type=PlayerActionType.ENTER_NEXT_FLOOR,
            actor_name="투르윈",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=3,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=loc)

    # ENTER_NEXT_FLOOR 본격 sim 종료 X → max_turns 도달 (★ 3턴 본격 진행)
    assert result.end_reason == "max_turns"
    assert world.simulation_status == SimulationStatus.FLOOR_TRANSITION
    assert 2 in world.floor_states
    assert world.floor_states[2].entered is True
    assert (
        world.floor_states[2].entry_sub_area_from_prev == "동쪽 포탈 통로"
    )
    assert loc.floor == 2
    assert loc.sub_area == "도착 지점"
    # 첫 turn ENTER_NEXT_FLOOR 본격, 2/3턴은 본격 재진입 시도 본격 fail 본격
    # (★ 이미 status=FLOOR_TRANSITION → enter_next_floor ACTIVE check 본격 fail)
    assert len(result.turn_logs) == 3


def test_scripted_first_party_bonus_applied() -> None:
    """본 sim 최초 진입 본격 전원 +500 exp + level 4 (★ B enabler 활용)."""
    party = _party()
    world = WorldState(party_members=list(party.keys()))
    loc = _loc("북쪽 포탈 통로")

    actions = [
        PlayerAction(
            action_type=PlayerActionType.ENTER_NEXT_FLOOR,
            actor_name="투르윈",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=1,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=loc)

    # ENTER_NEXT_FLOOR 본격 sim 종료 X — max_turns 본격 도달 (★ 1턴 본격 진행)
    assert result.end_reason == "max_turns"
    assert world.simulation_status == SimulationStatus.FLOOR_TRANSITION
    assert 2 in world.first_entry_parties
    for m in party.values():
        assert m.experience == 500
        assert m.level == 4 == level_for_exp(500)
    # side effect markers 본격 turn log
    only_log = result.turn_logs[0]
    assert any("exp_gained=" in e for e in only_log.side_effects)
    assert any("level_up=" in e for e in only_log.side_effects)
    assert "first_floor_party=2" in only_log.side_effects


def test_scripted_round_trip_floor_one_two_one_two() -> None:
    """왕복 본격 (★ 본인 답): 1층 portal → 2층 → 1층 → 2층, 보너스 1회만.

    turn 1: ENTER_NEXT_FLOOR (★ 1층 → 2층, 첫 진입 보너스 +500 exp)
    turn 2: EXIT_TO_PREV_FLOOR (★ 2층 → 1층, entry_sub_area 복귀, status ACTIVE)
    turn 3: ENTER_NEXT_FLOOR (★ 1층 → 2층 재진입, 보너스 X)
    turn 4: EXIT_TO_PREV_FLOOR (★ 2층 → 1층 본격)
    """
    party = _party()
    world = WorldState(party_members=list(party.keys()))
    loc = _loc("서쪽 포탈 통로")

    actions = [
        PlayerAction(
            action_type=PlayerActionType.ENTER_NEXT_FLOOR, actor_name="X",
        ),
        PlayerAction(
            action_type=PlayerActionType.EXIT_TO_PREV_FLOOR, actor_name="X",
        ),
        PlayerAction(
            action_type=PlayerActionType.ENTER_NEXT_FLOOR, actor_name="X",
        ),
        PlayerAction(
            action_type=PlayerActionType.EXIT_TO_PREV_FLOOR, actor_name="X",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=4,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=loc)

    assert result.end_reason == "max_turns"
    assert len(result.turn_logs) == 4

    # 최종 state: 2층 → 1층 복귀 후 → 2층 재진입 → 다시 1층
    assert loc.floor == 1
    assert loc.sub_area == "서쪽 포탈 통로"  # ★ 진입 sub_area 복귀
    assert world.simulation_status == SimulationStatus.ACTIVE
    assert world.floor_states[2].entered is True  # 본격 진입 한적 있음
    assert world.floor_states[2].returned_to_prev is True

    # 보너스 1회만 (★ 본인 답 "한달마다 1회")
    assert 2 in world.first_entry_parties
    for m in party.values():
        assert m.experience == 500  # ★ 본격 1회 보너스만 누적

    # turn 1: 보너스 marker
    assert any(
        "first_floor_party=2" in s
        for s in result.turn_logs[0].side_effects
    )
    # turn 3 (재진입): 보너스 marker X
    assert not any(
        "first_floor_party=2" in s
        for s in result.turn_logs[2].side_effects
    )


def test_scripted_enter_at_non_portal_does_not_terminate() -> None:
    """portal 본격 X 위치에서 ENTER_NEXT_FLOOR → 실패 + sim 계속."""
    party = _party()
    world = WorldState(party_members=list(party.keys()))
    loc = _loc("진입점")  # ★ portal 본격 X

    actions = [
        PlayerAction(
            action_type=PlayerActionType.ENTER_NEXT_FLOOR,
            actor_name="투르윈",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=3,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=loc)

    # 3턴 모두 실패 → max_turns 도달
    assert result.end_reason == "max_turns"
    assert world.simulation_status == SimulationStatus.ACTIVE
    assert 2 not in world.floor_states
    # 보너스 발현 X
    assert 2 not in world.first_entry_parties
    for m in party.values():
        assert m.experience == 0


# ─── 2. trace snapshot 본격 floor_states + first_entry_parties ───


def test_scripted_trace_world_snapshot_floor_states() -> None:
    """trace world_snapshot 본격 floor_states dict + first_entry_parties 본격 출력."""
    party = _party()
    world = WorldState(party_members=list(party.keys()))
    loc = _loc("서쪽 포탈 통로")

    actions = [
        PlayerAction(
            action_type=PlayerActionType.ENTER_NEXT_FLOOR,
            actor_name="투르윈",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=10,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=loc)

    # 모든 turn snapshot 본격 floor_states + first_entry_parties key 존재
    for log in result.turn_logs:
        snap = log.world_snapshot
        assert "floor_states" in snap
        assert "first_entry_parties" in snap

    # snapshot은 action mutate 후 캡처 — 2층 floor_state 본격 entered=True
    # (★ sim_runner.run_single_turn 본격 action 실행 후 _action_to_turn_log 호출).
    first_snap = result.turn_logs[0].world_snapshot
    assert "2" in first_snap["floor_states"]
    assert first_snap["floor_states"]["2"]["entered"] is True
    assert (
        first_snap["floor_states"]["2"]["entry_sub_area_from_prev"]
        == "서쪽 포탈 통로"
    )
    assert first_snap["first_entry_parties"] == [2]
    # 종료 후 state 본격 일치
    assert world.floor_states[2].entered is True
