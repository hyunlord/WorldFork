"""handle_enter_dungeon + handle_exit_to_prev_floor 의 hours_in_dungeon_reset 테스트."""

from __future__ import annotations

import pytest

from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_enter_dungeon, handle_exit_to_prev_floor


def _make_ctx(**kwargs: object) -> ActionContext:
    base: dict[str, object] = dict(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="마을",
        floor_number=0,
    )
    base.update(kwargs)
    return ActionContext(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_enter_dungeon_sets_reset_flag() -> None:
    ctx = _make_ctx(floor_number=0)
    result = await handle_enter_dungeon(ctx)
    assert result.hours_in_dungeon_reset is True


@pytest.mark.asyncio
async def test_enter_dungeon_floor_change_plus1() -> None:
    ctx = _make_ctx(floor_number=0)
    result = await handle_enter_dungeon(ctx)
    assert result.floor_change == 1


@pytest.mark.asyncio
async def test_exit_to_prev_floor_1_to_0_sets_reset() -> None:
    ctx = _make_ctx(floor_number=1, location="1층 중심부")
    result = await handle_exit_to_prev_floor(ctx)
    assert result.hours_in_dungeon_reset is True
    assert result.floor_change == -1


@pytest.mark.asyncio
async def test_exit_to_prev_floor_2_to_1_no_reset() -> None:
    ctx = _make_ctx(floor_number=2, location="2층 입구")
    result = await handle_exit_to_prev_floor(ctx)
    assert result.hours_in_dungeon_reset is False


@pytest.mark.asyncio
async def test_exit_already_outside_no_reset() -> None:
    ctx = _make_ctx(floor_number=0, location="마을")
    result = await handle_exit_to_prev_floor(ctx)
    assert result.success is False
    assert result.hours_in_dungeon_reset is False
