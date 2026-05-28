"""정수 흡수 시 parsed ability narrative + state 적용 통합 테스트."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import (
    AbilityEntry,
    AbilityTier,
    CanonFacts,
    Essence,
    EssenceAbilities,
)
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_absorb_essence


def _make_index() -> EntityIndex:
    facts = CanonFacts(
        essences=[
            Essence(
                name="데스핀드",
                grade=7,
                abilities=EssenceAbilities(
                    text="고통내성(상), 근력(중), 소화력(하)",
                    parsed=[
                        AbilityEntry(name="고통내성", tier=AbilityTier.HIGH),
                        AbilityEntry(name="근력", tier=AbilityTier.MID),
                        AbilityEntry(name="소화력", tier=AbilityTier.LOW),
                    ],
                ),
            ),
        ],
        characters=[], locations=[], races=[], mechanisms=[],
    )
    return EntityIndex(facts)


@pytest.fixture(autouse=True)
def _cleanup_index() -> object:
    yield
    clear_entity_index()


@pytest.mark.asyncio
async def test_absorb_essence_narrative_includes_resistance_and_etc() -> None:
    """parsed essence 흡수 → narrative에 stat + resistance + etc 출력."""
    set_entity_index(_make_index())
    from service.api.schemas.freeform_action import ExtractedEntities
    ctx = ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=["데스핀드"],
        location="1층",
        user_input="데스핀드 흡수",
        extracted_entities=ExtractedEntities(item="데스핀드"),
        player_level=5,
        max_essences=5,
    )

    result = await handle_absorb_essence(ctx)
    assert result.success is not False

    narr = result.narrative
    assert "데스핀드" in narr
    # stat 출력 (근력 중 → attack_bonus +2)
    assert "attack_bonus" in narr and "+2" in narr
    # resistance 출력 (고통내성 상 → 고통 +3)
    assert "고통 저항" in narr and "+3" in narr
    # 미분류 etc 출력 (소화력 하)
    assert "특성 발현" in narr and "소화력(하)" in narr


@pytest.mark.asyncio
async def test_absorb_essence_slot_carries_resistances() -> None:
    """ActionResult.essence_slot_add에 resistances 포함."""
    set_entity_index(_make_index())
    from service.api.schemas.freeform_action import ExtractedEntities
    ctx = ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=["데스핀드"],
        location="1층",
        user_input="데스핀드 흡수",
        extracted_entities=ExtractedEntities(item="데스핀드"),
        player_level=5,
        max_essences=5,
    )

    result = await handle_absorb_essence(ctx)
    slot_dict = result.essence_slot_add
    assert slot_dict is not None
    assert slot_dict["resistances"] == {"고통": 3}
    assert "소화력(하)" in slot_dict["etc_abilities"]


def test_total_resistances_accumulates() -> None:
    """ActionContext.total_resistances — 다중 정수 합산."""
    ctx = ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층",
        absorbed_essences=[
            {
                "essence_name": "A",
                "stat_bundle": {},
                "skills": [],
                "grade": None,
                "resistances": {"독": 2, "냉기": 1},
                "etc_abilities": [],
            },
            {
                "essence_name": "B",
                "stat_bundle": {},
                "skills": [],
                "grade": None,
                "resistances": {"독": 1, "고통": 3},
                "etc_abilities": [],
            },
        ],
    )
    assert ctx.total_resistances == {"독": 3, "냉기": 1, "고통": 3}
