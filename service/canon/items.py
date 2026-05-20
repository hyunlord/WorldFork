"""Phase D step 6b — canon mechanism → equipment ItemRegistry."""

from __future__ import annotations

import re

from service.canon.schema import CanonFacts
from service.sim.equipment import Equipment, EquipmentSlot

WEAPON_KEYWORDS = (
    "검", "활", "단검", "도끼", "창", "쇠뇌", "장검", "단도", "철퇴", "대검", "쌍검", "칼날"
)
ARMOR_KEYWORDS = ("갑옷", "투구", "방패", "흉갑", "튜닉", "외투", "장갑", "신발", "방어구", "로브")
ACCESSORY_KEYWORDS = ("반지", "목걸이", "팔찌", "부적", "마석", "보석")

_STAT_PAT = re.compile(r"([가-힣]+)\s*\+\s*(\d+)")


def classify_item_slot(name: str) -> EquipmentSlot | None:
    for kw in WEAPON_KEYWORDS:
        if kw in name:
            return EquipmentSlot.WEAPON
    for kw in ARMOR_KEYWORDS:
        if kw in name:
            return EquipmentSlot.ARMOR
    for kw in ACCESSORY_KEYWORDS:
        if kw in name:
            return EquipmentSlot.ACCESSORY
    return None


def _parse_item_stats(description: str, slot: EquipmentSlot) -> tuple[int, int, int]:
    """description 텍스트에서 +N 수치를 추출. 없으면 slot 기본값 적용."""
    attack, defense, agility = 0, 0, 0
    for m in _STAT_PAT.finditer(description or ""):
        kw, num = m.group(1), int(m.group(2))
        if "공격" in kw or "근력" in kw:
            attack += num
        elif "방어" in kw or "체력" in kw:
            defense += num
        elif "민첩" in kw or "감각" in kw:
            agility += num

    if attack == 0 and defense == 0 and agility == 0:
        if slot == EquipmentSlot.WEAPON:
            attack = 5
        elif slot == EquipmentSlot.ARMOR:
            defense = 5
        elif slot == EquipmentSlot.ACCESSORY:
            agility = 2

    return attack, defense, agility


class ItemRegistry:
    """canon mechanism에서 weapon/armor/accessory 추출."""

    def __init__(self, facts: CanonFacts) -> None:
        self._items: dict[str, Equipment] = {}
        self._build(facts)

    def _build(self, facts: CanonFacts) -> None:
        for m in facts.mechanisms:
            slot = classify_item_slot(m.name)
            if slot is None:
                continue
            attack, defense, agility = _parse_item_stats(m.description, slot)
            self._items[m.name] = Equipment(
                name=m.name,
                slot=slot,
                attack_bonus=attack,
                defense_bonus=defense,
                agility_bonus=agility,
                abilities=list(m.rules),
            )

    def lookup(self, name: str) -> Equipment | None:
        return self._items.get(name)

    def all_items(self) -> list[Equipment]:
        return list(self._items.values())

    def size(self) -> int:
        return len(self._items)
