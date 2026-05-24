"""Audit step 5 fix commit 2 — spawn 시 enemy_type 자동 주입 검증."""

from __future__ import annotations

from service.canon.spawn import _monster_name_to_enemy  # noqa: PLC2701
from service.sim.enemy import EnemyType

# ── _monster_name_to_enemy — enemy_type 주입 ──


def test_spawn_undead_from_name_goul() -> None:
    e = _monster_name_to_enemy("구울")
    assert e.enemy_type == EnemyType.UNDEAD


def test_spawn_undead_from_name_skeleton() -> None:
    e = _monster_name_to_enemy("스켈레톤 아처")
    assert e.enemy_type == EnemyType.UNDEAD


def test_spawn_undead_deadman() -> None:
    e = _monster_name_to_enemy("데드맨")
    assert e.enemy_type == EnemyType.UNDEAD


def test_spawn_spirit_from_name_banshee() -> None:
    e = _monster_name_to_enemy("벤시")
    assert e.enemy_type == EnemyType.SPIRIT


def test_spawn_cold_beast_yeti() -> None:
    e = _monster_name_to_enemy("예티")
    assert e.enemy_type == EnemyType.COLD_BEAST


def test_spawn_cold_beast_frost_wolf() -> None:
    e = _monster_name_to_enemy("서리 늑대")
    assert e.enemy_type == EnemyType.COLD_BEAST


def test_spawn_physical_default() -> None:
    e = _monster_name_to_enemy("이름 모를 적")
    assert e.enemy_type == EnemyType.PHYSICAL


# ── weakness_types 자동 주입 ──


def test_undead_weakness_types_injected() -> None:
    e = _monster_name_to_enemy("구울")
    assert "신성력" in e.weakness_types
    assert "불" in e.weakness_types


def test_cold_beast_weakness_types_injected() -> None:
    e = _monster_name_to_enemy("예티")
    assert "전격" in e.weakness_types


def test_physical_no_weakness_types() -> None:
    e = _monster_name_to_enemy("고블린")
    assert e.weakness_types == []


# ── enemy_to_dict / enemy_from_dict 라운드트립 ──


def test_enemy_type_roundtrip() -> None:
    from service.sim.enemy import enemy_from_dict, enemy_to_dict

    e = _monster_name_to_enemy("구울")
    d = enemy_to_dict(e)
    assert d["enemy_type"] == "undead"

    e2 = enemy_from_dict(d)
    assert e2.enemy_type == EnemyType.UNDEAD


def test_spirit_roundtrip_preserves_immunity() -> None:
    from service.sim.combat import compute_damage_multiplier
    from service.sim.enemy import enemy_from_dict, enemy_to_dict

    e = _monster_name_to_enemy("벤시")
    d = enemy_to_dict(e)
    e2 = enemy_from_dict(d)

    assert e2.enemy_type == EnemyType.SPIRIT
    assert compute_damage_multiplier(e2, ["물리"]) == 0.0
