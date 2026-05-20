"""Phase D step 6b — enemy_ai ability selection tests."""

from __future__ import annotations

from service.sim.enemy import Enemy
from service.sim.enemy_ai import plan_enemy_turn, select_ability


def _enemy(
    hp: int,
    max_hp: int,
    abilities: list[str] | None = None,
    attack: int = 8,
) -> Enemy:
    return Enemy(
        name="테스트 몬스터",
        hp=hp,
        max_hp=max_hp,
        attack=attack,
        defense=3,
        abilities=abilities or [],
    )


def test_select_ability_default_first() -> None:
    e = _enemy(hp=80, max_hp=100, abilities=["기본 공격", "강타", "회복"])
    assert select_ability(e) == "기본 공격"


def test_select_ability_below_50_last() -> None:
    e = _enemy(hp=40, max_hp=100, abilities=["기본 공격", "강타", "특수기"])
    assert select_ability(e) == "특수기"


def test_select_ability_below_30_defensive() -> None:
    e = _enemy(hp=25, max_hp=100, abilities=["기본 공격", "방어 태세 (P)", "회복"])
    result = select_ability(e)
    assert result in ("방어 태세 (P)", "회복")


def test_select_ability_below_30_no_defensive_fallback() -> None:
    e = _enemy(hp=20, max_hp=100, abilities=["기본 공격", "강타"])
    assert select_ability(e) == "기본 공격"


def test_select_ability_no_abilities() -> None:
    e = _enemy(hp=50, max_hp=100, abilities=[])
    assert select_ability(e) == "기본 공격"


def test_select_ability_single() -> None:
    e = _enemy(hp=10, max_hp=100, abilities=["독화살"])
    assert select_ability(e) == "독화살"


def test_plan_enemy_turn_basic() -> None:
    e = _enemy(hp=50, max_hp=100, abilities=["공격"])
    actions = plan_enemy_turn([e])
    assert len(actions) == 1
    assert actions[0].enemy_name == "테스트 몬스터"
    assert actions[0].target == "player"


def test_plan_enemy_turn_skips_dead() -> None:
    alive = _enemy(hp=30, max_hp=100, abilities=["공격"])
    dead = Enemy(name="죽은 몬스터", hp=0, max_hp=50, attack=5, defense=2)
    actions = plan_enemy_turn([alive, dead])
    assert len(actions) == 1
    assert actions[0].enemy_name == alive.name


def test_plan_enemy_turn_empty() -> None:
    assert plan_enemy_turn([]) == []
