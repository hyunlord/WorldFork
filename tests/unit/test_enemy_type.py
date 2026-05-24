"""Audit step 5 fix commit 2 — EnemyType enum + infer_enemy_type 단위 테스트."""

from __future__ import annotations

import pytest

from service.sim.enemy import WEAKNESS_BY_TYPE, EnemyType, infer_enemy_type

# ── infer_enemy_type ──


@pytest.mark.parametrize(
    "race,expected",
    [
        ("구울", EnemyType.UNDEAD),
        ("스켈레톤", EnemyType.UNDEAD),
        ("뱀파이어", EnemyType.UNDEAD),
        ("유령", EnemyType.SPIRIT),
        ("레이스", EnemyType.SPIRIT),
        ("예티", EnemyType.COLD_BEAST),
        ("서리", EnemyType.COLD_BEAST),
        ("바포메트", EnemyType.PSIONIC),
        ("고블린", EnemyType.PHYSICAL),  # race에 없으면 name fallback or PHYSICAL
    ],
)
def test_infer_enemy_type_from_race(race: str, expected: EnemyType) -> None:
    assert infer_enemy_type(race=race) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("스켈레톤 아처", EnemyType.UNDEAD),
        ("구울로드", EnemyType.UNDEAD),
        ("데드맨", EnemyType.UNDEAD),
        ("본 나이트", EnemyType.UNDEAD),
        ("스컬 랫", EnemyType.UNDEAD),
        ("벤시 퀸", EnemyType.SPIRIT),
        ("서리 늑대", EnemyType.COLD_BEAST),
        ("그림자 사자", EnemyType.DARK),
        ("이름 모를 적", EnemyType.PHYSICAL),  # 미매칭 → default
    ],
)
def test_infer_enemy_type_from_name(name: str, expected: EnemyType) -> None:
    assert infer_enemy_type(name=name) == expected


def test_infer_enemy_type_race_takes_priority() -> None:
    """race 매칭이 name keyword보다 우선."""
    result = infer_enemy_type(race="구울", name="이름 모를 적")
    assert result == EnemyType.UNDEAD


def test_infer_enemy_type_default_physical() -> None:
    assert infer_enemy_type() == EnemyType.PHYSICAL
    assert infer_enemy_type(race=None, name=None) == EnemyType.PHYSICAL


# ── WEAKNESS_BY_TYPE ──


def test_undead_weakness_types() -> None:
    weak = WEAKNESS_BY_TYPE[EnemyType.UNDEAD]
    assert "신성력" in weak
    assert "불" in weak


def test_cold_beast_weakness_types() -> None:
    assert "전격" in WEAKNESS_BY_TYPE[EnemyType.COLD_BEAST]


def test_dark_weakness_types() -> None:
    weak = WEAKNESS_BY_TYPE[EnemyType.DARK]
    assert "태양" in weak
    assert "빛" in weak


def test_spirit_no_weakness_types() -> None:
    assert WEAKNESS_BY_TYPE[EnemyType.SPIRIT] == []


def test_physical_no_weakness_types() -> None:
    assert WEAKNESS_BY_TYPE[EnemyType.PHYSICAL] == []


# ── EnemyType value ──


def test_enemy_type_str_values() -> None:
    assert EnemyType.SPIRIT.value == "spirit"
    assert EnemyType.UNDEAD.value == "undead"
    assert EnemyType.PHYSICAL.value == "physical"
