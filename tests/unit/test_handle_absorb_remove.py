"""Phase D step 6d — handle_absorb_essence / handle_remove_essence tests."""

from __future__ import annotations

import asyncio

from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_absorb_essence, handle_remove_essence
from service.sim.player_state import EssenceSlot, slot_to_dict


def _ctx(
    inventory: list[str] | None = None,
    absorbed: list[dict] | None = None,
    max_essences: int = 4,
    item_entity: str | None = None,
) -> ActionContext:
    from service.api.schemas.freeform_action import ExtractedEntities
    entities = ExtractedEntities(item=item_entity) if item_entity else None
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=list(inventory or []),
        location="1층",
        user_input="정수 흡수",
        extracted_entities=entities,
        max_essences=max_essences,
        absorbed_essences=list(absorbed or []),
    )


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


# ─── absorb ───


def test_absorb_no_essence_in_inventory() -> None:
    ctx = _ctx(inventory=[])
    result = run(handle_absorb_essence(ctx))
    assert result.success is False
    assert result.fail_reason == "no_essence"


def test_absorb_limit_reached() -> None:
    slots = [slot_to_dict(EssenceSlot(f"정수{i}")) for i in range(4)]
    ctx = _ctx(inventory=["고블린 정수"], absorbed=slots, max_essences=4)
    result = run(handle_absorb_essence(ctx))
    assert result.success is False
    assert result.fail_reason == "essence_limit_reached"


def test_absorb_success_adds_slot() -> None:
    ctx = _ctx(inventory=["고블린 정수"], max_essences=4)
    result = run(handle_absorb_essence(ctx))
    assert result.success is True
    assert "고블린 정수" in result.inventory_remove
    assert result.essence_slot_add is not None
    assert result.essence_slot_add.get("essence_name") == "고블린 정수"


def test_absorb_entity_extracted_item_used() -> None:
    ctx = _ctx(inventory=["오크 정수", "고블린 정수"], item_entity="오크 정수", max_essences=4)
    result = run(handle_absorb_essence(ctx))
    assert result.essence_slot_add is not None
    assert result.essence_slot_add.get("essence_name") == "오크 정수"


# ─── remove ───


def test_remove_not_absorbed_fails() -> None:
    ctx = _ctx(absorbed=[], item_entity="없는 정수")
    result = run(handle_remove_essence(ctx))
    assert result.success is False
    assert result.fail_reason == "not_absorbed"


def test_remove_no_entity_fails() -> None:
    ctx = _ctx(absorbed=[slot_to_dict(EssenceSlot("고블린 정수"))])
    result = run(handle_remove_essence(ctx))
    assert result.success is False
    assert result.fail_reason == "no_essence"


def test_remove_success_sets_remove_field() -> None:
    slot = slot_to_dict(EssenceSlot("오크 정수", stat_bundle={"strength": 10}))
    ctx = _ctx(absorbed=[slot], item_entity="오크 정수")
    result = run(handle_remove_essence(ctx))
    assert result.success is True
    assert result.essence_slot_remove == "오크 정수"


def test_remove_narrative_contains_stat() -> None:
    slot = slot_to_dict(EssenceSlot("시체골렘 정수", stat_bundle={"resistance": 70}))
    ctx = _ctx(absorbed=[slot], item_entity="시체골렘 정수")
    result = run(handle_remove_essence(ctx))
    assert "resistance" in result.narrative or "70" in result.narrative
