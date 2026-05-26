"""Phase 9.13 npc-affinity-effects — 환전 boost + 신전 할인.

검증 본질 (★ 9.7 호감도 dead consumer 방지):
- _exchange_rate_boost threshold (★ 25/50 정합)
- _temple_heal_discount threshold (★ 25/50)
- TempleDeity.priest_npc_id field (★ rapdonia.py NPCDef 정합)
- exchange_mage_stones 본격 호감도 boost wire
- execute_heal_at_temple 본격 사제 호감도 할인 wire
- per-deity 독립 (★ 토베라 ≠ 레아틀라스 affinity)
- gm_agent prompt hint (★ exchange + temple)

본문 X — 추측 (★ docstring 명시):
- 환전 +10%/+20% / 신전 -20%/-50% 수치
- threshold 25/50 (★ 9.7 LIBRARY 정합)
"""

from __future__ import annotations

from typing import Any

from service.game.cities.temples import KARUYI, REATLAS, TOBERAH
from service.game.gm_agent import _format_city_context
from service.game.state_v2 import (
    Character,
    Injury,
    Item,
    ItemCategory,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    AFFINITY_THRESHOLD_TIER1,
    AFFINITY_THRESHOLD_TIER2,
    EXCHANGE_BOOST_MULTIPLIER_TIER1,
    EXCHANGE_BOOST_MULTIPLIER_TIER2,
    EXCHANGE_CLERK_NPC_ID,
    HEAL_COST_PER_SEVERITY,
    TEMPLE_DISCOUNT_MULTIPLIER_TIER1,
    TEMPLE_DISCOUNT_MULTIPLIER_TIER2,
    _exchange_rate_boost,
    _temple_heal_discount,
    exchange_mage_stones,
    execute_heal_at_temple,
)

# ─── 1. _exchange_rate_boost threshold ───


def test_boost_low_affinity_baseline() -> None:
    assert _exchange_rate_boost(0) == 1.0
    assert _exchange_rate_boost(24) == 1.0


def test_boost_tier1_at_25() -> None:
    assert _exchange_rate_boost(25) == EXCHANGE_BOOST_MULTIPLIER_TIER1
    assert _exchange_rate_boost(49) == EXCHANGE_BOOST_MULTIPLIER_TIER1


def test_boost_tier2_at_50() -> None:
    assert _exchange_rate_boost(50) == EXCHANGE_BOOST_MULTIPLIER_TIER2
    assert _exchange_rate_boost(100) == EXCHANGE_BOOST_MULTIPLIER_TIER2


# ─── 2. _temple_heal_discount threshold ───


def test_discount_low_affinity_baseline() -> None:
    assert _temple_heal_discount(0) == 1.0
    assert _temple_heal_discount(24) == 1.0


def test_discount_tier1_at_25() -> None:
    assert _temple_heal_discount(25) == TEMPLE_DISCOUNT_MULTIPLIER_TIER1


def test_discount_tier2_at_50() -> None:
    assert _temple_heal_discount(50) == TEMPLE_DISCOUNT_MULTIPLIER_TIER2


def test_threshold_constants() -> None:
    """9.7 LIBRARY 정합 — 25 / 50 본격."""
    assert AFFINITY_THRESHOLD_TIER1 == 25
    assert AFFINITY_THRESHOLD_TIER2 == 50


# ─── 3. TempleDeity.priest_npc_id ───


def test_toberah_priest_npc_id() -> None:
    assert TOBERAH.priest_npc_id == "rairin_ersina"


def test_reatlas_priest_npc_id() -> None:
    assert REATLAS.priest_npc_id == "reatlas_priest"


def test_karuyi_priest_npc_id() -> None:
    assert KARUYI.priest_npc_id == "elisa"


# ─── 4. exchange_mage_stones boost wire ───


def _exchange_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="exchange_office",
        city_id="rascania",
    )


def _stone_item(grade: int) -> Item:
    return Item(
        name=f"{grade}등급 마석",
        category=ItemCategory.MATERIAL,
        weight=1,
        grade=grade,
    )


def test_exchange_no_world_baseline() -> None:
    """world=None — 기존 호출 호환성 (★ baseline rate)."""
    actor = Character(name="비요른", race=Race.BARBARIAN)
    actor.inventory.items.append(_stone_item(9))
    result = exchange_mage_stones(actor, _exchange_loc())
    assert result.success is True
    assert actor.stone == 20  # ★ 9등급 baseline


def test_exchange_zero_affinity_baseline() -> None:
    world = WorldState()
    actor = Character(name="비요른", race=Race.BARBARIAN)
    actor.inventory.items.append(_stone_item(9))
    result = exchange_mage_stones(actor, _exchange_loc(), world)
    assert result.success is True
    assert actor.stone == 20  # ★ baseline


def test_exchange_tier1_boost_25() -> None:
    """affinity 25 → +10% → 9등급 20 → 22."""
    world = WorldState()
    world.npc_affinities[EXCHANGE_CLERK_NPC_ID] = 25
    actor = Character(name="비요른", race=Race.BARBARIAN)
    actor.inventory.items.append(_stone_item(9))
    result = exchange_mage_stones(actor, _exchange_loc(), world)
    assert result.success is True
    assert actor.stone == 22  # ★ int(20 * 1.10)


def test_exchange_tier2_boost_50() -> None:
    """affinity 50 → +20% → 9등급 20 → 24."""
    world = WorldState()
    world.npc_affinities[EXCHANGE_CLERK_NPC_ID] = 50
    actor = Character(name="비요른", race=Race.BARBARIAN)
    actor.inventory.items.append(_stone_item(9))
    result = exchange_mage_stones(actor, _exchange_loc(), world)
    assert result.success is True
    assert actor.stone == 24  # ★ int(20 * 1.20)


def test_exchange_boost_message_shows_pct() -> None:
    world = WorldState()
    world.npc_affinities[EXCHANGE_CLERK_NPC_ID] = 50
    actor = Character(name="비요른", race=Race.BARBARIAN)
    actor.inventory.items.append(_stone_item(8))
    result = exchange_mage_stones(actor, _exchange_loc(), world)
    assert "+20%" in result.message


def test_exchange_baseline_no_boost_message() -> None:
    world = WorldState()
    actor = Character(name="비요른", race=Race.BARBARIAN)
    actor.inventory.items.append(_stone_item(9))
    result = exchange_mage_stones(actor, _exchange_loc(), world)
    assert "boost" not in result.message


# ─── 5. execute_heal_at_temple discount wire ───


def _temple_loc(sub_area: str = "reatlas_temple") -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area=sub_area,
        city_id="rascania",
    )


def _injured_actor(stone: int = 10000) -> Character:
    c = Character(
        name="비요른", race=Race.BARBARIAN, hp=80, hp_max=100, stone=stone
    )
    c.injuries.append(
        Injury(severity="minor", body_part="arm", recovery_days=5)
    )
    return c


def test_heal_zero_affinity_baseline() -> None:
    world = WorldState()
    actor = _injured_actor()
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("reatlas_temple")
    )
    assert result.success is True
    assert actor.stone == 10000 - HEAL_COST_PER_SEVERITY["minor"]


def test_heal_tier1_discount_25() -> None:
    """레아틀라스 사제 25 호감도 → minor 200 → 160."""
    world = WorldState()
    world.npc_affinities[REATLAS.priest_npc_id] = 25
    actor = _injured_actor()
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("reatlas_temple")
    )
    assert result.success is True
    expected = int(HEAL_COST_PER_SEVERITY["minor"] * 0.80)
    assert actor.stone == 10000 - expected


def test_heal_tier2_discount_50() -> None:
    """엘리사 50 호감도 → minor 200 → 100."""
    world = WorldState()
    world.npc_affinities[KARUYI.priest_npc_id] = 50
    actor = _injured_actor()
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("karuyi_temple")
    )
    assert result.success is True
    expected = int(HEAL_COST_PER_SEVERITY["minor"] * 0.50)
    assert actor.stone == 10000 - expected


def test_heal_per_deity_independent_affinity() -> None:
    """토베라 호감도 max ≠ 레아틀라스 호감도 0 — 독립."""
    world = WorldState()
    world.npc_affinities[TOBERAH.priest_npc_id] = 100  # ★ 토베라 max
    world.npc_affinities[REATLAS.priest_npc_id] = 0
    actor = _injured_actor()
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("reatlas_temple")
    )
    # 위치 = reatlas → reatlas affinity=0 → baseline (★ 할인 X)
    assert result.success is True
    assert actor.stone == 10000 - HEAL_COST_PER_SEVERITY["minor"]


def test_heal_discount_message_shows_pct() -> None:
    world = WorldState()
    world.npc_affinities[KARUYI.priest_npc_id] = 50
    actor = _injured_actor()
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("karuyi_temple")
    )
    assert "-50%" in result.message


def test_heal_baseline_no_discount_message() -> None:
    world = WorldState()
    actor = _injured_actor()
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("reatlas_temple")
    )
    assert "boost" not in result.message


# ─── 6. gm_agent prompt hint ───


def _ctx_with_affinity(
    sub_area: str, affinities: dict[str, int] | None = None
) -> dict[str, Any]:
    return {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": sub_area,
            "city_id": "rascania",
        },
        "v2_world_state": {
            "npc_affinities": affinities or {},
        },
    }


def test_prompt_exchange_low_no_boost_hint() -> None:
    out = _format_city_context(_ctx_with_affinity("exchange_office"))
    assert "환전 +" not in out


def test_prompt_exchange_tier1_boost_hint() -> None:
    out = _format_city_context(
        _ctx_with_affinity(
            "exchange_office", {EXCHANGE_CLERK_NPC_ID: 30}
        )
    )
    assert "환전소 호감도 30" in out
    assert "환전 +10%" in out


def test_prompt_exchange_tier2_boost_hint() -> None:
    out = _format_city_context(
        _ctx_with_affinity(
            "exchange_office", {EXCHANGE_CLERK_NPC_ID: 70}
        )
    )
    assert "환전 +20%" in out


def test_prompt_temple_tier1_discount_hint() -> None:
    out = _format_city_context(
        _ctx_with_affinity(
            "karuyi_temple", {KARUYI.priest_npc_id: 30}
        )
    )
    assert "엘리사 호감도 30" in out
    assert "치료 -20%" in out


def test_prompt_temple_tier2_discount_hint() -> None:
    out = _format_city_context(
        _ctx_with_affinity(
            "karuyi_temple", {KARUYI.priest_npc_id: 60}
        )
    )
    assert "치료 -50%" in out


def test_prompt_temple_baseline_no_discount_hint() -> None:
    out = _format_city_context(_ctx_with_affinity("karuyi_temple"))
    assert "치료 -" not in out


def test_prompt_temple_no_priest_npc_id_no_hint() -> None:
    """priest_npc_id 빈 placeholder → hint X (★ defensive)."""
    out = _format_city_context(_ctx_with_affinity("reatlas_temple"))
    # reatlas_priest affinity=0 → discount=1.0 → hint X
    assert "치료 -" not in out
