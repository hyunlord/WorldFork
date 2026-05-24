"""Phase D step 6d — xp_curve 본문 정합 단위 테스트.

canon sources:
  ep_0022: 비요른 L1 시작 / 포탈 EXP +2 → L2
  ep_0035: 5등급 캠보르미어 EXP +5 / variant+1 / guardian+3
  wiki 008: 포탈 +2 ≈ 8등급 → base = 10 - grade
  wiki 008: L≤5 영혼력 +10/레벨, L>5 +30/레벨
"""

from __future__ import annotations

from service.sim.xp_curve import (
    INITIAL_LEVEL,
    INITIAL_MAX_ESSENCES,
    INITIAL_SOUL_POWER,
    LEVEL_CAP,
    XP_CURVE,
    compute_level_for_xp,
    compute_soul_power_for_level,
    compute_xp_grant,
    soul_power_gain_on_level_up,
    xp_for_level,
)

# ─── 초기 상수 ───


def test_initial_level() -> None:
    assert INITIAL_LEVEL == 1


def test_initial_soul_power() -> None:
    assert INITIAL_SOUL_POWER == 10


def test_initial_max_essences() -> None:
    assert INITIAL_MAX_ESSENCES == 1


def test_xp_curve_values() -> None:
    assert XP_CURVE == [
        0, 6, 36, 186, 936, 4_686, 23_436, 117_186, 585_936, 2_929_686, 14_648_436
    ]


# ─── compute_level_for_xp ───


def test_level_for_xp_zero_is_1() -> None:
    assert compute_level_for_xp(0) == 1


def test_level_for_xp_just_below_l2() -> None:
    assert compute_level_for_xp(5) == 1


def test_level_for_xp_exact_threshold_l2() -> None:
    # wiki 008 + ep_0022: 포탈 EXP +2 × 3 = 6 → L2
    assert compute_level_for_xp(6) == 2


def test_level_for_xp_l3() -> None:
    assert compute_level_for_xp(36) == 3


def test_level_for_xp_very_high_capped_at_11() -> None:
    assert compute_level_for_xp(99_999_999) == LEVEL_CAP


# ─── xp_for_level ───


def test_xp_for_level_1_is_0() -> None:
    assert xp_for_level(1) == 0


def test_xp_for_level_2_is_6() -> None:
    assert xp_for_level(2) == 6


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


# ─── compute_soul_power_for_level ───


def test_soul_power_for_level_1() -> None:
    assert compute_soul_power_for_level(1) == 10


def test_soul_power_for_level_5() -> None:
    # L1:10, L2:+10=20, L3:+10=30, L4:+10=40, L5:+10=50
    assert compute_soul_power_for_level(5) == 50


def test_soul_power_for_level_6() -> None:
    # L5:50, L6:+30=80
    assert compute_soul_power_for_level(6) == 80


# ─── compute_xp_grant ───


def test_xp_grant_repeat_kill_zero() -> None:
    assert compute_xp_grant(5, is_first_kill=False, modifiers=[]) == 0


def test_xp_grant_grade9() -> None:
    # 10-9=1
    assert compute_xp_grant(9, is_first_kill=True, modifiers=[]) == 1


def test_xp_grant_grade8_wiki_008() -> None:
    # wiki 008: 포탈 EXP +2 ≈ 8등급 → 10-8=2
    assert compute_xp_grant(8, is_first_kill=True, modifiers=[]) == 2


def test_xp_grant_grade5_ep0035() -> None:
    # ep_0035: 5등급 캠보르미어 EXP +5 → 10-5=5
    assert compute_xp_grant(5, is_first_kill=True, modifiers=[]) == 5


def test_xp_grant_guardian_bonus() -> None:
    # ep_0035: 수호자 처치 bonus +3
    assert compute_xp_grant(3, is_first_kill=True, modifiers=["guardian"]) == 7 + 3


def test_xp_grant_variant_bonus() -> None:
    # ep_0035: 상위 변이종 bonus +1
    assert compute_xp_grant(2, is_first_kill=True, modifiers=["variant"]) == 8 + 1


def test_xp_grant_variant_and_guardian_ep0035() -> None:
    # ep_0035: 5등급 캠보르미어 variant + guardian → 5+1+3=9
    assert compute_xp_grant(5, is_first_kill=True, modifiers=["variant", "guardian"]) == 9


def test_xp_grant_none_grade_defaults_to_grade5() -> None:
    # grade None → default 5 → 10-5=5
    assert compute_xp_grant(None, is_first_kill=True, modifiers=[]) == 5


def test_xp_grant_out_of_range_grade_zero() -> None:
    assert compute_xp_grant(0, is_first_kill=True, modifiers=[]) == 0


def test_xp_grant_out_of_range_grade_10() -> None:
    assert compute_xp_grant(10, is_first_kill=True, modifiers=[]) == 0
