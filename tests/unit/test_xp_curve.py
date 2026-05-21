"""Phase D step 6d — xp_curve unit tests."""

from __future__ import annotations

from service.sim.xp_curve import (
    LEVEL_CAP,
    compute_level_for_xp,
    compute_xp_grant,
    soul_power_gain_on_level_up,
    xp_for_level,
)

# ─── compute_level_for_xp ───


def test_level_for_xp_zero_is_1() -> None:
    assert compute_level_for_xp(0) == 1


def test_level_for_xp_exact_threshold_l2() -> None:
    assert compute_level_for_xp(5) == 2


def test_level_for_xp_just_below_l2() -> None:
    assert compute_level_for_xp(4) == 1


def test_level_for_xp_l3() -> None:
    assert compute_level_for_xp(20) == 3


def test_level_for_xp_l4() -> None:
    assert compute_level_for_xp(55) == 4


def test_level_for_xp_very_high_capped_at_11() -> None:
    assert compute_level_for_xp(99999) == LEVEL_CAP


def test_level_for_xp_exact_l11() -> None:
    assert compute_level_for_xp(9880) == 11


# ─── xp_for_level ───


def test_xp_for_level_1_is_0() -> None:
    assert xp_for_level(1) == 0


def test_xp_for_level_2_is_5() -> None:
    assert xp_for_level(2) == 5


def test_xp_for_level_beyond_cap_clamped() -> None:
    assert xp_for_level(99) == xp_for_level(LEVEL_CAP)


# ─── soul_power_gain_on_level_up ───


def test_soul_power_gain_l2_is_10() -> None:
    assert soul_power_gain_on_level_up(2) == 10


def test_soul_power_gain_l5_is_10() -> None:
    assert soul_power_gain_on_level_up(5) == 10


def test_soul_power_gain_l6_is_30() -> None:
    assert soul_power_gain_on_level_up(6) == 30


def test_soul_power_gain_l11_is_30() -> None:
    assert soul_power_gain_on_level_up(11) == 30


# ─── compute_xp_grant ───


def test_xp_grant_repeat_kill_zero() -> None:
    assert compute_xp_grant(5, is_first_kill=False, modifiers=[]) == 0


def test_xp_grant_first_kill_base_grade() -> None:
    assert compute_xp_grant(3, is_first_kill=True, modifiers=[]) == 3


def test_xp_grant_guardian_bonus() -> None:
    assert compute_xp_grant(1, is_first_kill=True, modifiers=["guardian"]) == 1 + 3


def test_xp_grant_variant_bonus() -> None:
    assert compute_xp_grant(2, is_first_kill=True, modifiers=["variant"]) == 2 + 1


def test_xp_grant_stratum_boss() -> None:
    result = compute_xp_grant(1, is_first_kill=True, modifiers=["stratum_boss"])
    assert result == 1 + 99 + 15


def test_xp_grant_stratum_boss_with_guardian() -> None:
    result = compute_xp_grant(5, is_first_kill=True, modifiers=["stratum_boss", "guardian"])
    assert result == 5 + 99 + 15 + 3


def test_xp_grant_none_grade_treated_as_1() -> None:
    assert compute_xp_grant(None, is_first_kill=True, modifiers=[]) == 1
