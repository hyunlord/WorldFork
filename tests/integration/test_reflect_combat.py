"""피해 반사 combat 연결 — execute_enemy_turn 반사 적용 (★ case A e2e)."""

from __future__ import annotations

from service.sim.combat import execute_enemy_turn
from service.sim.enemy import Enemy


def _enemy(hp: int = 30, attack: int = 20, defense: int = 3) -> Enemy:
    return Enemy(
        name="고블린",
        hp=hp,
        max_hp=30,
        attack=attack,
        defense=defense,
        grade=1,
        race="고블린",
        essence_drop="고블린 정수",
        weakness_races=[],
    )


def test_enemy_attack_reflected() -> None:
    """★ case A — enemy 공격 시 받은 피해의 일부를 enemy에게 반사."""
    enemy = _enemy(hp=30, attack=20)
    enemies, new_hp, _status, logs = execute_enemy_turn(
        [enemy], 100, 100, player_defense=5, player_status=[], player_reflect=0.15
    )
    # 받은 피해 15(=20-5), 반사 int(15*0.15)=2 → enemy 30-2=28
    assert new_hp == 85
    assert enemies[0].hp == 28
    assert any("반사" in log.notes for log in logs)


def test_no_reflect_without_passive() -> None:
    """반사 passive 없으면 enemy hp 불변 (회귀)."""
    enemy = _enemy(hp=30, attack=20)
    enemies, new_hp, _status, _logs = execute_enemy_turn(
        [enemy], 100, 100, player_defense=5, player_status=[], player_reflect=0.0
    )
    assert new_hp == 85
    assert enemies[0].hp == 30  # 반사 없음


def test_reflect_can_kill_enemy() -> None:
    """반사 데미지로 enemy 처치 가능 (high reflect, low enemy hp)."""
    enemy = _enemy(hp=2, attack=30)
    enemies, _new_hp, _status, _logs = execute_enemy_turn(
        [enemy], 100, 100, player_defense=0, player_status=[], player_reflect=0.25
    )
    # 받은 피해 30, 반사 int(30*0.25)=7 → enemy 2-7 → 0
    assert enemies[0].hp == 0


def test_reflect_min_one_on_hit() -> None:
    """피해 적중 시 반사는 최소 1 (작은 피해도 보복)."""
    enemy = _enemy(hp=30, attack=4)
    enemies, _new_hp, _status, _logs = execute_enemy_turn(
        [enemy], 100, 100, player_defense=3, player_status=[], player_reflect=0.10
    )
    # 받은 피해 1(=max(1,4-3)), 반사 max(1, int(1*0.10))=1 → enemy 30-1=29
    assert enemies[0].hp == 29
