"""Phase 8 A4 E2E — 1층 종료 조건 scripted trace.

검증 본질 (★ LLM 무관 결정적):
- 7일 (168h) 만료 → simulation_status TIME_LIMIT_REACHED + 마을 mutation
  * ★ Phase 9 sim-cycle: TIME_LIMIT_REACHED 본격 sim 종료 X
  * 마을 turn loop 본격 계속 (★ WAIT_IN_VILLAGE / ENTER_DUNGEON)
  * end_reason 본격 max_turns 까지 진행
- 전원 사망 (HP=0) → simulation_status PARTY_DEFEATED
  * 1인 파티 + is_player=True 면 permadeath가 먼저 발현 (★ 본격 backward compat)
  * 2인 파티 모두 die 시 PARTY_DEFEATED 본격 (★ 종료)
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerAction, PlayerActionType, SimConfig


def _loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


# ─── 1. 7일 만료 ───


def test_scripted_time_limit_reaches_168h() -> None:
    """WAIT 반복 → 168h 도달 → TIME_LIMIT_REACHED + 종료."""
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            physical=14,
            strength=16,
            is_player=True,
        ),
    }
    world = WorldState(party_members=["비요른"])

    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="비요른"),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=200,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,  # ★ permadeath 분기 차단 (★ A4 본격)
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=_loc())

    # ★ Phase 9 sim-cycle 본격 — TIME_LIMIT_REACHED 본격 sim 종료 X.
    # max_turns 까지 진행 + status / 본격 정합 본격.
    assert result.end_reason == "max_turns"
    assert world.simulation_status == SimulationStatus.TIME_LIMIT_REACHED
    assert world.simulation_over_reason is not None
    assert "168" in world.simulation_over_reason
    assert world.simulation_over_turn is not None
    assert result.final_hours_in_dungeon >= 168


def test_scripted_time_limit_trace_snapshot_has_status() -> None:
    """trace world_snapshot 본격 simulation_status 본격 출력 (★ 본격 source).

    snapshot 본격 turn 본격 start 시점이라 마지막 trace 본격 ACTIVE 가능
    (★ check_time_limit은 snapshot 이후 호출). 첫 턴 ACTIVE + 본격
    snapshot 본격 simulation_status 필드 존재만 본격 확정.
    """
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            is_player=True,
        ),
    }
    world = WorldState(party_members=["비요른"])
    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="비요른"),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=200,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=_loc())

    # 모든 turn snapshot 본격 simulation_status 필드 존재 (★ A4 trace 본격)
    for log in result.turn_logs:
        assert "simulation_status" in log.world_snapshot
        assert "simulation_over_reason" in log.world_snapshot
        assert "simulation_over_turn" in log.world_snapshot

    # 첫 턴 snapshot은 ACTIVE (★ 모든 turn 본격 ACTIVE — snapshot이 turn 시작 시점)
    first = result.turn_logs[0].world_snapshot
    assert first["simulation_status"] == "active"

    # 종료 후 state는 TIME_LIMIT_REACHED (★ check_time_limit 본격 호출됨)
    assert world.simulation_status == SimulationStatus.TIME_LIMIT_REACHED


# ─── 2. 전원 사망 ───


def test_scripted_party_defeated_all_dead() -> None:
    """2인 party 모두 HP=0 도달 시 PARTY_DEFEATED + 종료.

    ★ stop_on_permadeath=False로 permadeath 분기 차단 후 본 enum 분기 발현.
    """
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=10,  # 매우 약함
            hp_max=150,
            physical=5,
            strength=5,
            bone_strength=2,
            is_player=True,
        ),
        "에르웬": Character(
            name="에르웬",
            race=Race.FAERIE,
            hp=10,
            hp_max=90,
            physical=5,
            strength=5,
            bone_strength=2,
        ),
    }
    world = WorldState(party_members=["비요른", "에르웬"])

    # 약한 ATTACK은 처치 실패 → 받는 데미지로 본인 HP 감소
    actions = [
        PlayerAction(
            action_type=PlayerActionType.ATTACK,
            actor_name="X",
            target="고블린",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=50,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,  # ★ A4 enum 분기 검증
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=_loc())

    assert result.end_reason == "party_defeated", (
        f"expected party_defeated, got {result.end_reason}"
    )
    assert world.simulation_status == SimulationStatus.PARTY_DEFEATED
    # ★ Phase 8 (b) — 본문 톤 정합
    assert world.simulation_over_reason == "탐사대 전원이 미궁에서 쓰러졌다."
    assert world.simulation_over_turn is not None
    # 두 캐릭터 모두 HP=0
    assert party["투르윈"].hp == 0
    assert party["실렌"].hp == 0


def test_scripted_permadeath_still_first_priority() -> None:
    """기존 stop_on_permadeath 분기는 enum 분기 전 우선 (★ backward compat)."""
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=10,
            hp_max=150,
            physical=5,
            strength=5,
            bone_strength=2,
            is_player=True,
        ),
    }
    world = WorldState(party_members=["비요른"])
    actions = [
        PlayerAction(
            action_type=PlayerActionType.ATTACK,
            actor_name="비요른",
            target="고블린",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=50,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=True,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=_loc())

    # permadeath가 enum 분기보다 먼저
    assert result.end_reason == "permadeath"
    # state mutation은 발현 (★ check_party_defeated 호출됨)
    assert world.simulation_status == SimulationStatus.PARTY_DEFEATED


# ─── 3. ACTIVE 시 본격 X ───


def test_scripted_active_no_termination_in_short_run() -> None:
    """50턴 짧은 run — time_limit / party_defeated 본격 X → max_turns 도달."""
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            is_player=True,
        ),
    }
    world = WorldState(party_members=["비요른"])
    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="비요른"),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=50, initial_hours_in_dungeon=0.0, time_scale=1.0
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=_loc())

    assert result.end_reason == "max_turns"
    assert world.simulation_status == SimulationStatus.ACTIVE
    assert world.simulation_over_reason is None
    assert world.simulation_over_turn is None
