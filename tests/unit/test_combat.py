"""Phase D step 6b — combat.py primitives tests."""

from __future__ import annotations

from service.sim.combat import (
    cleanup_dead_enemies,
    execute_enemy_turn,
    execute_player_attack,
    find_target_index,
)
from service.sim.enemy import Enemy
from service.sim.status import StatusEffect, StatusType


def _goblin(hp: int = 30, defense: int = 3, attack: int = 8) -> Enemy:
    return Enemy(
        name="고블린",
        hp=hp,
        max_hp=30,
        attack=attack,
        defense=defense,
        grade=1,
        race="고블린",
        essence_drop="고블린 정수",
        weakness_races=["인간"],
    )


def _orc(hp: int = 50) -> Enemy:
    return Enemy(
        name="오크",
        hp=hp,
        max_hp=50,
        attack=12,
        defense=5,
        grade=2,
        abilities=["강타"],
    )


# ── execute_player_attack ─────────────────────────────────────────────────────


def test_player_attack_deals_damage() -> None:
    enemies, log = execute_player_attack([_goblin(hp=30, defense=3)], 0, 10, "공격")
    assert log.damage_dealt == 7
    assert enemies[0].hp == 23


def test_player_attack_resolves_enemy() -> None:
    enemies, log = execute_player_attack([_goblin(hp=5, defense=0)], 0, 10, "공격")
    assert log.enemy_resolved is True
    assert enemies[0].hp == 0


def test_player_attack_min_damage_one() -> None:
    _, log = execute_player_attack([_goblin(hp=50, defense=50)], 0, 10, "공격")
    assert log.damage_dealt == 1


def test_player_attack_weakness_multiplier() -> None:
    _, log = execute_player_attack([_goblin(defense=0)], 0, 10, "인간 약점 공격")
    assert log.damage_dealt == 15  # 10 * 1.5


def test_player_attack_out_of_range_idx() -> None:
    _, log = execute_player_attack([], 0, 10, "공격")
    assert log.notes == "no target"


def test_player_attack_multi_target() -> None:
    enemies = [_goblin(hp=30), _orc(hp=50)]
    enemies, log = execute_player_attack(enemies, 1, 15, "오크")
    assert log.target_name == "오크"
    assert enemies[1].hp == 40  # 15 - 5 = 10 damage


# ── execute_enemy_turn ────────────────────────────────────────────────────────


def test_enemy_turn_deals_damage() -> None:
    goblin = Enemy(
        name="고블린", hp=30, max_hp=30, attack=8, defense=3, abilities=["기본 공격"]
    )
    _, new_hp, _, logs = execute_enemy_turn([goblin], 100, 100, 5, [])
    assert new_hp == 97  # max(1, 8-5) = 3
    assert len(logs) == 1


def test_enemy_turn_heal_ability() -> None:
    goblin = Enemy(
        name="고블린", hp=10, max_hp=30, attack=8, defense=3, abilities=["회복 (P)"]
    )
    enemies, new_hp, _, logs = execute_enemy_turn([goblin], 100, 100, 5, [])
    assert new_hp == 100  # no damage
    assert any("hp +" in log.notes for log in logs)
    assert enemies[0].hp > 10


def test_enemy_turn_status_applied() -> None:
    goblin = Enemy(
        name="고블린 궁수", hp=30, max_hp=30, attack=8, defense=2, abilities=["독화살 (P)"]
    )
    _, _, new_status, logs = execute_enemy_turn([goblin], 100, 100, 3, [])
    status_types = {s.type for s in new_status}
    assert StatusType.POISON in status_types


def test_enemy_turn_applies_existing_status_hp_reduction() -> None:
    goblin = Enemy(
        name="고블린", hp=30, max_hp=30, attack=8, defense=3, abilities=["공격"]
    )
    poison = StatusEffect(type=StatusType.POISON, duration=3, intensity=5, source="독")
    _, new_hp, _, _ = execute_enemy_turn([goblin], 100, 100, 5, [poison])
    # attack: max(1, 8-5)=3 damage + poison 5 = 92
    assert new_hp == 92


def test_enemy_turn_skips_dead() -> None:
    dead = Enemy(name="죽은 몬스터", hp=0, max_hp=50, attack=20, defense=0, abilities=["공격"])
    _, new_hp, _, logs = execute_enemy_turn([dead], 100, 100, 0, [])
    assert new_hp == 100
    assert logs == []


# ── cleanup_dead_enemies ──────────────────────────────────────────────────────


def test_cleanup_removes_dead() -> None:
    alive = _goblin(hp=10)
    dead = _goblin(hp=0)
    living, essence, _ = cleanup_dead_enemies([alive, dead])
    assert len(living) == 1
    assert living[0].hp == 10


def test_cleanup_essence_drop() -> None:
    dead = _goblin(hp=0)
    _, essence, _ = cleanup_dead_enemies([dead])
    assert "고블린 정수" in essence


def test_cleanup_no_drop_if_alive() -> None:
    alive = _goblin(hp=10)
    _, essence, _ = cleanup_dead_enemies([alive])
    assert essence == []


# ── find_target_index ─────────────────────────────────────────────────────────


def test_find_target_by_name() -> None:
    enemies = [_goblin(), _orc()]
    idx = find_target_index(enemies, "오크를 공격")
    assert idx == 1


def test_find_target_default_first() -> None:
    enemies = [_goblin(), _orc()]
    idx = find_target_index(enemies, "공격")
    assert idx == 0
