"""Audit step 5 fix commit 2 — compute_damage_multiplier 단위 테스트."""

from __future__ import annotations

from service.sim.combat import compute_damage_multiplier
from service.sim.enemy import Enemy, EnemyType


def _make_enemy(
    enemy_type: EnemyType = EnemyType.PHYSICAL,
    weakness_types: list[str] | None = None,
) -> Enemy:
    return Enemy(
        name="테스트 몬스터",
        hp=100,
        max_hp=100,
        attack=10,
        defense=5,
        grade=9,
        race="test",
        abilities=[],
        weakness_races=[],
        weakness_types=weakness_types or [],
        essence_drop=None,
        is_hostile=True,
        enemy_type=enemy_type,
    )


# ── Fix 5: 영체류 물리 면역 ──


def test_spirit_immune_to_physical_only() -> None:
    enemy = _make_enemy(enemy_type=EnemyType.SPIRIT)
    assert compute_damage_multiplier(enemy, ["물리"]) == 0.0


def test_spirit_immune_to_default_elements() -> None:
    """attack_elements 미지정 시 물리 default → 면역."""
    enemy = _make_enemy(enemy_type=EnemyType.SPIRIT)
    assert compute_damage_multiplier(enemy, None) == 0.0


def test_spirit_takes_holy_damage() -> None:
    """영체류도 신성력 공격은 통과."""
    enemy = _make_enemy(enemy_type=EnemyType.SPIRIT)
    result = compute_damage_multiplier(enemy, ["신성력"])
    assert result > 0.0


def test_spirit_takes_mixed_elements() -> None:
    """물리 + 신성력 — 신성력 포함 시 면역 X."""
    enemy = _make_enemy(enemy_type=EnemyType.SPIRIT)
    result = compute_damage_multiplier(enemy, ["물리", "신성력"])
    assert result > 0.0


# ── Fix 4: weakness_types 약점 배율 ──


def test_undead_weakness_holy() -> None:
    enemy = _make_enemy(
        enemy_type=EnemyType.UNDEAD,
        weakness_types=["신성력", "불"],
    )
    assert compute_damage_multiplier(enemy, ["신성력"]) == 1.5


def test_undead_weakness_fire() -> None:
    enemy = _make_enemy(
        enemy_type=EnemyType.UNDEAD,
        weakness_types=["신성력", "불"],
    )
    assert compute_damage_multiplier(enemy, ["불"]) == 1.5


def test_cold_beast_weakness_electric() -> None:
    enemy = _make_enemy(
        enemy_type=EnemyType.COLD_BEAST,
        weakness_types=["전격"],
    )
    assert compute_damage_multiplier(enemy, ["전격"]) == 1.5


def test_dark_weakness_light() -> None:
    enemy = _make_enemy(
        enemy_type=EnemyType.DARK,
        weakness_types=["태양", "빛"],
    )
    assert compute_damage_multiplier(enemy, ["빛"]) == 1.5


def test_no_weakness_match_returns_1() -> None:
    enemy = _make_enemy(
        enemy_type=EnemyType.UNDEAD,
        weakness_types=["신성력"],
    )
    assert compute_damage_multiplier(enemy, ["물리"]) == 1.0


def test_physical_enemy_no_weakness_no_immunity() -> None:
    enemy = _make_enemy(enemy_type=EnemyType.PHYSICAL)
    assert compute_damage_multiplier(enemy, ["물리"]) == 1.0


def test_empty_weakness_types_returns_1() -> None:
    enemy = _make_enemy(enemy_type=EnemyType.PHYSICAL, weakness_types=[])
    assert compute_damage_multiplier(enemy, ["신성력"]) == 1.0
