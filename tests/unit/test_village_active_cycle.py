"""Phase 9 — 마을 turn loop 본격 unit (★ 19화 본문 정합).

검증 본질:
- WorldState.month_number / day_in_month default
- DAYS_PER_MONTH = 30 (★ 19화 정합)
- HP_RECOVERY_PER_DAY / SP_RECOVERY_PER_DAY 본격
- execute_wait_in_village:
  * TIME_LIMIT_REACHED status 본격만 → success
  * day++ / 30 wrap → month++
  * HP/SP 회복 (★ 살아남은 멤버만)
  * 죽은 멤버 영구 (★ 본인 답)
- execute_enter_dungeon:
  * day=1 검증 (★ 19화)
  * 살아남은 멤버 검증
  * 1층 재진입 (★ 본인 답)
  * inventory / stone 보존
  * simulation 재시작

본 commit option 3 additive — SimulationStatus enum 변경 X (★ TIME_LIMIT_REACHED 유지).
sim_runner _check_end_condition 본격 종료 condition 유지 (★ 후속 commit cascade).
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
from service.game.turn_handler_v2 import (
    DAYS_PER_MONTH,
    HP_RECOVERY_PER_DAY,
    SP_RECOVERY_PER_DAY,
    execute_enter_dungeon,
    execute_wait_in_village,
)

# ─── 1. State / 상수 ───


def test_world_state_default_month_1_day_1() -> None:
    ws = WorldState()
    assert ws.month_number == 1
    assert ws.day_in_month == 1


def test_days_per_month_30_per_19hwa() -> None:
    """19화 본문: '한 달은 정확히 30일'."""
    assert DAYS_PER_MONTH == 30


def test_hp_recovery_per_day_10() -> None:
    assert HP_RECOVERY_PER_DAY == 10


def test_sp_recovery_per_day_5() -> None:
    assert SP_RECOVERY_PER_DAY == 5


# ─── 2. execute_wait_in_village ───


def _village_world() -> WorldState:
    w = WorldState()
    w.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    return w


def _bjorn(hp: int = 50, hp_max: int = 100, sp: int = 10, sp_max: int = 30) -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=hp,
        hp_max=hp_max,
        soul_power=sp,
        soul_power_max=sp_max,
    )


def test_wait_outside_village_fails() -> None:
    """ACTIVE status 본격 WAIT_IN_VILLAGE → fail."""
    world = WorldState()  # ACTIVE default
    actor = _bjorn()
    result = execute_wait_in_village("비요른", [actor], world)
    assert result.success is False


def test_wait_advances_day() -> None:
    world = _village_world()
    actor = _bjorn()
    pre_day = world.day_in_month
    result = execute_wait_in_village("비요른", [actor], world)
    assert result.success is True
    assert world.day_in_month == pre_day + 1


def test_wait_recovers_hp() -> None:
    world = _village_world()
    actor = _bjorn(hp=50, hp_max=100)
    execute_wait_in_village("비요른", [actor], world)
    assert actor.hp == 50 + HP_RECOVERY_PER_DAY


def test_wait_recovers_sp() -> None:
    world = _village_world()
    actor = _bjorn(sp=10, sp_max=30)
    execute_wait_in_village("비요른", [actor], world)
    assert actor.soul_power == 10 + SP_RECOVERY_PER_DAY


def test_wait_hp_caps_at_max() -> None:
    """hp 95 + 10 → 100 (★ hp_max cap)."""
    world = _village_world()
    actor = _bjorn(hp=95, hp_max=100)
    execute_wait_in_village("비요른", [actor], world)
    assert actor.hp == 100


def test_wait_sp_caps_at_max() -> None:
    world = _village_world()
    actor = _bjorn(sp=28, sp_max=30)
    execute_wait_in_village("비요른", [actor], world)
    assert actor.soul_power == 30


def test_wait_dead_member_no_recovery() -> None:
    """본인 답: 죽은 멤버 영구 (★ 회복 X)."""
    world = _village_world()
    dead = _bjorn(hp=0, hp_max=100)
    execute_wait_in_village("비요른", [dead], world)
    assert dead.hp == 0  # 변화 X


def test_wait_30_day_wraps_to_month() -> None:
    """day=30 + WAIT → day=1, month++."""
    world = _village_world()
    world.day_in_month = 30
    world.month_number = 1
    actor = _bjorn()
    execute_wait_in_village("비요른", [actor], world)
    assert world.day_in_month == 1
    assert world.month_number == 2


def test_wait_side_effects_emitted() -> None:
    world = _village_world()
    actor = _bjorn(hp=50, hp_max=100, sp=10, sp_max=30)
    result = execute_wait_in_village("비요른", [actor], world)
    assert any(
        "day_advanced=" in s for s in result.side_effects
    )
    assert any("hp_gain=비요른:" in s for s in result.side_effects)
    assert any("sp_gain=비요른:" in s for s in result.side_effects)


def test_wait_full_hp_emits_no_hp_gain_marker() -> None:
    """이미 full hp 본격 hp_gain marker 본격 X (★ +0)."""
    world = _village_world()
    actor = _bjorn(hp=100, hp_max=100, sp=30, sp_max=30)
    result = execute_wait_in_village("비요른", [actor], world)
    assert not any("hp_gain=" in s for s in result.side_effects)
    assert not any("sp_gain=" in s for s in result.side_effects)


# ─── 3. execute_enter_dungeon ───


def _village_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="district_7_plaza",
        city_id="rascania",
    )


def test_enter_outside_village_fails() -> None:
    world = WorldState()  # ACTIVE
    actor = _bjorn(hp=100)
    loc = _village_loc()
    result = execute_enter_dungeon("비요른", [actor], world, loc)
    assert result.success is False


def test_enter_not_day_1_fails() -> None:
    """day=15 본격 ENTER → fail (★ 19화 매월 1일만)."""
    world = _village_world()
    world.day_in_month = 15
    actor = _bjorn(hp=100)
    loc = _village_loc()
    result = execute_enter_dungeon("비요른", [actor], world, loc)
    assert result.success is False
    assert "매월 1일" in result.message


def test_enter_no_alive_fails() -> None:
    world = _village_world()
    dead = _bjorn(hp=0)
    loc = _village_loc()
    result = execute_enter_dungeon("비요른", [dead], world, loc)
    assert result.success is False
    assert "살아남은" in result.message


def test_enter_on_day_1_success() -> None:
    world = _village_world()
    # 본격 본격 본격 month 2 day 1 (★ wait 30회 본격)
    world.month_number = 2
    world.day_in_month = 1
    actor = _bjorn(hp=100)
    loc = _village_loc()
    result = execute_enter_dungeon("비요른", [actor], world, loc)
    assert result.success is True


def test_enter_resets_simulation_status() -> None:
    world = _village_world()
    world.month_number = 2
    world.day_in_month = 1
    world.simulation_over_reason = "7일 만료"
    world.simulation_over_turn = 100
    actor = _bjorn(hp=100)
    loc = _village_loc()
    execute_enter_dungeon("비요른", [actor], world, loc)
    assert world.simulation_status == SimulationStatus.ACTIVE
    assert world.simulation_over_reason is None
    assert world.simulation_over_turn is None
    assert world.hours_in_dungeon == 0


def test_enter_location_to_floor_1_entry() -> None:
    """본인 답: 항상 1층 재진입."""
    world = _village_world()
    world.day_in_month = 1
    actor = _bjorn(hp=100)
    loc = _village_loc()
    execute_enter_dungeon("비요른", [actor], world, loc)
    assert loc.realm == Realm.DUNGEON
    assert loc.floor == 1
    assert loc.sub_area == "진입점"  # ★ floor1 _ENTRANCE.name 정합
    assert loc.city_id is None


def test_enter_inventory_preserved() -> None:
    """본인 답: inventory 보존."""
    world = _village_world()
    world.day_in_month = 1
    actor = _bjorn(hp=100)
    actor.inventory.items.append(
        Item(
            name="9등급 마석",
            category=ItemCategory.MATERIAL,
            weight=1,
            grade=9,
        )
    )
    loc = _village_loc()
    execute_enter_dungeon("비요른", [actor], world, loc)
    assert len(actor.inventory.items) == 1


def test_enter_stone_preserved() -> None:
    """본인 답: stone 보존."""
    world = _village_world()
    world.day_in_month = 1
    actor = _bjorn(hp=100)
    actor.stone = 5000
    loc = _village_loc()
    execute_enter_dungeon("비요른", [actor], world, loc)
    assert actor.stone == 5000


def test_enter_rift_state_reset() -> None:
    """active_rifts 본격 reset (★ Phase 9 rift-cooldown 본격 본격 본격 자연 활성 가능).

    본 test 본격 ENTER_DUNGEON 본격 carry-over 본격 reset 본격 검증.
    rift_last_opened_periods 본격 pre-populate 본격 자연 활성 차단 (★ min 3 본격).
    """
    world = _village_world()
    world.day_in_month = 1
    world.month_number = 2  # ★ elapsed=1 (월 1→2) < min 3 → eligible X
    world.active_rifts = ["bloody_castle"]
    # ★ 4 균열 본격 본격 본격 본격 활성 본격 (★ 본 commit 본격 자연 활성 차단)
    from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS

    for rid in FLOOR1_RIFT_DEFS:
        world.rift_last_opened_periods[rid] = 1
    actor = _bjorn(hp=100)
    loc = _village_loc()
    execute_enter_dungeon("비요른", [actor], world, loc)
    # carry-over "bloody_castle" 본격 reset (★ 자연 활성 차단 본격 본격 X)
    assert world.active_rifts == []
    assert world.active_boss_encounter is None


def test_enter_side_effects_emitted() -> None:
    world = _village_world()
    world.month_number = 3
    world.day_in_month = 1
    actor = _bjorn(hp=100)
    loc = _village_loc()
    result = execute_enter_dungeon("비요른", [actor], world, loc)
    assert "dungeon_re_entered=month_3" in result.side_effects
    assert "floor_transition=1" in result.side_effects
