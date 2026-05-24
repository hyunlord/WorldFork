"""Phase D step 6d — handle_examine_stats tests."""

from __future__ import annotations

import asyncio

from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_examine_stats
from service.sim.player_state import EssenceSlot, slot_to_dict


def _ctx(**kwargs) -> ActionContext:  # type: ignore[no-untyped-def]
    defaults: dict = dict(
        current_hp=80,
        max_hp=100,
        inventory=[],
        location="1층",
        player_level=1,
        player_xp=0,
        max_essences=1,
        soul_power=10,
        absorbed_essences=[],
        defeated_monster_types=[],
    )
    defaults.update(kwargs)
    return ActionContext(**defaults)


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def test_examine_shows_level_and_xp() -> None:
    ctx = _ctx(player_level=4, player_xp=55)
    result = run(handle_examine_stats(ctx))
    assert "4" in result.narrative
    assert "55" in result.narrative


def test_examine_shows_hp() -> None:
    ctx = _ctx(current_hp=70, max_hp=100)
    result = run(handle_examine_stats(ctx))
    assert "70" in result.narrative
    assert "100" in result.narrative


def test_examine_shows_essence_count() -> None:
    slots = [slot_to_dict(EssenceSlot("오크 정수"))]
    ctx = _ctx(absorbed_essences=slots, max_essences=4)
    result = run(handle_examine_stats(ctx))
    assert "오크 정수" in result.narrative


def test_examine_shows_total_stats() -> None:
    slot = slot_to_dict(EssenceSlot("A", stat_bundle={"strength": 15, "agility": -5}))
    ctx = _ctx(absorbed_essences=[slot])
    result = run(handle_examine_stats(ctx))
    assert "strength" in result.narrative or "agility" in result.narrative


def test_examine_zero_time_advance() -> None:
    ctx = _ctx()
    result = run(handle_examine_stats(ctx))
    assert result.time_advance == 0


def test_examine_shows_defeated_count() -> None:
    ctx = _ctx(defeated_monster_types=["고블린", "오크", "슬라임"])
    result = run(handle_examine_stats(ctx))
    assert "3" in result.narrative
