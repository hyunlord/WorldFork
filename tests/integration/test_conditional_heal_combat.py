"""HP 임계 회복 combat 연결 — enemy 조건부 회복 강도 정밀화 (★ case A e2e).

enemy_ai HP<30% 회복 우선(select_ability) + combat 회복량 canon 강도 반영.
"""

from __future__ import annotations

import pytest

import service.sim.combat as _combat
from service.sim.combat import execute_enemy_turn
from service.sim.enemy import Enemy


def _enemy(hp: int, max_hp: int, abilities: list[str]) -> Enemy:
    return Enemy(
        name="보스",
        hp=hp,
        max_hp=max_hp,
        attack=5,
        defense=0,
        grade=5,
        race="boss",
        essence_drop="x",
        weakness_races=[],
        abilities=abilities,
    )


def test_enemy_heal_scaled_by_canon(monkeypatch: pytest.MonkeyPatch) -> None:
    """★ HP<30% 회복 우선 → canon 강도(0.5)로 회복량 정밀화."""
    monkeypatch.setattr(
        _combat, "_lookup_heal_ratio", lambda name: 0.5 if "회복" in name else 0.0
    )
    enemy = _enemy(hp=10, max_hp=100, abilities=["회복(최상급)"])  # 10% < 30% → 회복 우선
    enemies, _hp, _st, logs = execute_enemy_turn([enemy], 100, 100, 0, [])
    assert enemies[0].hp == 60  # 10 + int(100*0.5)
    assert any("hp +50" in log.notes for log in logs)


def test_enemy_heal_fallback_preserves_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    """★ 회귀 — fallback 0.2 = 기존 max_hp//5 동작 보존."""
    monkeypatch.setattr(_combat, "_lookup_heal_ratio", lambda name: 0.2)
    enemy = _enemy(hp=10, max_hp=100, abilities=["회복"])
    enemies, _hp, _st, _logs = execute_enemy_turn([enemy], 100, 100, 0, [])
    assert enemies[0].hp == 30  # 10 + int(100*0.2) = 10 + 20 (= max_hp//5)


def test_enemy_attacks_when_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    """HP 충분(>50%) 시 회복 우선 안 함 — 공격 (select_ability 정합)."""
    monkeypatch.setattr(_combat, "_lookup_heal_ratio", lambda name: 0.5)
    enemy = _enemy(hp=90, max_hp=100, abilities=["강타", "회복(최상급)"])
    enemies, new_hp, _st, _logs = execute_enemy_turn([enemy], 100, 100, 0, [])
    # HP 90% → select_ability abilities[0]="강타"(공격) → enemy hp 불변, player 피해
    assert enemies[0].hp == 90
    assert new_hp < 100


def test_heal_min_five(monkeypatch: pytest.MonkeyPatch) -> None:
    """작은 max_hp에서도 회복 최소 5."""
    monkeypatch.setattr(_combat, "_lookup_heal_ratio", lambda name: 0.2)
    enemy = _enemy(hp=2, max_hp=10, abilities=["회복"])
    enemies, _hp, _st, _logs = execute_enemy_turn([enemy], 100, 100, 0, [])
    assert enemies[0].hp == 7  # 2 + max(5, int(10*0.2)=2) = 2 + 5
