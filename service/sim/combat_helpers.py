"""Race combat effect helpers."""
from __future__ import annotations

import random

from service.canon.races import Race, get_dodge_chance


def apply_race_dodge(race: Race, incoming_damage: int) -> tuple[int, bool]:
    """race 회피 확률 정합.

    return: (final_damage, dodged)
    - dodged=True 시 damage=0, 회피 성공
    """
    dodge_pct = get_dodge_chance(race)
    if dodge_pct <= 0:
        return incoming_damage, False
    if random.random() * 100 < dodge_pct:
        return 0, True
    return incoming_damage, False
