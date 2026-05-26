"""종족 effect fields + helper 함수 unit tests."""
from __future__ import annotations

from service.canon.races import (
    Race,
    get_dodge_chance,
    get_unarmed_bonus,
    get_xp_multiplier,
)


def test_human_xp_multiplier_1_1() -> None:
    """인간 — 정수 흡수 XP × 1.1."""
    assert get_xp_multiplier(Race.HUMAN) == 1.1


def test_dwarf_dodge_5pct() -> None:
    """드워프 — 회피 +5%."""
    assert get_dodge_chance(Race.DWARF) == 5


def test_fairy_dodge_10pct() -> None:
    """요정 — 회피 +10%."""
    assert get_dodge_chance(Race.FAIRY) == 10


def test_beastkin_unarmed_3() -> None:
    """수인 — 비무장 공격 +3."""
    assert get_unarmed_bonus(Race.BEASTKIN) == 3


def test_other_races_no_dodge() -> None:
    """바바리안 / 인간 / 수인 — 회피 0."""
    assert get_dodge_chance(Race.BARBARIAN) == 0
    assert get_dodge_chance(Race.HUMAN) == 0
    assert get_dodge_chance(Race.BEASTKIN) == 0


def test_other_races_no_unarmed_bonus() -> None:
    """수인 외 비무장 보너스 0."""
    assert get_unarmed_bonus(Race.BARBARIAN) == 0
    assert get_unarmed_bonus(Race.HUMAN) == 0
    assert get_unarmed_bonus(Race.DWARF) == 0
    assert get_unarmed_bonus(Race.FAIRY) == 0


def test_other_races_xp_default_1() -> None:
    """인간 외 XP multiplier 1.0."""
    for race in [Race.BARBARIAN, Race.DWARF, Race.BEASTKIN, Race.FAIRY]:
        assert get_xp_multiplier(race) == 1.0
