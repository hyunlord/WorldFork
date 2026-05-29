"""I-G1 combat resistance — enemy 반격 시 player 저항 감산 통합 테스트."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index
from service.sim.combat import execute_enemy_turn
from service.sim.enemy import Enemy, EnemyType


@pytest.fixture(autouse=True)
def _cleanup() -> object:
    clear_entity_index()
    yield
    clear_entity_index()


def _cold_beast(attack: int = 15) -> Enemy:
    return Enemy(
        name="서리늑대",
        hp=50,
        max_hp=50,
        attack=attack,
        defense=3,
        enemy_type=EnemyType.COLD_BEAST,
    )


def test_cold_beast_attack_reduced_by_cold_resistance() -> None:
    """COLD_BEAST 반격 — 냉기 저항 정합 감산."""
    enemies = [_cold_beast(attack=15)]
    # base_damage = 15 - player_defense 5 = 10, 냉기 저항 3 → 7
    _, new_hp, _, logs = execute_enemy_turn(
        enemies, player_hp=100, player_max_hp=100, player_defense=5,
        player_status=[], player_resistances={"냉기": 3},
    )
    attack_logs = [log for log in logs if log.damage_received > 0]
    assert attack_logs, "enemy 공격 log 없음"
    log = attack_logs[0]
    assert log.damage_received == 7
    assert log.resist_reduced == 3
    assert log.resist_element == "냉기"
    assert new_hp == 93


def test_no_resistance_full_damage() -> None:
    """저항 없으면 감산 X."""
    enemies = [_cold_beast(attack=15)]
    _, new_hp, _, logs = execute_enemy_turn(
        enemies, player_hp=100, player_max_hp=100, player_defense=5,
        player_status=[], player_resistances={"화염": 5},
    )
    attack_logs = [log for log in logs if log.damage_received > 0]
    assert attack_logs[0].damage_received == 10
    assert attack_logs[0].resist_reduced == 0
    assert new_hp == 90


def test_resistance_min_one_damage() -> None:
    """저항 ≥ damage — 최소 1 피해."""
    enemies = [_cold_beast(attack=8)]
    # base_damage = 8 - 5 = 3, 냉기 저항 10 → max(1, -7) = 1
    _, new_hp, _, logs = execute_enemy_turn(
        enemies, player_hp=100, player_max_hp=100, player_defense=5,
        player_status=[], player_resistances={"냉기": 10},
    )
    attack_logs = [log for log in logs if log.damage_received > 0]
    assert attack_logs[0].damage_received == 1
    assert new_hp == 99


def test_default_no_resistances_param() -> None:
    """player_resistances 미전달 — 기존 동작 (감산 X)."""
    enemies = [_cold_beast(attack=15)]
    _, new_hp, _, logs = execute_enemy_turn(
        enemies, player_hp=100, player_max_hp=100, player_defense=5,
        player_status=[],
    )
    attack_logs = [log for log in logs if log.damage_received > 0]
    assert attack_logs[0].damage_received == 10
    assert new_hp == 90
