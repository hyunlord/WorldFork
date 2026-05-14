"""Phase 8 (c) — USE_ITEM effect minimal unit 본격.

검증 본질 (★ docs/FLOOR1_COMPLETION_REVIEW.md §2-2 (c) 본격 해결):
- use_item no-op stub → 실작동 minimal
- Scope:
  * 포션 → HP +50 (hp_max cap)
  * 식량 → message only (★ 후속 hunger field 본격)
  * 횃불 → message only (★ 후속 visibility field 본격)
  * unknown → message only
  * 1회 사용 → inventory 본격 remove

본문 정합:
- 26화 mention '거동까지 몇 분' — 본 commit 즉시 회복 (★ 게임성 채택)
- 본문 시작값 X — POTION_HEAL_AMOUNT=50 추측 (★ hp_max 본격 50%)

race-starting 식량 enabler:
- 8f8dbcf '부족장의 일주일 식량' Item.grade=None
- 본 commit USE_ITEM 본격 message만 → effect X
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Item,
    ItemCategory,
    Race,
)
from service.game.turn_handler_v2 import (
    POTION_HEAL_AMOUNT,
    _item_use_category,
    use_item,
)

# ─── 1. _item_use_category 본격 substring 분류 ───


def _make_item(name: str, grade: int | None = None) -> Item:
    return Item(
        name=name,
        category=ItemCategory.CONSUMABLE,
        weight=1,
        grade=grade,
    )


def test_category_potion() -> None:
    assert _item_use_category(_make_item("회복 포션")) == "potion"


def test_category_food() -> None:
    """race-starting 식량 본격 본격 (★ 8f8dbcf)."""
    assert (
        _item_use_category(_make_item("부족장의 일주일 식량")) == "food"
    )


def test_category_torch() -> None:
    assert _item_use_category(_make_item("횃불")) == "torch"


def test_category_unknown_for_mage_stone() -> None:
    """마석 (grade != None)은 use_item 본격 unknown (★ EXCHANGE 본격 본격)."""
    assert _item_use_category(_make_item("9등급 마석", grade=9)) == "unknown"


# ─── 2. Potion effect ───


def _bjorn_with_items(hp: int, *items: Item) -> Character:
    c = Character(
        name="비요른", race=Race.BARBARIAN, hp=hp, hp_max=100
    )
    for it in items:
        c.inventory.items.append(it)
    return c


def test_potion_heals_50() -> None:
    """포션 본격 +50 HP (★ hp_max cap 본격 본격)."""
    c = _bjorn_with_items(50, _make_item("회복 포션"))
    result = use_item(c, "회복 포션")
    assert result.success is True
    assert c.hp == 100
    assert "+50" in result.message


def test_potion_caps_at_hp_max() -> None:
    """hp 90 + 포션 50 → 100 cap (★ +10만)."""
    c = _bjorn_with_items(90, _make_item("회복 포션"))
    result = use_item(c, "회복 포션")
    assert result.success is True
    assert c.hp == 100
    # 메시지 본격 본격 +10 (★ cap 본격 actual healed)
    assert "+10" in result.message


def test_potion_constant_is_50() -> None:
    """POTION_HEAL_AMOUNT = 50 (★ 본문 X 추측, hp_max 50%)."""
    assert POTION_HEAL_AMOUNT == 50


def test_potion_removed_from_inventory() -> None:
    """1회 사용 → inventory 본격 제거."""
    c = _bjorn_with_items(50, _make_item("회복 포션"))
    use_item(c, "회복 포션")
    assert len(c.inventory.items) == 0


# ─── 3. Food effect (★ race-starting 식량 본격) ───


def test_food_message_no_hp_change() -> None:
    """식량 본격 message만 (★ 본 commit 본격 hunger field 본격 X)."""
    c = _bjorn_with_items(80, _make_item("부족장의 일주일 식량"))
    result = use_item(c, "부족장의 일주일 식량")
    assert result.success is True
    assert c.hp == 80  # 변화 X
    assert "든든" in result.message


def test_food_removed_from_inventory() -> None:
    c = _bjorn_with_items(80, _make_item("부족장의 일주일 식량"))
    use_item(c, "부족장의 일주일 식량")
    assert len(c.inventory.items) == 0


def test_food_substring_target_match() -> None:
    """target substring 본격 본격 — '식량' 본격 본격 본격 match."""
    c = _bjorn_with_items(80, _make_item("부족장의 일주일 식량"))
    result = use_item(c, "식량")
    assert result.success is True
    assert "든든" in result.message


# ─── 4. Torch effect ───


def test_torch_message_only() -> None:
    c = _bjorn_with_items(100, _make_item("횃불"))
    result = use_item(c, "횃불")
    assert result.success is True
    assert "밝아" in result.message
    assert len(c.inventory.items) == 0


# ─── 5. Edge cases ───


def test_empty_inventory_fails() -> None:
    c = _bjorn_with_items(50)  # no items
    result = use_item(c, "포션")
    assert result.success is False
    assert "아이템 X" in result.message


def test_item_not_found_fails() -> None:
    c = _bjorn_with_items(50, _make_item("횃불"))
    result = use_item(c, "포션")
    assert result.success is False
    assert "X" in result.message
    # 잘못된 호출은 inventory 본격 변경 X
    assert len(c.inventory.items) == 1


def test_unknown_item_uses_fallback_message() -> None:
    """grade=9 마석 본격 unknown — fallback message + 본격 본격 remove."""
    c = _bjorn_with_items(100, _make_item("9등급 마석", grade=9))
    result = use_item(c, "9등급 마석")
    assert result.success is True
    assert "미정" in result.message
    assert len(c.inventory.items) == 0


# ─── 6. Side effects markers ───


def test_potion_emits_hp_gain_and_item_used() -> None:
    c = _bjorn_with_items(50, _make_item("회복 포션"))
    result = use_item(c, "회복 포션")
    assert any(
        se == "hp_gain=비요른:+50" for se in result.side_effects
    )
    assert any(
        se == "item_used=비요른:회복 포션"
        for se in result.side_effects
    )


def test_food_emits_item_used_only_no_hp_gain() -> None:
    c = _bjorn_with_items(80, _make_item("부족장의 일주일 식량"))
    result = use_item(c, "부족장의 일주일 식량")
    assert not any("hp_gain=" in se for se in result.side_effects)
    assert any("item_used=비요른:" in se for se in result.side_effects)


# ─── 7. Race-starting 식량 production caller 본격 wire ───


def test_race_starting_barbarian_food_usable() -> None:
    """plan_character_to_v2 본격 바바리안 → 식량 inventory → use_item 본격 message."""
    from service.game.init_from_plan import plan_character_to_v2
    from service.pipeline.types import CharacterPlan

    plan = CharacterPlan(
        name="투르윈", role="주인공 바바리안", description="..."
    )
    char = plan_character_to_v2(plan)
    assert char.race == Race.BARBARIAN
    assert len(char.inventory.items) >= 1

    food = char.inventory.items[0]
    result = use_item(char, food.name)
    assert result.success is True
    assert "든든" in result.message
    assert len(char.inventory.items) == 0  # ★ 본격 1회 사용
