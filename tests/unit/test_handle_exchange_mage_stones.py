"""Audit C1 — handle_exchange_mage_stones 단위 테스트."""

import asyncio
from collections.abc import Coroutine
from typing import Any

from service.sim.action_context import ActionContext, ActionResult
from service.sim.action_handlers import handle_exchange_mage_stones


def run(coro: Coroutine[Any, Any, ActionResult]) -> ActionResult:
    return asyncio.run(coro)


def _ctx(inventory: list[str]) -> ActionContext:
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=inventory,
        location="라스카니아 · 차원광장",
    )


def test_no_mage_stone_fails() -> None:
    result = run(handle_exchange_mage_stones(_ctx(["방패", "포션"])))
    assert result.success is False
    assert result.fail_reason == "no_mage_stone"
    assert result.stone_change == 0


def test_9th_grade_single() -> None:
    result = run(handle_exchange_mage_stones(_ctx(["9등급 마석"])))
    assert result.success is True
    assert result.stone_change == 20
    assert "9등급 마석" in result.inventory_remove


def test_8th_grade_single() -> None:
    result = run(handle_exchange_mage_stones(_ctx(["8등급 마석"])))
    assert result.stone_change == 100


def test_mixed_grades_sum() -> None:
    # 9등급×2=40 + 8등급×1=100 = 140
    result = run(handle_exchange_mage_stones(
        _ctx(["9등급 마석", "9등급 마석", "8등급 마석", "방패"])
    ))
    assert result.stone_change == 140
    assert len(result.inventory_remove) == 3
    assert "방패" not in result.inventory_remove


def test_tip_format_in_narrative() -> None:
    result = run(handle_exchange_mage_stones(_ctx(["9등급 마석"])))
    assert "20스톤입니다" in result.narrative
    assert "「" in result.narrative
