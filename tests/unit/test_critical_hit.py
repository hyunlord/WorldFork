"""Audit step 5 fix commit 3 — 치명타 메커니즘 단위 테스트."""

from __future__ import annotations

import pytest

from service.sim.combat import (
    CRITICAL_BASE_CHANCE,
    CRITICAL_MULTIPLIER,
    apply_critical_damage,
    compute_critical_hit,
)

# ── compute_critical_hit ──


def test_critical_hit_always_fires_with_rand_zero() -> None:
    assert compute_critical_hit(rand_func=lambda: 0.0) is True


def test_critical_hit_never_fires_with_rand_one() -> None:
    assert compute_critical_hit(rand_func=lambda: 1.0) is False


def test_critical_hit_base_chance_boundary() -> None:
    # rand < 0.05 → True
    assert compute_critical_hit(player_agility=0, rand_func=lambda: 0.049) is True
    # rand == 0.05 → False (not strictly less than)
    assert compute_critical_hit(player_agility=0, rand_func=lambda: 0.050) is False


def test_critical_hit_agility_increases_chance() -> None:
    # agility=20 → chance ≈ 0.15
    assert compute_critical_hit(player_agility=20, rand_func=lambda: 0.14) is True
    assert compute_critical_hit(player_agility=20, rand_func=lambda: 0.16) is False


def test_critical_hit_chance_capped_at_30_percent() -> None:
    # agility=100 → raw=0.55 → capped=0.30
    assert compute_critical_hit(player_agility=100, rand_func=lambda: 0.29) is True
    assert compute_critical_hit(player_agility=100, rand_func=lambda: 0.30) is False


def test_critical_hit_agility_zero_uses_base_chance() -> None:
    chance = CRITICAL_BASE_CHANCE
    assert compute_critical_hit(player_agility=0, rand_func=lambda: chance - 0.001) is True
    assert compute_critical_hit(player_agility=0, rand_func=lambda: chance) is False


# ── apply_critical_damage ──


def test_apply_critical_damage_doubles() -> None:
    assert apply_critical_damage(10) == int(10 * CRITICAL_MULTIPLIER)


def test_apply_critical_damage_one() -> None:
    assert apply_critical_damage(1) == 2


def test_apply_critical_damage_large() -> None:
    assert apply_critical_damage(500) == 1000


@pytest.mark.parametrize("base,expected", [
    (7, 14),
    (15, 30),
    (100, 200),
])
def test_apply_critical_damage_parametrized(base: int, expected: int) -> None:
    assert apply_critical_damage(base) == expected
