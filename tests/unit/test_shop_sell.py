"""Phase 9.16-a shop-sell — 2 shop + 가격 차등 + 호감도 변동.

검증 본질 (★ 18화 본문 정합):
- 허용 sub_area: general_store / alminus_market (★ blacksmith X)
- 가격 = base × shop_mult × affinity_mult
- 환전 우대 invariant 보존 (★ max SHOP_SELL < 환전)
- 호감도 +10%/+20% (★ 9.13 정합)
- atomic mutation (★ fail 시 변경 X)
- PlayerActionType.SHOP_SELL enum (★ 23 → 24)

본문 정합:
- 18화: SELL 위주 + '값을 잘 쳐주는 상점'
- general_store '전리품 처분'
- alminus_market '거래'
- blacksmith '제작/수리' (★ SELL X)

추측 (본문 X — docstring 명시):
- base 가격 수치 (★ 환전 비율 아래)
- shop multiplier (★ alminus 1.2 premium)
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _format_city_context
from service.game.state_v2 import (
    Character,
    Item,
    ItemCategory,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    MAGE_STONE_EXCHANGE_RATE,
    SHOP_AFFINITY_BOOST_TIER1,
    SHOP_AFFINITY_BOOST_TIER2,
    SHOP_NPC_ID,
    SHOP_PRICE_MULTIPLIER,
    SHOP_SELL_PRICE_BY_GRADE,
    SHOP_SELL_PRICE_DEFAULT,
    _sell_price_for_item,
    _shop_affinity_boost,
    execute_shop_sell,
)
from service.sim.types import PlayerActionType

# ─── 1. 가격 매핑 (★ 환전 우대 invariant) ───


def test_grade_9_below_exchange() -> None:
    """환전 9등급=20 → SHOP_SELL 9등급 < 20."""
    assert SHOP_SELL_PRICE_BY_GRADE[9] < MAGE_STONE_EXCHANGE_RATE[9]


def test_grade_8_below_exchange() -> None:
    """환전 8등급=100 → SHOP_SELL 8등급 < 100."""
    assert SHOP_SELL_PRICE_BY_GRADE[8] < MAGE_STONE_EXCHANGE_RATE[8]


def test_default_price_present() -> None:
    assert SHOP_SELL_PRICE_DEFAULT > 0


# ─── 2. shop multiplier (★ 18화 차등) ───


def test_alminus_premium_over_general() -> None:
    assert (
        SHOP_PRICE_MULTIPLIER["alminus_market"]
        > SHOP_PRICE_MULTIPLIER["general_store"]
    )


def test_blacksmith_not_in_shops() -> None:
    """blacksmith = 제작/수리만 (★ 18화 본문)."""
    assert "blacksmith" not in SHOP_PRICE_MULTIPLIER


def test_shop_npc_ids() -> None:
    """rapdonia.py NPCDef.id 정합."""
    assert SHOP_NPC_ID["general_store"] == "store_owner"
    assert SHOP_NPC_ID["alminus_market"] == "market_broker"


# ─── 3. affinity boost ───


def test_no_boost_low_affinity() -> None:
    assert _shop_affinity_boost(0) == 1.0
    assert _shop_affinity_boost(24) == 1.0


def test_tier1_boost_at_25() -> None:
    assert _shop_affinity_boost(25) == SHOP_AFFINITY_BOOST_TIER1


def test_tier2_boost_at_50() -> None:
    assert _shop_affinity_boost(50) == SHOP_AFFINITY_BOOST_TIER2


# ─── 4. _sell_price_for_item ───


def _stone(grade: int) -> Item:
    return Item(
        name=f"{grade}등급 마석",
        category=ItemCategory.MATERIAL,
        weight=1,
        grade=grade,
    )


def test_price_grade_9_general_no_affinity() -> None:
    """9등급 마석 × general_store × affinity=0 → base 5."""
    price = _sell_price_for_item(_stone(9), "general_store", 0)
    assert price == 5


def test_price_grade_9_alminus_no_affinity() -> None:
    """9등급 × alminus 1.2 × affinity=0 → 5 × 1.2 = 6."""
    price = _sell_price_for_item(_stone(9), "alminus_market", 0)
    assert price == 6


def test_price_grade_9_alminus_tier2_affinity() -> None:
    """9등급 × alminus 1.2 × affinity 50 1.2 → int(5 × 1.44) = 7."""
    price = _sell_price_for_item(_stone(9), "alminus_market", 50)
    assert price == 7


def test_price_alminus_max_still_below_exchange() -> None:
    """max SHOP_SELL 9등급 (1.44 × 5 = 7) < 환전 20 (★ invariant)."""
    max_price = _sell_price_for_item(_stone(9), "alminus_market", 100)
    assert max_price < MAGE_STONE_EXCHANGE_RATE[9]


def test_price_grade_8_alminus_max_below_exchange() -> None:
    """8등급 max SHOP_SELL (1.44 × 30 = 43) < 환전 100."""
    max_price = _sell_price_for_item(_stone(8), "alminus_market", 100)
    assert max_price < MAGE_STONE_EXCHANGE_RATE[8]


def test_price_default_no_grade() -> None:
    """grade=None → SHOP_SELL_PRICE_DEFAULT."""
    torch = Item(
        name="횃불", category=ItemCategory.CONSUMABLE, weight=1
    )
    price = _sell_price_for_item(torch, "general_store", 0)
    assert price == SHOP_SELL_PRICE_DEFAULT


# ─── 5. execute_shop_sell handler ───


def _general_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="general_store",
        city_id="rascania",
    )


def _alminus_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="alminus_market",
        city_id="rascania",
    )


def _blacksmith_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="blacksmith",
        city_id="rascania",
    )


def _dungeon_loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


def _bjorn() -> Character:
    return Character(
        name="비요른", race=Race.BARBARIAN, hp=150, hp_max=150
    )


def test_sell_general_store_baseline() -> None:
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _general_loc()
    )
    assert result.success is True
    assert actor.stone == 5
    assert len(actor.inventory.items) == 0


def test_sell_alminus_market_premium() -> None:
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _alminus_loc()
    )
    assert result.success is True
    assert actor.stone == 6


def test_sell_alminus_with_tier2_affinity() -> None:
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    world.npc_affinities["market_broker"] = 50
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _alminus_loc()
    )
    assert result.success is True
    assert actor.stone == 7
    assert "+20%" in result.message


def test_sell_general_with_tier1_affinity() -> None:
    """1.0 × 1.10 = 1.10 → int(5 × 1.10) = 5 (★ float trunc)."""
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    world.npc_affinities["store_owner"] = 25
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _general_loc()
    )
    assert result.success is True
    assert actor.stone == 5  # ★ int(5.5) = 5
    assert "+10%" in result.message


def test_sell_blacksmith_fails_atomic() -> None:
    """대장간 SELL X — 본문 18화 정합."""
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _blacksmith_loc()
    )
    assert result.success is False
    assert "대장간" in result.message
    assert actor.stone == 0  # ★ mutation X
    assert len(actor.inventory.items) == 1


def test_sell_outside_city_fails() -> None:
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _dungeon_loc()
    )
    assert result.success is False
    assert actor.stone == 0


def test_sell_empty_inventory_fails() -> None:
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _general_loc()
    )
    assert result.success is False


def test_sell_target_not_found_fails() -> None:
    actor = _bjorn()
    actor.inventory.items.append(
        Item(name="횃불", category=ItemCategory.CONSUMABLE, weight=1)
    )
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _general_loc()
    )
    assert result.success is False


def test_sell_actor_not_in_party_fails() -> None:
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    result = execute_shop_sell(
        "투르윈", "9등급 마석", [actor], world, _general_loc()
    )
    assert result.success is False


def test_sell_empty_target_fails() -> None:
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "", [actor], world, _general_loc()
    )
    assert result.success is False


def test_sell_substring_match_works() -> None:
    """target 'Vlater의 마석' 본격 정합 (★ boss stone Item.name 정합)."""
    actor = _bjorn()
    actor.inventory.items.append(
        Item(
            name="블라터의 마석",
            category=ItemCategory.MATERIAL,
            weight=1,
            grade=6,
        )
    )
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "마석", [actor], world, _general_loc()
    )
    assert result.success is True
    assert actor.stone == SHOP_SELL_PRICE_BY_GRADE[6]


def test_sell_side_effects() -> None:
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _alminus_loc()
    )
    assert any(
        s == "item_sold=비요른:9등급 마석" for s in result.side_effects
    )
    assert any(
        s == "stone_gained=비요른:+6" for s in result.side_effects
    )


def test_sell_baseline_no_boost_message() -> None:
    actor = _bjorn()
    actor.inventory.items.append(_stone(9))
    world = WorldState()
    result = execute_shop_sell(
        "비요른", "9등급 마석", [actor], world, _general_loc()
    )
    assert "boost" not in result.message


# ─── 6. PlayerActionType ───


def test_shop_sell_enum_value() -> None:
    assert PlayerActionType.SHOP_SELL.value == "shop_sell"


# ─── 7. gm_agent prompt hint ───


def _shop_ctx(sub_area: str, affinity: int = 0) -> dict[str, Any]:
    npc_id = SHOP_NPC_ID.get(sub_area, "")
    return {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": sub_area,
            "city_id": "rascania",
        },
        "v2_world_state": {
            "npc_affinities": {npc_id: affinity} if npc_id else {},
        },
    }


def test_prompt_general_store_hint() -> None:
    out = _format_city_context(_shop_ctx("general_store"))
    assert "잡화점" in out
    assert "SHOP_SELL" in out
    assert "×1.00" in out


def test_prompt_alminus_market_premium_hint() -> None:
    out = _format_city_context(_shop_ctx("alminus_market"))
    assert "알미너스 거래소" in out
    assert "SHOP_SELL" in out
    assert "×1.20" in out


def test_prompt_alminus_with_tier2_affinity() -> None:
    out = _format_city_context(_shop_ctx("alminus_market", affinity=50))
    # 1.2 × 1.2 = 1.44
    assert "×1.44" in out


def test_prompt_blacksmith_sell_x_hint() -> None:
    out = _format_city_context(
        {
            "v2_initial_location": {
                "realm": "도시",
                "sub_area": "blacksmith",
                "city_id": "rascania",
            }
        }
    )
    assert "대장간" in out
    assert "SELL X" in out


def test_prompt_blacksmith_no_shop_sell_action() -> None:
    """blacksmith prompt 본격 SHOP_SELL action 표시 X (★ 본문 strict)."""
    out = _format_city_context(
        {
            "v2_initial_location": {
                "realm": "도시",
                "sub_area": "blacksmith",
                "city_id": "rascania",
            }
        }
    )
    assert "SHOP_SELL" not in out
