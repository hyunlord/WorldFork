"""Phase 9.16-b shop-buy — blacksmith + general_store BUY.

검증 본질:
- ShopItem dataclass (★ name / item_category / base_price / weight / grade)
- SHOP_INVENTORY:
  * blacksmith 본격 21화 가격 정합 (★ 하프 아머 36만 / 강철 검 25만)
  * general_store 본격 포션/식량/횃불 (추측)
  * alminus_market 본격 X (★ 본 commit X)
- SHOP_BUY_MULTIPLIER (★ 본 commit baseline 1.0)
- _get_shop_item substring 매칭
- execute_shop_buy:
  * blacksmith + general_store OK
  * alminus / 외부 / non-shop fail
  * 비용 부족 → atomic fail
  * mutation: stone-=price, inventory.append
- PlayerActionType.SHOP_BUY enum

본문 정합:
- 21화: 하프 아머 36만 / 무기 25만 (★ 본문 직접)

추측 (본문 X — docstring):
- 강철 투구 15만 / 단검 5만
- 회복 포션 1만 / 식량 500 / 횃불 100
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _format_city_context
from service.game.state_v2 import (
    Character,
    ItemCategory,
    Location,
    Race,
    Realm,
    ShopItem,
    WorldState,
)
from service.game.turn_handler_v2 import (
    SHOP_BUY_MULTIPLIER,
    SHOP_INVENTORY,
    _get_shop_item,
    execute_shop_buy,
)
from service.sim.types import PlayerActionType

# ─── 1. ShopItem dataclass ───


def test_shop_item_frozen() -> None:
    item = ShopItem(
        name="하프 아머",
        item_category=ItemCategory.ARMOR,
        base_price=360_000,
    )
    try:
        item.name = "X"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("ShopItem 본격 frozen 본격 X")


def test_shop_item_defaults() -> None:
    item = ShopItem(
        name="포션",
        item_category=ItemCategory.CONSUMABLE,
        base_price=10_000,
    )
    assert item.weight == 1
    assert item.grade is None


# ─── 2. SHOP_INVENTORY 정합 (★ 21화 본문) ───


def test_blacksmith_inventory_has_half_armor() -> None:
    inv = SHOP_INVENTORY["blacksmith"]
    assert any(i.name == "하프 아머" for i in inv)


def test_half_armor_price_360k_21hwa() -> None:
    """21화 본문 직접 — 하프 아머 36만."""
    item = _get_shop_item("blacksmith", "하프 아머")
    assert item is not None
    assert item.base_price == 360_000


def test_steel_sword_price_250k_21hwa() -> None:
    """21화 본문 — 무기 25만."""
    item = _get_shop_item("blacksmith", "강철 검")
    assert item is not None
    assert item.base_price == 250_000


def test_blacksmith_items_are_equipment() -> None:
    """대장간 = 무기/방어구만."""
    inv = SHOP_INVENTORY["blacksmith"]
    for item in inv:
        assert item.item_category in (
            ItemCategory.WEAPON,
            ItemCategory.ARMOR,
        )


def test_general_store_inventory_has_potion() -> None:
    inv = SHOP_INVENTORY["general_store"]
    assert any(i.name == "회복 포션" for i in inv)


def test_general_store_items_are_consumable() -> None:
    inv = SHOP_INVENTORY["general_store"]
    for item in inv:
        assert item.item_category == ItemCategory.CONSUMABLE


def test_alminus_market_no_buy_inventory() -> None:
    """alminus_market BUY 본 commit X (★ 후속)."""
    assert "alminus_market" not in SHOP_INVENTORY


def test_buy_multiplier_baseline() -> None:
    assert SHOP_BUY_MULTIPLIER["blacksmith"] == 1.0
    assert SHOP_BUY_MULTIPLIER["general_store"] == 1.0


# ─── 3. _get_shop_item ───


def test_get_shop_item_exact_match() -> None:
    item = _get_shop_item("blacksmith", "강철 검")
    assert item is not None
    assert item.name == "강철 검"


def test_get_shop_item_substring_match() -> None:
    """target '아머' → '하프 아머' (★ SHOP_SELL 정합)."""
    item = _get_shop_item("blacksmith", "아머")
    assert item is not None
    assert item.name == "하프 아머"


def test_get_shop_item_not_found() -> None:
    assert _get_shop_item("blacksmith", "전설의 검") is None


def test_get_shop_item_wrong_shop() -> None:
    """general_store 본격 강철 검 X."""
    assert _get_shop_item("general_store", "강철 검") is None


def test_get_shop_item_empty_target() -> None:
    assert _get_shop_item("blacksmith", None) is None
    assert _get_shop_item("blacksmith", "") is None


# ─── 4. execute_shop_buy handler ───


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


def _alminus_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="alminus_market",
        city_id="rascania",
    )


def _dungeon_loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


def _bjorn(stone: int = 500_000) -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        stone=stone,
    )


def test_buy_half_armor_21hwa() -> None:
    """21화 본문 정합 — 하프 아머 36만."""
    actor = _bjorn(stone=500_000)
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert result.success is True
    assert actor.stone == 500_000 - 360_000
    assert any(i.name == "하프 아머" for i in actor.inventory.items)
    item = next(i for i in actor.inventory.items if i.name == "하프 아머")
    assert item.category == ItemCategory.ARMOR


def test_buy_steel_sword_21hwa() -> None:
    actor = _bjorn(stone=300_000)
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "강철 검", [actor], world, _blacksmith_loc()
    )
    assert result.success is True
    assert actor.stone == 300_000 - 250_000


def test_buy_potion_at_general_store() -> None:
    actor = _bjorn(stone=20_000)
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "회복 포션", [actor], world, _general_loc()
    )
    assert result.success is True
    assert actor.stone == 20_000 - 10_000


def test_buy_insufficient_stone_atomic() -> None:
    """비용 부족 → fail + mutation X."""
    actor = _bjorn(stone=100)
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert result.success is False
    assert actor.stone == 100
    assert len(actor.inventory.items) == 0


def test_buy_outside_city_fails() -> None:
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _dungeon_loc()
    )
    assert result.success is False
    assert actor.stone == 500_000


def test_buy_at_alminus_fails() -> None:
    """alminus_market BUY 본 commit X."""
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _alminus_loc()
    )
    assert result.success is False
    assert actor.stone == 500_000


def test_buy_wrong_shop_for_item_fails() -> None:
    """general_store 본격 무기 X."""
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "강철 검", [actor], world, _general_loc()
    )
    assert result.success is False


def test_buy_unknown_item_fails() -> None:
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "전설의 검", [actor], world, _blacksmith_loc()
    )
    assert result.success is False


def test_buy_actor_not_in_party_fails() -> None:
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "투르윈", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert result.success is False


def test_buy_empty_target_fails() -> None:
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "", [actor], world, _blacksmith_loc()
    )
    assert result.success is False


def test_buy_substring_match_armor() -> None:
    """target '아머' → '하프 아머' (★ substring)."""
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "아머", [actor], world, _blacksmith_loc()
    )
    assert result.success is True
    assert any(i.name == "하프 아머" for i in actor.inventory.items)


def test_buy_side_effects() -> None:
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert any(
        s == "item_bought=비요른:하프 아머" for s in result.side_effects
    )
    assert any(
        s == "stone_paid=비요른:-360000" for s in result.side_effects
    )


def test_buy_message_shows_shop_name() -> None:
    actor = _bjorn()
    world = WorldState()
    result = execute_shop_buy(
        "비요른", "하프 아머", [actor], world, _blacksmith_loc()
    )
    assert "대장간" in result.message
    assert "구매" in result.message


# ─── 5. PlayerActionType ───


def test_shop_buy_enum_value() -> None:
    assert PlayerActionType.SHOP_BUY.value == "shop_buy"


# ─── 6. gm_agent prompt hint ───


def _ctx(sub_area: str) -> dict[str, Any]:
    return {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": sub_area,
            "city_id": "rascania",
        }
    }


def test_prompt_blacksmith_shows_catalog() -> None:
    out = _format_city_context(_ctx("blacksmith"))
    assert "SHOP_BUY" in out
    assert "하프 아머" in out
    assert "360,000" in out  # ★ 21화 정합


def test_prompt_blacksmith_shows_weapon() -> None:
    out = _format_city_context(_ctx("blacksmith"))
    assert "강철 검" in out
    assert "250,000" in out


def test_prompt_general_store_shows_catalog() -> None:
    out = _format_city_context(_ctx("general_store"))
    assert "SHOP_BUY" in out
    assert "회복 포션" in out


def test_prompt_alminus_no_buy_catalog() -> None:
    """alminus BUY 본 commit X — prompt 본격 catalog X."""
    out = _format_city_context(_ctx("alminus_market"))
    assert "SHOP_BUY" not in out
