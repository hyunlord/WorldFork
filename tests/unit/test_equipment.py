"""Phase D step 6b — Equipment schema + EquipmentSet tests."""

from __future__ import annotations

from service.sim.equipment import (
    Equipment,
    EquipmentSet,
    EquipmentSlot,
    equipment_from_dict,
    equipment_set_from_dict,
    equipment_to_dict,
)


def _weapon(attack: int = 5) -> Equipment:
    return Equipment(name="철검", slot=EquipmentSlot.WEAPON, attack_bonus=attack)


def _armor(defense: int = 5) -> Equipment:
    return Equipment(name="가죽갑옷", slot=EquipmentSlot.ARMOR, defense_bonus=defense)


def _accessory(agility: int = 2) -> Equipment:
    return Equipment(name="민첩 반지", slot=EquipmentSlot.ACCESSORY, agility_bonus=agility)


def test_equipment_set_total_attack() -> None:
    eq_set = EquipmentSet(weapon=_weapon(8), armor=_armor(0), accessory=_accessory(0))
    assert eq_set.total_attack_bonus() == 8


def test_equipment_set_total_defense() -> None:
    eq_set = EquipmentSet(weapon=_weapon(0), armor=_armor(6))
    assert eq_set.total_defense_bonus() == 6


def test_equipment_set_total_agility() -> None:
    eq_set = EquipmentSet(accessory=_accessory(3))
    assert eq_set.total_agility_bonus() == 3


def test_equipment_set_combined() -> None:
    eq_set = EquipmentSet(weapon=_weapon(5), armor=_armor(3), accessory=_accessory(2))
    assert eq_set.total_attack_bonus() == 5
    assert eq_set.total_defense_bonus() == 3
    assert eq_set.total_agility_bonus() == 2


def test_equipment_set_empty() -> None:
    eq_set = EquipmentSet()
    assert eq_set.total_attack_bonus() == 0
    assert eq_set.total_defense_bonus() == 0
    assert eq_set.total_agility_bonus() == 0


def test_equipment_round_trip() -> None:
    eq = Equipment(
        name="마법검",
        slot=EquipmentSlot.WEAPON,
        attack_bonus=10,
        defense_bonus=2,
        agility_bonus=1,
        abilities=["불꽃 날 (A)"],
    )
    d = equipment_to_dict(eq)
    eq2 = equipment_from_dict(d)
    assert eq2.name == eq.name
    assert eq2.slot == EquipmentSlot.WEAPON
    assert eq2.attack_bonus == 10
    assert eq2.defense_bonus == 2
    assert eq2.agility_bonus == 1
    assert eq2.abilities == ["불꽃 날 (A)"]


def test_equipment_from_dict_defaults() -> None:
    d: dict[str, object] = {"name": "단검", "slot": "weapon"}
    eq = equipment_from_dict(d)
    assert eq.attack_bonus == 0
    assert eq.defense_bonus == 0
    assert eq.agility_bonus == 0
    assert eq.abilities == []


def test_equipment_set_from_dict_none_slots() -> None:
    d: dict[str, object] = {"weapon": None, "armor": None, "accessory": None}
    eq_set = equipment_set_from_dict(d)
    assert eq_set.weapon is None
    assert eq_set.armor is None
    assert eq_set.accessory is None
    assert eq_set.total_attack_bonus() == 0


def test_equipment_set_from_dict_partial() -> None:
    weapon_dict: dict[str, object] = {
        "name": "대검", "slot": "weapon", "attack_bonus": 12,
        "defense_bonus": 0, "agility_bonus": 0, "abilities": [],
    }
    d: dict[str, object] = {"weapon": weapon_dict, "armor": None, "accessory": None}
    eq_set = equipment_set_from_dict(d)
    assert eq_set.weapon is not None
    assert eq_set.weapon.attack_bonus == 12
    assert eq_set.armor is None
