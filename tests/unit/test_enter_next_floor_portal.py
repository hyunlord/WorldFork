"""audit-step7 fix — handle_enter_next_floor 포탈 비석 narrative 검증."""

from __future__ import annotations

import pytest

from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_enter_next_floor


def _make_ctx(floor: int = 1) -> ActionContext:
    return ActionContext(
        current_hp=100, max_hp=100,
        inventory=[], location="1층 입구",
        encounters=[], user_input="다음 층으로",
        floor_number=floor,
    )


@pytest.mark.asyncio
async def test_enter_next_floor_portal_narrative() -> None:
    """다음 층 진입 — '포탈 비석' 포함."""
    result = await handle_enter_next_floor(_make_ctx(floor=1))
    assert result.success
    assert "포탈 비석" in result.narrative


@pytest.mark.asyncio
async def test_enter_next_floor_no_old_stairs() -> None:
    """다음 층 진입 narrative — '층계를 내려가' 미포함."""
    result = await handle_enter_next_floor(_make_ctx(floor=1))
    assert "층계를 내려가" not in result.narrative


@pytest.mark.asyncio
async def test_enter_next_floor_location() -> None:
    """다음 층 진입 → location = '2층 입구'."""
    result = await handle_enter_next_floor(_make_ctx(floor=1))
    assert result.location == "2층 입구"
    assert result.floor_change == 1


@pytest.mark.asyncio
async def test_enter_next_floor_max_floor() -> None:
    """10층 초과 진입 시 실패."""
    result = await handle_enter_next_floor(_make_ctx(floor=10))
    assert not result.success
    assert result.fail_reason == "max_floor"
