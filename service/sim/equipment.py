"""Phase D step 6b — Equipment slot schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EquipmentSlot(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"


@dataclass
class Equipment:
    name: str
    slot: EquipmentSlot
    attack_bonus: int = 0
    defense_bonus: int = 0
    agility_bonus: int = 0
    abilities: list[str] = field(default_factory=list)
    element: str = ""  # ★ 무기 속성 (불/냉기/전격/신성력/빛 — combat 약점 정합)


@dataclass
class EquipmentSet:
    weapon: Equipment | None = None
    armor: Equipment | None = None
    accessory: Equipment | None = None

    def total_attack_bonus(self) -> int:
        pieces = [self.weapon, self.armor, self.accessory]
        return sum(e.attack_bonus for e in pieces if e is not None)

    def total_defense_bonus(self) -> int:
        pieces = [self.weapon, self.armor, self.accessory]
        return sum(e.defense_bonus for e in pieces if e is not None)

    def total_agility_bonus(self) -> int:
        pieces = [self.weapon, self.armor, self.accessory]
        return sum(e.agility_bonus for e in pieces if e is not None)


def equipment_to_dict(e: Equipment) -> dict[str, object]:
    return {
        "name": e.name,
        "slot": e.slot.value,
        "attack_bonus": e.attack_bonus,
        "defense_bonus": e.defense_bonus,
        "agility_bonus": e.agility_bonus,
        "abilities": list(e.abilities),
        "element": e.element,
    }


def _to_int(val: object, default: int = 0) -> int:
    if isinstance(val, (int, float)):
        return int(val)
    return default


def equipment_from_dict(d: dict[str, object]) -> Equipment:
    name = str(d.get("name", ""))
    slot_val = str(d.get("slot", EquipmentSlot.WEAPON.value))
    attack = _to_int(d.get("attack_bonus"))
    defense = _to_int(d.get("defense_bonus"))
    agility = _to_int(d.get("agility_bonus"))
    abilities_raw = d.get("abilities", [])
    abilities = [str(a) for a in abilities_raw] if isinstance(abilities_raw, list) else []
    element = str(d.get("element", ""))
    return Equipment(
        name=name,
        slot=EquipmentSlot(slot_val),
        attack_bonus=attack,
        defense_bonus=defense,
        agility_bonus=agility,
        abilities=abilities,
        element=element,
    )


def _as_str_obj_dict(val: object) -> dict[str, object] | None:
    if isinstance(val, dict):
        return {str(k): v for k, v in val.items()}
    return None


def equipment_set_from_dict(d: dict[str, object]) -> EquipmentSet:
    """session state의 equipment dict → EquipmentSet."""
    weapon_d = _as_str_obj_dict(d.get("weapon"))
    armor_d = _as_str_obj_dict(d.get("armor"))
    accessory_d = _as_str_obj_dict(d.get("accessory"))
    return EquipmentSet(
        weapon=equipment_from_dict(weapon_d) if weapon_d is not None else None,
        armor=equipment_from_dict(armor_d) if armor_d is not None else None,
        accessory=equipment_from_dict(accessory_d) if accessory_d is not None else None,
    )


DEFAULT_EQUIPMENT_DICT: dict[str, object] = {
    "weapon": None,
    "armor": None,
    "accessory": None,
}
