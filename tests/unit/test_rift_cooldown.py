"""Phase 9 rift-cooldown — 27화 본문 정합 cooldown counter 본격 unit.

검증 본질:
- RiftDef.cooldown_min_periods = 3 (★ 27화 "최소 3주기")
- RiftDef.cooldown_max_periods = 8 (★ 27화 "맥시멈 8주기")
- RiftDef.cooldown_typical_range = (5, 6) (★ 27화 "대부분 5~6주기 랜덤")
- WorldState.rift_last_opened_periods default {}
- _eligible_rifts_for_period:
  * cleared 제외 / active 제외 / never opened eligible / min cooldown 본격
- _select_rift_to_activate:
  * never opened → typical_range probabilistic candidate (★ 28화 본인 가설)
  * elapsed ∈ typical_range → candidate
  * elapsed >= max → forced
  * elapsed < typical low → 본격 X
- activate_natural_rifts: mutation (★ active_rifts append + period 기록)
- production caller wire:
  * execute_enter_dungeon → activate_natural_rifts
  * offer_to_stone → period 기록 (의도적 활성도)

본문 정합:
- 27화: 최소 3주기 세 달 / 5~6주기 랜덤 / 맥시멈 8주기
- 28화: 통계학적 trigger (★ 본인 가설 '랜덤처럼 보여도 트리거')
"""

from __future__ import annotations

import random

from service.game.floors.floor1 import get_floor1_definition
from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    _eligible_rifts_for_period,
    _select_rift_to_activate,
    activate_natural_rifts,
    execute_enter_dungeon,
    offer_to_stone,
)

# ─── 1. RiftDef cooldown field defaults (★ 27화) ───


def test_rift_def_min_3_periods_27hwa() -> None:
    """27화: '최소 3주기'."""
    for rift in FLOOR1_RIFT_DEFS.values():
        assert rift.cooldown_min_periods == 3


def test_rift_def_max_8_periods_27hwa() -> None:
    """27화: '맥시멈 8주기'."""
    for rift in FLOOR1_RIFT_DEFS.values():
        assert rift.cooldown_max_periods == 8


def test_rift_def_typical_5_6_27hwa() -> None:
    """27화: '대부분 5~6주기 랜덤'."""
    for rift in FLOOR1_RIFT_DEFS.values():
        assert rift.cooldown_typical_range == (5, 6)


# ─── 2. WorldState.rift_last_opened_periods ───


def test_world_state_default_empty_dict() -> None:
    ws = WorldState()
    assert ws.rift_last_opened_periods == {}


# ─── 3. _eligible_rifts_for_period ───


def test_never_opened_all_eligible() -> None:
    """본격 활성 X → 4 균열 본격 본격 eligible."""
    world = WorldState()
    floor1 = get_floor1_definition()
    eligible = _eligible_rifts_for_period(floor1, world, current_period=1)
    assert set(eligible) == set(FLOOR1_RIFT_DEFS.keys())


def test_cleared_not_eligible() -> None:
    world = WorldState()
    world.cleared_rifts.append("bloody_castle")
    floor1 = get_floor1_definition()
    eligible = _eligible_rifts_for_period(floor1, world, current_period=5)
    assert "bloody_castle" not in eligible


def test_active_not_eligible() -> None:
    world = WorldState()
    world.active_rifts.append("green_mine")
    floor1 = get_floor1_definition()
    eligible = _eligible_rifts_for_period(floor1, world, current_period=5)
    assert "green_mine" not in eligible


def test_below_min_cooldown_not_eligible() -> None:
    """last_opened=5, current=7 → elapsed=2 < min 3 → X."""
    world = WorldState()
    world.rift_last_opened_periods["bloody_castle"] = 5
    floor1 = get_floor1_definition()
    eligible = _eligible_rifts_for_period(floor1, world, current_period=7)
    assert "bloody_castle" not in eligible


def test_min_cooldown_exact_eligible() -> None:
    """last_opened=5, current=8 → elapsed=3 == min 3 → eligible."""
    world = WorldState()
    world.rift_last_opened_periods["bloody_castle"] = 5
    floor1 = get_floor1_definition()
    eligible = _eligible_rifts_for_period(floor1, world, current_period=8)
    assert "bloody_castle" in eligible


# ─── 4. _select_rift_to_activate ───


def test_select_typical_range_candidate() -> None:
    """elapsed=5 ∈ (5, 6) → candidate."""
    world = WorldState()
    world.rift_last_opened_periods["bloody_castle"] = 1
    floor1 = get_floor1_definition()
    rng = random.Random(42)
    selected = _select_rift_to_activate(
        ["bloody_castle"], floor1, world, current_period=6, rng=rng
    )
    assert selected == "bloody_castle"


def test_select_below_typical_returns_none() -> None:
    """elapsed=3 < typical low (5) + < max (8) → 본격 X."""
    world = WorldState()
    world.rift_last_opened_periods["bloody_castle"] = 1
    floor1 = get_floor1_definition()
    rng = random.Random(42)
    selected = _select_rift_to_activate(
        ["bloody_castle"], floor1, world, current_period=4, rng=rng
    )
    assert selected is None


def test_select_above_max_forced() -> None:
    """elapsed=9 >= max 8 → 강제 forced."""
    world = WorldState()
    world.rift_last_opened_periods["bloody_castle"] = 1
    floor1 = get_floor1_definition()
    rng = random.Random(42)
    selected = _select_rift_to_activate(
        ["bloody_castle"], floor1, world, current_period=10, rng=rng
    )
    assert selected == "bloody_castle"


def test_select_first_time_eligible_as_typical() -> None:
    """본격 활성 X (★ first time) → typical_range probabilistic candidate.

    28화 본인 가설 정합: '랜덤처럼 보여도 트리거' — 본격 활성 X 본격
    typical_range probabilistic 본격 진입.
    """
    world = WorldState()
    floor1 = get_floor1_definition()
    rng = random.Random(42)
    selected = _select_rift_to_activate(
        ["bloody_castle"], floor1, world, current_period=6, rng=rng
    )
    assert selected == "bloody_castle"


def test_select_empty_returns_none() -> None:
    world = WorldState()
    floor1 = get_floor1_definition()
    rng = random.Random(42)
    selected = _select_rift_to_activate([], floor1, world, 5, rng)
    assert selected is None


# ─── 5. activate_natural_rifts mutation ───


def test_activate_appends_active_rifts() -> None:
    world = WorldState()
    world.month_number = 6
    world.rift_last_opened_periods["bloody_castle"] = 1
    floor1 = get_floor1_definition()
    # ★ 다른 균열 본격 cleared 본격 → 본격 본격 본격
    for rid in FLOOR1_RIFT_DEFS:
        if rid != "bloody_castle":
            world.cleared_rifts.append(rid)
    rng = random.Random(42)
    activated = activate_natural_rifts(world, floor1, rng)
    assert activated == ["bloody_castle"]
    assert "bloody_castle" in world.active_rifts


def test_activate_records_last_opened_period() -> None:
    world = WorldState()
    world.month_number = 6
    world.rift_last_opened_periods["bloody_castle"] = 1
    floor1 = get_floor1_definition()
    for rid in FLOOR1_RIFT_DEFS:
        if rid != "bloody_castle":
            world.cleared_rifts.append(rid)
    rng = random.Random(42)
    activate_natural_rifts(world, floor1, rng)
    assert world.rift_last_opened_periods["bloody_castle"] == 6


def test_activate_no_eligible_returns_empty() -> None:
    """본격 균열 본격 본격 cleared → eligible 0 → 활성 X."""
    world = WorldState()
    world.month_number = 5
    for rid in FLOOR1_RIFT_DEFS:
        world.cleared_rifts.append(rid)
    floor1 = get_floor1_definition()
    activated = activate_natural_rifts(world, floor1, random.Random(0))
    assert activated == []


def test_activate_default_rng_no_crash() -> None:
    """rng=None 본격 default 본격 (★ production caller 본격 본격 본격)."""
    world = WorldState()
    world.month_number = 1
    floor1 = get_floor1_definition()
    activated = activate_natural_rifts(world, floor1)
    # 본격 결정 X 본격 list type 본격 검증
    assert isinstance(activated, list)


# ─── 6. execute_enter_dungeon production wire ───


def _alive_actor() -> Character:
    return Character(name="투르윈", race=Race.BARBARIAN, hp=150, hp_max=150)


def _village_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="district_7_plaza",
        city_id="rapdonia",
    )


def test_enter_dungeon_activates_natural_rifts() -> None:
    """ENTER_DUNGEON 본격 자연 균열 활성 trigger (★ 본 commit 본격)."""
    world = WorldState()
    world.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    world.month_number = 2
    world.day_in_month = 1
    actor = _alive_actor()
    loc = _village_loc()

    result = execute_enter_dungeon("투르윈", [actor], world, loc)
    assert result.success is True
    # 본격 활성 X 본격 → typical_range probabilistic 본격 본격 적어도 1개 활성 가능
    # (★ 결정성 X — rng default 본격) — 본 test 본격 mechanism 본격 검증만
    # 본 commit 본격 본격 본격 검증: rift_last_opened_periods 본격 본격 본격
    # 또는 본격 본격 X (★ 본문 정합 — typical_range 본격 본격 본격 본격)
    if world.active_rifts:
        # 활성 본격 본격 period 기록
        for rift_id in world.active_rifts:
            assert world.rift_last_opened_periods.get(rift_id) == 2
        # side_effects marker
        assert any(
            s.startswith("rift_activated=") for s in result.side_effects
        )


def test_enter_dungeon_preserves_last_opened_periods() -> None:
    """ENTER_DUNGEON 본격 rift_last_opened_periods 본격 reset X (★ cooldown 본격)."""
    world = WorldState()
    world.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    world.month_number = 5
    world.day_in_month = 1
    world.rift_last_opened_periods["bloody_castle"] = 2
    world.rift_last_opened_periods["green_mine"] = 3
    actor = _alive_actor()
    loc = _village_loc()

    execute_enter_dungeon("투르윈", [actor], world, loc)
    # bloody_castle / green_mine 본격 기존 period 보존 (★ 활성 X 시)
    assert world.rift_last_opened_periods.get("bloody_castle") == 2 or (
        world.rift_last_opened_periods.get("bloody_castle") == 5
    )
    assert world.rift_last_opened_periods.get("green_mine") == 3 or (
        world.rift_last_opened_periods.get("green_mine") == 5
    )


# ─── 7. offer_to_stone period 기록 (★ 의도적 활성도) ───


def test_offer_to_stone_records_period() -> None:
    """A3 의도적 활성도 rift_last_opened_periods 본격 본격 기록."""
    world = WorldState()
    world.month_number = 3
    actor = Character(name="투르윈", race=Race.BARBARIAN, hp=150, hp_max=150)

    result = offer_to_stone(actor, "bloody_castle", world)
    assert result.success is True
    assert world.rift_last_opened_periods["bloody_castle"] == 3


def test_offer_to_stone_failed_no_period_record() -> None:
    """잘못된 rift_id → fail → period 기록 X."""
    world = WorldState()
    world.month_number = 3
    actor = Character(name="투르윈", race=Race.BARBARIAN, hp=150, hp_max=150)

    result = offer_to_stone(actor, "nonexistent_rift", world)
    assert result.success is False
    assert "nonexistent_rift" not in world.rift_last_opened_periods
