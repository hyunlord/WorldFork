"""Phase D step 6b — canon mechanism → equipment ItemRegistry.

★ element/sensitivity 확장: 무기 element(13deef0 정합) + 감응도 소비 아이템(37d3c4f 정합).
별도 items entity 추출 X — mechanisms 파생 구조 유지 (중복/MbNU 회피).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from service.canon.schema import CanonFacts
from service.sim.equipment import Equipment, EquipmentSlot

WEAPON_KEYWORDS = (
    "검", "활", "단검", "도끼", "창", "쇠뇌", "장검", "단도", "철퇴", "대검", "쌍검", "칼날"
)
ARMOR_KEYWORDS = ("갑옷", "투구", "방패", "흉갑", "튜닉", "외투", "장갑", "신발", "방어구", "로브")
ACCESSORY_KEYWORDS = ("반지", "목걸이", "팔찌", "부적", "마석", "보석")

_STAT_PAT = re.compile(r"([가-힣]+)\s*\+\s*(\d+)")

# 무기 element keyword (★ 13deef0 _get_attack_elements vocabulary 정합, 오탐 차단)
_ELEMENT_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("성스러운", "신성", "성광"), "신성력"),
    (("화염", "불꽃", "용암", "작열"), "불"),
    (("전격", "번개", "뇌전", "낙뢰"), "전격"),
    (("태양", "빛", "광휘", "여명"), "빛"),
    (("서리", "얼음", "빙결", "냉기", "한기"), "냉기"),
)

# 감응도 element keyword (★ 37d3c4f sensitivity 정합 — 화염→불)
_SENS_ELEMENT_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("화염", "불"), ("불", "불"),
    ("냉기", "냉기"), ("서리", "냉기"), ("빙", "냉기"),
    ("전격", "전격"), ("번개", "전격"),
    ("신성", "신성력"),
    ("빛", "빛"), ("태양", "빛"),
    ("독", "독"),
)
# "X 감응도 ... +N" / "X 감응도가 +N" — element 감응도 상승 수치
_SENS_PAT = re.compile(r"감응도[가를을]?\s*(?:[^+\d]{0,12})?\+\s*(\d+)")


@dataclass
class SensitivityItem:
    """감응도 소비/획득 아이템 (★ 빙정 냉기+3 / 순수한 불꽃 불+15)."""

    name: str
    element: str
    bonus: int
    source: str = ""  # mechanism 출처 명칭


def _parse_element(name: str, description: str) -> str:
    """무기/장비 element 파싱 (★ name + description, 13deef0 vocabulary)."""
    text = f"{name} {description}"
    for keywords, element in _ELEMENT_KEYWORDS:
        if any(kw in text for kw in keywords):
            return element
    return ""


def _parse_sensitivity_item(name: str, description: str) -> SensitivityItem | None:
    """감응도 상승 아이템 파싱 — "X 감응도 +N" → (element, bonus).

    description에 '감응도' + 상승 수치(+N) + element keyword가 있어야 성립.
    """
    if "감응도" not in description:
        return None
    m = _SENS_PAT.search(description)
    if not m:
        return None
    bonus = int(m.group(1))
    # 감응도 앞쪽 element keyword 탐색 (★ 화염/냉기 등)
    head = description[: description.find("감응도")]
    element = ""
    for kw, el in _SENS_ELEMENT_KEYWORDS:
        if kw in head:
            element = el
            break
    if not element:
        return None
    return SensitivityItem(name=name, element=element, bonus=bonus, source=name)


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
        self._sensitivity_items: dict[str, SensitivityItem] = {}
        self._build(facts)

    def _build(self, facts: CanonFacts) -> None:
        for m in facts.mechanisms:
            desc = m.description or ""
            # 감응도 소비/획득 아이템 (★ slot 무관 — 빙정/순수한 불꽃)
            sens = _parse_sensitivity_item(m.name, desc)
            if sens is not None:
                self._sensitivity_items[m.name] = sens

            slot = classify_item_slot(m.name)
            if slot is None:
                continue
            attack, defense, agility = _parse_item_stats(desc, slot)
            self._items[m.name] = Equipment(
                name=m.name,
                slot=slot,
                attack_bonus=attack,
                defense_bonus=defense,
                agility_bonus=agility,
                abilities=list(m.rules),
                element=_parse_element(m.name, desc),
            )

    def lookup(self, name: str) -> Equipment | None:
        return self._items.get(name)

    def all_items(self) -> list[Equipment]:
        return list(self._items.values())

    def lookup_sensitivity_item(self, name: str) -> SensitivityItem | None:
        return self._sensitivity_items.get(name)

    def sensitivity_items(self) -> list[SensitivityItem]:
        return list(self._sensitivity_items.values())

    def size(self) -> int:
        return len(self._items)
