"""Phase D step 6a — Enemy serialize / deserialize tests."""

from __future__ import annotations

from service.sim.enemy import Enemy, enemy_from_dict, enemy_to_dict


def _base() -> Enemy:
    return Enemy(
        name="고블린",
        hp=20,
        max_hp=30,
        attack=8,
        defense=3,
        grade=1,
        race="고블린",
        abilities=["집착 (P)"],
        weakness_races=["인간"],
        weakness_types=["불"],
        essence_drop="고블린 정수",
        is_hostile=True,
    )


def test_round_trip_full() -> None:
    e = _base()
    d = enemy_to_dict(e)
    e2 = enemy_from_dict(d)
    assert e2.name == e.name
    assert e2.hp == e.hp
    assert e2.max_hp == e.max_hp
    assert e2.attack == e.attack
    assert e2.defense == e.defense
    assert e2.grade == e.grade
    assert e2.race == e.race
    assert e2.abilities == e.abilities
    assert e2.weakness_races == e.weakness_races
    assert e2.weakness_types == e.weakness_types
    assert e2.essence_drop == e.essence_drop
    assert e2.is_hostile == e.is_hostile


def test_to_dict_hostile_key() -> None:
    """get_first_enemy 호환 - 'hostile' 키 보장."""
    d = enemy_to_dict(_base())
    assert d["hostile"] is True
    assert d["is_hostile"] is True


def test_from_dict_defaults() -> None:
    """최소 dict에서 기본값 적용."""
    d: dict[str, object] = {"name": "슬라임"}
    e = enemy_from_dict(d)
    assert e.name == "슬라임"
    assert e.hp == 30
    assert e.max_hp == 30
    assert e.attack == 8
    assert e.defense == 3
    assert e.grade is None
    assert e.race is None
    assert e.abilities == []
    assert e.essence_drop is None
    assert e.is_hostile is True


def test_from_dict_grade_none() -> None:
    d: dict[str, object] = {"name": "보스", "grade": None, "hp": 100, "max_hp": 100,
                            "attack": 20, "defense": 10}
    e = enemy_from_dict(d)
    assert e.grade is None


def test_from_dict_not_hostile() -> None:
    d: dict[str, object] = {"name": "NPC", "is_hostile": False}
    e = enemy_from_dict(d)
    assert e.is_hostile is False


def test_hp_mutation_preserved() -> None:
    """HP 감소 후 re-serialize 시 유지."""
    e = _base()
    e.hp = 10
    d = enemy_to_dict(e)
    e2 = enemy_from_dict(d)
    assert e2.hp == 10
    assert e2.max_hp == 30


def test_essence_drop_none_round_trip() -> None:
    e = Enemy(name="슬라임", hp=10, max_hp=10, attack=3, defense=1)
    d = enemy_to_dict(e)
    e2 = enemy_from_dict(d)
    assert e2.essence_drop is None
