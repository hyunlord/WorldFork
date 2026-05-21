"""dungeon_clock 단위 테스트 — 168h cycle + warning thresholds."""

from __future__ import annotations

import pytest

from service.sim.dungeon_clock import (
    FLOOR_CYCLE_HOURS,
    RETURN_TIME_ADVANCE_HOURS,
    check_warning,
    hours_remaining,
    should_force_return,
)


class TestFloorCycleHours:
    def test_floor1_168h(self) -> None:
        assert FLOOR_CYCLE_HOURS[1] == 168.0

    def test_floor2_240h(self) -> None:
        assert FLOOR_CYCLE_HOURS[2] == 240.0

    def test_floor3_15days(self) -> None:
        assert FLOOR_CYCLE_HOURS[3] == 15.0 * 24

    def test_return_advance_24h(self) -> None:
        assert RETURN_TIME_ADVANCE_HOURS == 24.0


class TestHoursRemaining:
    def test_basic(self) -> None:
        assert hours_remaining(1, 100.0) == pytest.approx(68.0)

    def test_zero_at_start(self) -> None:
        assert hours_remaining(1, 0.0) == pytest.approx(168.0)

    def test_at_limit(self) -> None:
        assert hours_remaining(1, 168.0) == pytest.approx(0.0)

    def test_beyond_limit(self) -> None:
        result = hours_remaining(1, 170.0)
        assert result is not None and result < 0

    def test_unknown_floor_returns_none(self) -> None:
        assert hours_remaining(99, 0.0) is None


class TestShouldForceReturn:
    def test_not_yet(self) -> None:
        assert should_force_return(1, 167.9) is False

    def test_exactly_at_limit(self) -> None:
        assert should_force_return(1, 168.0) is True

    def test_past_limit(self) -> None:
        assert should_force_return(1, 200.0) is True

    def test_unknown_floor(self) -> None:
        assert should_force_return(99, 999.0) is False


class TestCheckWarning:
    def test_1h_threshold_crossed(self) -> None:
        # 1.3h → 0.8h: 1h threshold 통과
        result = check_warning(1, 166.7, 167.2)
        assert result is not None
        assert result.kind == "1h"
        assert "층계" in result.message

    def test_10min_threshold_crossed(self) -> None:
        # 0.2h → 0.1h: 10min(0.1667h) threshold 통과
        result = check_warning(1, 167.8, 167.95)
        assert result is not None
        assert result.kind == "10min"
        assert "10분" in result.message

    def test_1min_threshold_crossed(self) -> None:
        # 0.02h → 0.005h: 1min(0.01667h) threshold 통과
        result = check_warning(1, 167.98, 167.995)
        assert result is not None
        assert result.kind == "1min"
        assert "1분" in result.message

    def test_no_threshold_crossed(self) -> None:
        assert check_warning(1, 100.0, 101.0) is None

    def test_already_past_limit_returns_none(self) -> None:
        # 강제 귀환 대상 — check_warning은 None 반환
        assert check_warning(1, 168.0, 170.0) is None

    def test_unknown_floor_returns_none(self) -> None:
        assert check_warning(99, 0.0, 1.0) is None

    def test_1min_beats_10min_when_both_crossed(self) -> None:
        # 0.02h → 0.001h: 1min이 더 급함
        result = check_warning(1, 167.98, 167.999)
        assert result is not None
        assert result.kind == "1min"
