"""Audit step 5 fix — HP threshold 시스템 메시지 단위 테스트."""

from __future__ import annotations

import pytest

from service.sim.combat import check_hp_threshold_message


@pytest.mark.parametrize(
    "prev_hp,new_hp,max_hp,expected_fragment",
    [
        # 50% 경계 진입
        (60, 50, 100, "50% 이하"),
        (51, 49, 100, "50% 이하"),
        # 20% 경계 진입
        (25, 20, 100, "20% 이하"),
        (21, 19, 100, "20% 이하"),
        # 5% 경계 진입 (경고)
        (10, 4, 100, "5% 미만"),
        (6, 3, 100, "5% 미만"),
        # 0% 도달
        (5, 0, 100, "0%에 도달"),
    ],
)
def test_threshold_message_emitted(
    prev_hp: int, new_hp: int, max_hp: int, expected_fragment: str
) -> None:
    msg = check_hp_threshold_message(prev_hp, new_hp, max_hp)
    assert msg is not None, f"expected message for {prev_hp}→{new_hp}/{max_hp}"
    assert expected_fragment in msg


@pytest.mark.parametrize(
    "prev_hp,new_hp,max_hp",
    [
        # 같은 구간 내 하락 — threshold 미경계
        (80, 70, 100),
        (45, 35, 100),
        (15, 12, 100),
        # HP 증가 — 메시지 없음
        (30, 50, 100),
        # 이미 지난 threshold (prev가 이미 낮은 쪽)
        (40, 35, 100),  # 50% 이미 아래였으므로 없음
    ],
)
def test_threshold_message_none(prev_hp: int, new_hp: int, max_hp: int) -> None:
    assert check_hp_threshold_message(prev_hp, new_hp, max_hp) is None


def test_max_hp_zero_returns_none() -> None:
    assert check_hp_threshold_message(0, 0, 0) is None


def test_50pct_threshold_not_triggered_if_already_below() -> None:
    """prev가 이미 50% 이하면 50% threshold 메시지 없음."""
    assert check_hp_threshold_message(40, 30, 100) is None


def test_20pct_boundary_exact() -> None:
    msg = check_hp_threshold_message(21, 20, 100)
    assert msg is not None
    assert "20%" in msg


def test_lowest_threshold_wins_on_large_drop() -> None:
    """크게 HP가 떨어져 여러 threshold를 넘으면 가장 낮은 threshold 메시지 반환."""
    msg = check_hp_threshold_message(100, 0, 100)
    assert msg is not None
    assert "0%" in msg
