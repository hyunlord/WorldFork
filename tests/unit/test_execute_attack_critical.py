"""Audit step 5 fix commit 3 — execute_player_attack 치명타 통합 테스트."""

from __future__ import annotations

from service.sim.combat import execute_player_attack
from service.sim.enemy import Enemy, EnemyType


def _make_enemy(
    name: str = "고블린",
    hp: int = 50,
    defense: int = 0,
    enemy_type: EnemyType = EnemyType.PHYSICAL,
) -> Enemy:
    return Enemy(
        name=name,
        hp=hp, max_hp=hp,
        attack=5, defense=defense,
        grade=1,
        enemy_type=enemy_type,
    )


# ── 일반 공격 (치명타 없음) ──


def test_normal_attack_no_critical() -> None:
    enemies = [_make_enemy(hp=50, defense=0)]
    new_enemies, log = execute_player_attack(
        enemies, 0, player_attack=10, user_input="",
        player_agility=0, rand_func=lambda: 1.0,  # 치명타 없음
    )
    assert log.critical_hit is False
    assert log.damage_dealt == 10
    assert new_enemies[0].hp == 40


# ── 치명타 공격 ──


def test_critical_attack_doubles_damage() -> None:
    enemies = [_make_enemy(hp=100, defense=0)]
    new_enemies, log = execute_player_attack(
        enemies, 0, player_attack=10, user_input="",
        player_agility=0, rand_func=lambda: 0.0,  # 치명타 확정
    )
    assert log.critical_hit is True
    assert log.damage_dealt == 20  # base 10 * 2
    assert new_enemies[0].hp == 80


# ── 영체류 면역 + 치명타 ──


def test_spirit_immune_no_critical() -> None:
    enemies = [_make_enemy(hp=50, enemy_type=EnemyType.SPIRIT)]
    new_enemies, log = execute_player_attack(
        enemies, 0, player_attack=10, user_input="",
        attack_elements=["물리"],
        player_agility=0, rand_func=lambda: 0.0,  # 치명타 판정 전 면역으로 조기 반환
    )
    assert log.immune is True
    assert log.critical_hit is False
    assert log.damage_dealt == 0


# ── 약점 적중 + 치명타 ──


def test_weakness_hit_and_critical() -> None:
    enemies = [_make_enemy(hp=100, defense=0)]
    enemies[0].weakness_types = ["불"]
    new_enemies, log = execute_player_attack(
        enemies, 0, player_attack=10, user_input="",
        attack_elements=["불"],
        player_agility=0, rand_func=lambda: 0.0,  # 치명타 확정
    )
    assert log.weakness_hit is True
    assert log.critical_hit is True
    # base=10, weakness 1.5→15, critical 2x→30
    assert log.damage_dealt == 30


# ── 치명타로 enemy 처치 ──


def test_critical_kill_sets_enemy_resolved() -> None:
    enemies = [_make_enemy(hp=5, defense=0)]
    _, log = execute_player_attack(
        enemies, 0, player_attack=10, user_input="",
        player_agility=0, rand_func=lambda: 0.0,
    )
    assert log.enemy_resolved is True
    assert log.critical_hit is True


# ── agility가 치명타율을 높이는지 ──


def test_high_agility_increases_critical_chance() -> None:
    enemies = [_make_enemy(hp=100)]
    _, log = execute_player_attack(
        enemies, 0, player_attack=10, user_input="",
        player_agility=50, rand_func=lambda: 0.25,  # 0.25 < 0.30 (cap)
    )
    assert log.critical_hit is True
