"""I-G1 combat resistance 감산 단위 테스트."""

from __future__ import annotations

from service.canon.effects import (
    ENEMY_ELEMENT_MAP,
    apply_resistance,
    get_enemy_attack_element,
)


def test_enemy_element_mapping() -> None:
    assert get_enemy_attack_element("cold_beast") == "냉기"
    assert get_enemy_attack_element("psionic") == "정신"
    assert get_enemy_attack_element("spirit") == "정신"
    assert get_enemy_attack_element("physical") == "물리"
    assert get_enemy_attack_element("undead") == "물리"
    assert get_enemy_attack_element("dark") == "정신"


def test_enemy_element_case_insensitive() -> None:
    """대문자/공백 정규화."""
    assert get_enemy_attack_element("COLD_BEAST") == "냉기"
    assert get_enemy_attack_element(" cold_beast ") == "냉기"


def test_enemy_element_default() -> None:
    """unknown EnemyType → 물리 default."""
    assert get_enemy_attack_element("unknown") == "물리"
    assert get_enemy_attack_element("") == "물리"


def test_all_mapped_elements_are_valid_resistance_keys() -> None:
    """ENEMY_ELEMENT_MAP element는 resistance keyword 정합."""
    valid = {"독", "냉기", "화염", "고통", "정신", "물리", "대지", "산성", "기타"}
    for element in ENEMY_ELEMENT_MAP.values():
        assert element in valid, f"invalid element: {element}"


def test_apply_resistance_basic() -> None:
    """flat 감산 — damage 10 - 냉기 3 = 7."""
    final, reduced = apply_resistance(10, "냉기", {"냉기": 3})
    assert final == 7
    assert reduced == 3


def test_apply_resistance_no_match() -> None:
    """저항 element 불일치 — 감산 X."""
    final, reduced = apply_resistance(10, "화염", {"냉기": 3})
    assert final == 10
    assert reduced == 0


def test_apply_resistance_min_one() -> None:
    """저항 ≥ damage — 최소 1 보장."""
    final, reduced = apply_resistance(3, "냉기", {"냉기": 10})
    assert final == 1
    assert reduced == 2  # 3 - 1


def test_apply_resistance_exact() -> None:
    """damage == 저항 → 최소 1."""
    final, reduced = apply_resistance(5, "독", {"독": 5})
    assert final == 1
    assert reduced == 4


def test_apply_resistance_zero_damage() -> None:
    final, reduced = apply_resistance(0, "냉기", {"냉기": 3})
    assert final == 0
    assert reduced == 0


def test_apply_resistance_empty_dict() -> None:
    final, reduced = apply_resistance(10, "냉기", {})
    assert final == 10
    assert reduced == 0
