"""handle_dialogue race ability_tiers context 통합 테스트 (★ I-G1 runtime)."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import (
    AbilityEntry,
    AbilityTier,
    CanonFacts,
    Character,
    EssenceAbilities,
    Race,
)
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_dialogue


def _make_index() -> EntityIndex:
    facts = CanonFacts(
        essences=[],
        characters=[
            Character(name="가르파", role="주민", race="수인",
                      background="노움트리 농장 일꾼"),
        ],
        locations=[],
        races=[
            Race(
                name="수인",
                ability_tiers=EssenceAbilities(
                    text="민첩(상), 후각(상), 동물 교감(중)",
                    parsed=[
                        AbilityEntry(name="민첩", tier=AbilityTier.HIGH),
                        AbilityEntry(name="후각", tier=AbilityTier.HIGH),
                        AbilityEntry(name="동물 교감", tier=AbilityTier.MID),
                    ],
                ),
            ),
        ],
        mechanisms=[],
    )
    return EntityIndex(facts)


@pytest.fixture(autouse=True)
def _cleanup() -> object:
    yield
    clear_entity_index()


def test_race_ability_tiers_lookup_via_character_race() -> None:
    """character.race → race ability_tiers 연결."""
    idx = _make_index()
    char = idx.get_raw_character("가르파")
    assert char is not None
    race = char["race"]
    at = idx.get_race_ability_tiers(str(race))
    assert at is not None
    assert "민첩(상)" in str(at["text"])


@pytest.mark.asyncio
async def test_dialogue_proceeds_with_race_context() -> None:
    """수인 NPC dialogue — race 특성 context 정합 (template path)."""
    set_entity_index(_make_index())
    ctx = ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="노움트리",
        encounters=[{"name": "가르파", "hostile": False, "is_hostile": False}],
        user_input="안녕",
    )
    result = await handle_dialogue(ctx)
    assert result.success is not False
    assert "가르파" in result.narrative
    assert result.affinity_changes == {"가르파": 1}
