"""inventory 무기 판정 helper."""
from __future__ import annotations

WEAPON_KEYWORDS: frozenset[str] = frozenset([
    "도끼", "검", "방패", "망치", "단검", "곤봉",
    "활", "지팡이", "창",
])


def is_unarmed(inventory: list[str]) -> bool:
    """inventory에 무기가 없으면 True.

    - [] → True (수인 default)
    - ["도끼"] → False
    - ["횃불"] → True (비무기 only)
    """
    for item in inventory:
        for kw in WEAPON_KEYWORDS:
            if kw in item:
                return False
    return True
