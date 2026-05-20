"""Phase D step 6b — ItemRegistry + classify_item_slot tests."""

from __future__ import annotations

from service.canon.items import ItemRegistry, _parse_item_stats, classify_item_slot
from service.canon.schema import CanonFacts, Mechanism
from service.sim.equipment import EquipmentSlot


def _facts_with_mechanisms(items: list[dict[str, object]]) -> CanonFacts:
    mechs = [
        Mechanism(
            name=str(m["name"]),
            category="combat",  # type: ignore[arg-type]
            description=str(m.get("description", "")),
            rules=[],
        )
        for m in items
    ]
    return CanonFacts(
        essences=[],
        characters=[],
        locations=[],
        races=[],
        mechanisms=mechs,
    )


def test_classify_weapon_keyword() -> None:
    assert classify_item_slot("철검") == EquipmentSlot.WEAPON
    assert classify_item_slot("단도") == EquipmentSlot.WEAPON
    assert classify_item_slot("대검") == EquipmentSlot.WEAPON


def test_classify_armor_keyword() -> None:
    assert classify_item_slot("가죽갑옷") == EquipmentSlot.ARMOR
    assert classify_item_slot("방패") == EquipmentSlot.ARMOR
    assert classify_item_slot("투구") == EquipmentSlot.ARMOR


def test_classify_accessory_keyword() -> None:
    assert classify_item_slot("마석 반지") == EquipmentSlot.ACCESSORY
    assert classify_item_slot("부적") == EquipmentSlot.ACCESSORY


def test_classify_unknown() -> None:
    assert classify_item_slot("미지의 물건") is None


def test_parse_item_stats_weapon_fallback() -> None:
    attack, defense, agility = _parse_item_stats("", EquipmentSlot.WEAPON)
    assert attack == 5
    assert defense == 0
    assert agility == 0


def test_parse_item_stats_armor_fallback() -> None:
    attack, defense, agility = _parse_item_stats("", EquipmentSlot.ARMOR)
    assert attack == 0
    assert defense == 5
    assert agility == 0


def test_parse_item_stats_accessory_fallback() -> None:
    attack, defense, agility = _parse_item_stats("", EquipmentSlot.ACCESSORY)
    assert agility == 2


def test_item_registry_builds() -> None:
    facts = _facts_with_mechanisms([
        {"name": "철검", "category": "combat"},
        {"name": "방패", "category": "combat"},
        {"name": "반지", "category": "magic"},
        {"name": "잡동사니", "category": "misc"},
    ])
    registry = ItemRegistry(facts)
    assert registry.size() == 3


def test_item_registry_lookup_weapon() -> None:
    facts = _facts_with_mechanisms([
        {"name": "장검", "category": "combat", "description": ""},
    ])
    registry = ItemRegistry(facts)
    eq = registry.lookup("장검")
    assert eq is not None
    assert eq.slot == EquipmentSlot.WEAPON
    assert eq.attack_bonus == 5  # fallback


def test_item_registry_lookup_missing() -> None:
    facts = _facts_with_mechanisms([])
    registry = ItemRegistry(facts)
    assert registry.lookup("없는아이템") is None


def test_item_registry_all_items() -> None:
    facts = _facts_with_mechanisms([
        {"name": "단검", "category": "combat"},
        {"name": "투구", "category": "combat"},
    ])
    registry = ItemRegistry(facts)
    items = registry.all_items()
    assert len(items) == 2
    names = {i.name for i in items}
    assert "단검" in names
    assert "투구" in names
