"""Phase 9.16-b2 shop-buy-discount — SHOP_BUY 호감도 할인.

검증 본질 (★ 9.13/9.15 mechanism 일관):
- SHOP_BUY_DISCOUNT_TIER1/2 = 0.90/0.80 (★ SELL boost 대칭)
- SHOP_NPC_ID 확장 (★ blacksmith_master 추가)
- _shop_buy_discount threshold (★ 25/50 정합)
- _buy_price_for_item: base × shop_mult × discount
- execute_shop_buy 본격 호감도 wire (★ 21화 정합 정합)
- shop별 독립 호감도
- 대칭 invariant (★ TIER1+TIER1' = 2.0)

본문 X — 추측 (★ docstring 명시):
- SHOP_SELL boost 대칭 수치

본인 답:
- 호감도 할인 ✓
- 9.13/9.15 mechanism 일관 ✓
"""

from __future__ import annotations

from typing import Any

import pytest

from service.game.gm_agent import _format_city_context
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    AFFINITY_THRESHOLD_TIER1,
    AFFINITY_THRESHOLD_TIER2,
    SHOP_AFFINITY_BOOST_TIER1,
    SHOP_AFFINITY_BOOST_TIER2,
    SHOP_BUY_DISCOUNT_TIER1,
    SHOP_BUY_DISCOUNT_TIER2,
    SHOP_NPC_ID,
    _buy_price_for_item,
    _get_shop_item,
    _shop_buy_discount,
    execute_shop_buy,
)

# ─── 1. _shop_buy_discount threshold ───


def test_discount_low_affinity_baseline() -> None:
    assert _shop_buy_discount(0) == 1.0
    assert _shop_buy_discount(24) == 1.0


def test_discount_tier1_at_25() -> None:
    assert _shop_buy_discount(25) == SHOP_BUY_DISCOUNT_TIER1
    assert _shop_buy_discount(49) == SHOP_BUY_DISCOUNT_TIER1


def test_discount_tier2_at_50() -> None:
    assert _shop_buy_discount(50) == SHOP_BUY_DISCOUNT_TIER2
    assert _shop_buy_discount(100) == SHOP_BUY_DISCOUNT_TIER2


def test_threshold_matches_9_13() -> None:
    assert AFFINITY_THRESHOLD_TIER1 == 25
    assert AFFINITY_THRESHOLD_TIER2 == 50


# ─── 2. SELL boost 대칭 invariant ───


def test_tier1_symmetry_with_sell() -> None:
    """SHOP_SELL +10% boost ↔ SHOP_BUY -10% 할인 (★ TIER1+TIER1' = 2.0)."""
    assert SHOP_AFFINITY_BOOST_TIER1 + SHOP_BUY_DISCOUNT_TIER1 == pytest.approx(2.0)


def test_tier2_symmetry_with_sell() -> None:
    """TIER2: 1.20 + 0.80 = 2.00."""
    assert SHOP_AFFINITY_BOOST_TIER2 + SHOP_BUY_DISCOUNT_TIER2 == pytest.approx(2.0)


# ─── 3. SHOP_NPC_ID extension ───


def test_blacksmith_master_in_shop_npc_id() -> None:
    """9.16-b2 본격 blacksmith_master 추가 (★ BUY 호감도 lookup)."""
    assert SHOP_NPC_ID["blacksmith"] == "blacksmith_master"


def test_existing_npc_ids_preserved() -> None:
    """9.16-a SHOP_SELL 본격 정합 유지."""
    assert SHOP_NPC_ID["general_store"] == "store_owner"
    assert SHOP_NPC_ID["alminus_market"] == "market_broker"


# ─── 4. _buy_price_for_item ───


def test_buy_price_blacksmith_baseline() -> None:
    """affinity=0 → base 360k × 1.0 × 1.0 = 360k (★ 21화 본문)."""
    item = _get_shop_item("blacksmith", "하프 아머")
    assert item is not None
    price = _buy_price_for_item(item, "blacksmith", 0)
    assert price == 360_000


def test_buy_price_blacksmith_tier1_discount() -> None:
    """affinity 25 → -10% → 360k × 0.9 = 324k."""
    item = _get_shop_item("blacksmith", "하프 아머")
    assert item is not None
    price = _buy_price_for_item(item, "blacksmith", 25)
    assert price == 324_000


def test_buy_price_blacksmith_tier2_discount() -> None:
    """affinity 50 → -20% → 360k × 0.8 = 288k."""
    item = _get_shop_item("blacksmith", "하프 아머")
    assert item is not None
    price = _buy_price_for_item(item, "blacksmith", 50)
    assert price == 288_000


def test_buy_price_general_store_tier2() -> None:
    """포션 10k × 0.8 = 8000."""
    item = _get_shop_item("general_store", "회복 포션")
    assert item is not None
    price = _buy_price_for_item(item, "general_store", 50)
    assert price == 8000


# ─── 5. execute_shop_buy 호감도 wire ───


def _blacksmith_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="blacksmith",
        city_id="rascania",
    )


def _general_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="general_store",
        city_id="rascania",
    )


def _bjorn(stone: int = 500_000) -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        stone=stone,
    )


def test_buy_baseline_no_affinity() -> None:
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert result.success is True
    assert actor.stone == 500_000 - 360_000
    assert "boost" not in result.message
    assert "할인" not in result.message


def test_buy_blacksmith_tier1_discount() -> None:
    actor = _bjorn()
    world = WorldState()
    world.npc_affinities["blacksmith_master"] = 25
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert result.success is True
    assert actor.stone == 500_000 - 324_000
    assert "-10%" in result.message


def test_buy_blacksmith_tier2_discount() -> None:
    actor = _bjorn()
    world = WorldState()
    world.npc_affinities["blacksmith_master"] = 50
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert result.success is True
    assert actor.stone == 500_000 - 288_000
    assert "-20%" in result.message


def test_buy_general_store_tier2_discount() -> None:
    actor = _bjorn(stone=20_000)
    world = WorldState()
    world.npc_affinities["store_owner"] = 50
    result = execute_shop_buy(
        "비요른", "회복 포션", [actor], world, _general_loc()
    )
    assert result.success is True
    assert actor.stone == 20_000 - 8000


def test_buy_insufficient_after_discount_atomic() -> None:
    """할인 적용 후에도 부족 → fail + mutation X."""
    actor = _bjorn(stone=200_000)
    world = WorldState()
    world.npc_affinities["blacksmith_master"] = 50  # ★ 288k 본격 본격 X
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert result.success is False
    assert actor.stone == 200_000
    assert len(actor.inventory.items) == 0
    # ★ 비용 message 본격 할인 적용 비용 표시
    assert "288000" in result.message


def test_buy_exact_discounted_cost_works() -> None:
    """할인 cost 정확 = stone."""
    actor = _bjorn(stone=288_000)
    world = WorldState()
    world.npc_affinities["blacksmith_master"] = 50
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert result.success is True
    assert actor.stone == 0


def test_buy_shop_independence() -> None:
    """blacksmith_master ≠ store_owner — shop별 독립."""
    actor = _bjorn()
    world = WorldState()
    world.npc_affinities["store_owner"] = 100  # ★ 다른 shop
    world.npc_affinities["blacksmith_master"] = 0
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    # blacksmith_master=0 → 할인 X
    assert result.success is True
    assert actor.stone == 500_000 - 360_000
    assert "할인" not in result.message


def test_buy_side_effect_uses_discounted_cost() -> None:
    actor = _bjorn()
    world = WorldState()
    world.npc_affinities["blacksmith_master"] = 50
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert any(
        s == "stone_paid=비요른:-288000" for s in result.side_effects
    )


# ─── 6. gm_agent prompt hint 할인 표시 ───


def _ctx(sub_area: str, affinity_npc: str = "", affinity: int = 0) -> dict[str, Any]:
    return {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": sub_area,
            "city_id": "rascania",
        },
        "v2_world_state": {
            "npc_affinities": (
                {affinity_npc: affinity} if affinity_npc else {}
            ),
        },
    }


def test_prompt_baseline_no_discount() -> None:
    out = _format_city_context(_ctx("blacksmith"))
    assert "할인" not in out
    assert "360,000" in out  # ★ baseline 21화


def test_prompt_blacksmith_tier1_discount_hint() -> None:
    out = _format_city_context(
        _ctx("blacksmith", "blacksmith_master", 30)
    )
    assert "할인 -10%" in out
    assert "324,000" in out


def test_prompt_blacksmith_tier2_discount_hint() -> None:
    out = _format_city_context(
        _ctx("blacksmith", "blacksmith_master", 70)
    )
    assert "할인 -20%" in out
    assert "288,000" in out


def test_prompt_general_store_tier2_discount() -> None:
    out = _format_city_context(
        _ctx("general_store", "store_owner", 50)
    )
    assert "할인 -20%" in out
    assert "8,000" in out  # ★ 회복 포션 8k
