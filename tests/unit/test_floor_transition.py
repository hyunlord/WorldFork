"""Phase D step 7 — floor transition 단위 테스트."""

from __future__ import annotations

import asyncio

from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_enter_next_floor, handle_exit_to_prev_floor


def _ctx(floor_number: int = 1, location: str = "1층 입구") -> ActionContext:
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location=location,
        floor_number=floor_number,
    )


def run(coro: object) -> object:
    import inspect
    if inspect.iscoroutine(coro):
        return asyncio.run(coro)  # type: ignore[arg-type]
    return coro


class TestEnterNextFloor:
    def test_floor1_to_floor2(self) -> None:
        result = run(handle_enter_next_floor(_ctx(floor_number=1)))
        assert result.floor_change == 1  # type: ignore[union-attr]
        assert result.location == "2층 입구"  # type: ignore[union-attr]
        assert result.success  # type: ignore[union-attr]

    def test_floor5_to_floor6(self) -> None:
        result = run(handle_enter_next_floor(_ctx(floor_number=5, location="5층 입구")))
        assert result.floor_change == 1  # type: ignore[union-attr]
        assert result.location == "6층 입구"  # type: ignore[union-attr]

    def test_floor10_max_blocked(self) -> None:
        result = run(handle_enter_next_floor(_ctx(floor_number=10, location="10층 입구")))
        assert not result.success  # type: ignore[union-attr]
        assert result.fail_reason == "max_floor"  # type: ignore[union-attr]
        assert result.floor_change is None  # type: ignore[union-attr]

    def test_floor0_town_to_floor1(self) -> None:
        result = run(handle_enter_next_floor(_ctx(floor_number=0, location="마을")))
        assert result.floor_change == 1  # type: ignore[union-attr]
        assert result.location == "1층 입구"  # type: ignore[union-attr]


class TestExitToPrevFloor:
    def test_floor1_to_town(self) -> None:
        result = run(handle_exit_to_prev_floor(_ctx(floor_number=1)))
        assert result.floor_change == -1  # type: ignore[union-attr]
        assert result.location == "마을"  # type: ignore[union-attr]
        assert result.success  # type: ignore[union-attr]

    def test_floor3_to_floor2(self) -> None:
        result = run(handle_exit_to_prev_floor(_ctx(floor_number=3, location="3층 입구")))
        assert result.floor_change == -1  # type: ignore[union-attr]
        assert result.location == "2층 입구"  # type: ignore[union-attr]

    def test_floor0_already_outside(self) -> None:
        result = run(handle_exit_to_prev_floor(_ctx(floor_number=0, location="마을")))
        assert not result.success  # type: ignore[union-attr]
        assert result.fail_reason == "already_outside"  # type: ignore[union-attr]
        assert result.floor_change is None  # type: ignore[union-attr]

    def test_floor1_narrative_has_town(self) -> None:
        result = run(handle_exit_to_prev_floor(_ctx(floor_number=1)))
        assert "마을" in result.narrative  # type: ignore[union-attr]
