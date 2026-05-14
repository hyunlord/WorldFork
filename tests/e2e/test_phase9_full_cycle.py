"""Phase 9 sim-cycle e2e — 1층 → 마을 → 1층 재진입 full cycle 검증.

검증 본질:
- _check_end_condition: PARTY_DEFEATED만 종료 (★ Phase 9 sim-cycle)
- TIME_LIMIT_REACHED → 마을 mutation → sim loop 계속 (★ 종료 X)
- 스크립트: 1층 168h → 마을 WAIT_IN_VILLAGE × 30 → 매월 1일 ENTER_DUNGEON
- 본인 답 정합:
  * 마석/inventory 보존 (★ village 본격 영구)
  * HP 회복 (★ 30일 마을)
  * 전멸 = 게임 오버 (★ PARTY_DEFEATED 본격 종료)
- 본문 정합: 19화 매월 1일 자정, 30일
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Item,
    ItemCategory,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import SimRunner, _check_end_condition
from service.sim.types import (
    PlayerAction,
    PlayerActionType,
    SimConfig,
)


def _strong_actor() -> Character:
    return Character(
        name="투르윈",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        physical=14,
        strength=16,
        bone_strength=12,
        is_player=True,
    )


def _floor1_entry() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


# ─── 1. _check_end_condition 본격 ───


def _make_config() -> SimConfig:
    return SimConfig(max_turns=1)


def test_check_end_active_continues() -> None:
    world = WorldState()
    world.simulation_status = SimulationStatus.ACTIVE
    assert _check_end_condition(_make_config(), {}, world, 0) is None


def test_check_end_time_limit_continues_phase9() -> None:
    """본 commit 변경: TIME_LIMIT_REACHED 본격 종료 X (★ 마을 turn loop)."""
    world = WorldState()
    world.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    assert _check_end_condition(_make_config(), {}, world, 0) is None


def test_check_end_party_defeated_ends() -> None:
    world = WorldState()
    world.simulation_status = SimulationStatus.PARTY_DEFEATED
    assert _check_end_condition(_make_config(), {}, world, 0) == "party_defeated"


def test_check_end_max_turns() -> None:
    world = WorldState()
    config = SimConfig(max_turns=10)
    assert _check_end_condition(config, {}, world, 10) == "max_turns"


# ─── 2. 168h 도달 후 sim 계속 본격 ───


def test_sim_continues_past_168h() -> None:
    """200턴 WAIT → 168h 도달 후 sim 종료 X, max_turns 까지 진행."""
    party = {"투르윈": _strong_actor()}
    world = WorldState(party_members=["투르윈"])
    loc = _floor1_entry()

    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="투르윈"),
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
    result = runner.run(party=party, world=world, location=loc)

    # 본 commit: TIME_LIMIT_REACHED 본격 sim 종료 X → max_turns 본격 진행
    assert result.end_reason == "max_turns"
    assert result.completed_turns == 200
    assert world.simulation_status == SimulationStatus.TIME_LIMIT_REACHED
    # 마을 mutation 자동 발현 (★ Phase 8 a-3)
    assert loc.realm == Realm.CITY
    assert loc.floor == 0


def test_sim_party_defeated_status_ends_loop() -> None:
    """world.simulation_status = PARTY_DEFEATED 본격 _check_end_condition 종료.

    본 test 본격 unit-level _check_end_condition 본격 본격 정합
    (★ check_party_defeated 본격 transition 본격 turn_handler test 본격).
    """
    world = WorldState()
    world.simulation_status = SimulationStatus.PARTY_DEFEATED
    reason = _check_end_condition(SimConfig(max_turns=200), {}, world, 5)
    assert reason == "party_defeated"


# ─── 3. 본인 답 보존 검증 (★ scripted) ───


def test_inventory_preserved_across_time_limit() -> None:
    """마석 본격 inventory 본격 168h 도달 본격 본격 보존."""
    actor = _strong_actor()
    actor.inventory.items.append(
        Item(
            name="9등급 마석",
            category=ItemCategory.MATERIAL,
            weight=1,
            grade=9,
        )
    )
    party = {"투르윈": actor}
    world = WorldState(party_members=["투르윈"])
    loc = _floor1_entry()

    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="투르윈"),
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
    runner.run(party=party, world=world, location=loc)

    # 마석 보존 (★ 168h 도달 본격 inventory mutate X)
    stones = [
        it for it in actor.inventory.items if it.grade == 9
    ]
    assert len(stones) == 1
    assert stones[0].name == "9등급 마석"


# ─── 4. 마을 turn handler 직접 호출 본격 e2e cycle ───


def test_village_cycle_30_days_advances_month() -> None:
    """마을 도착 → WAIT_IN_VILLAGE × 30 → month++.

    본 test 본격 turn_handler 본격 직접 호출 (★ sim_runner LLM 의존 X).
    Phase 9 mechanism 본격 month wrap 검증.
    """
    from service.game.turn_handler_v2 import execute_wait_in_village

    actor = _strong_actor()
    actor.hp = 50  # ★ 회복 검증 본격
    world = WorldState(party_members=["투르윈"])
    world.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    world.month_number = 1
    world.day_in_month = 1

    for _ in range(30):
        result = execute_wait_in_village("투르윈", [actor], world)
        assert result.success is True

    # 30일 후 → month=2, day=1 (★ wrap)
    assert world.month_number == 2
    assert world.day_in_month == 1
    # HP 회복 (★ +10 × 30 = +300, cap 150)
    assert actor.hp == 150


def test_full_cycle_dungeon_village_reentry() -> None:
    """1층 → 마을 mutation → WAIT 30 → ENTER_DUNGEON → 1층 ACTIVE 재진입.

    Phase 9 sim-cycle 본격 본격 e2e (★ scripted turn_handler 본격 정합).
    """
    from service.game.turn_handler_v2 import (
        apply_time_limit_village_return,
        check_time_limit,
        execute_enter_dungeon,
        execute_wait_in_village,
    )

    actor = _strong_actor()
    actor.inventory.items.append(
        Item(
            name="8등급 마석",
            category=ItemCategory.MATERIAL,
            weight=1,
            grade=8,
        )
    )
    actor.stone = 500
    world = WorldState(party_members=["투르윈"])
    loc = _floor1_entry()

    # 1) 168h 도달 시뮬
    world.hours_in_dungeon = 168
    triggered = check_time_limit(world, time_limit_hours=168, turn_number=100)
    assert triggered is True
    assert world.simulation_status == SimulationStatus.TIME_LIMIT_REACHED

    # 2) 마을 mutation
    apply_time_limit_village_return(loc)
    assert loc.realm == Realm.CITY
    assert loc.floor == 0

    # 3) 마을 turn loop × 30 (★ HP 회복 + day wrap)
    actor.hp = 50
    for _ in range(30):
        execute_wait_in_village("투르윈", [actor], world)
    assert world.month_number == 2
    assert world.day_in_month == 1
    assert actor.hp == 150

    # 4) ENTER_DUNGEON → 1층 ACTIVE 재진입
    result = execute_enter_dungeon("투르윈", [actor], world, loc)
    assert result.success is True
    assert world.simulation_status == SimulationStatus.ACTIVE
    assert world.hours_in_dungeon == 0
    assert loc.realm == Realm.DUNGEON
    assert loc.floor == 1
    assert loc.sub_area == "진입점"

    # 5) 본인 답: inventory / stone 보존
    stones = [
        it for it in actor.inventory.items if it.grade == 8
    ]
    assert len(stones) == 1
    assert actor.stone == 500
