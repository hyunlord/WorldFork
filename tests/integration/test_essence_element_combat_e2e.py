"""정수 흡수 → 공격 element → enemy 약점 통합 테스트."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Essence
from service.sim.action_context import ActionContext
from service.sim.action_handlers import _get_attack_elements, handle_absorb_essence
from service.sim.combat import compute_damage_multiplier
from service.sim.enemy import enemy_from_dict


@pytest.fixture(autouse=True)
def _cleanup() -> object:
    yield
    clear_entity_index()


def _index_with_fire_essence() -> EntityIndex:
    facts = CanonFacts(
        essences=[
            Essence(name="용암거인 정수", grade=5, source_monster="용암거인"),
        ],
        characters=[], locations=[], races=[], mechanisms=[],
    )
    return EntityIndex(facts)


@pytest.mark.asyncio
async def test_absorb_grants_attack_element() -> None:
    """불 monster 정수 흡수 → attack_element '불' 부여 + narrative."""
    from service.api.schemas.freeform_action import ExtractedEntities

    set_entity_index(_index_with_fire_essence())
    ctx = ActionContext(
        current_hp=100, max_hp=100, inventory=["용암거인 정수"], location="1층",
        user_input="용암거인 정수 흡수",
        extracted_entities=ExtractedEntities(item="용암거인 정수"),
        player_level=5, max_essences=5,
    )
    result = await handle_absorb_essence(ctx)
    assert result.success is not False
    slot = result.essence_slot_add
    assert slot is not None
    assert slot["attack_elements"] == ["불"]
    assert "불 속성 공격" in result.narrative


def test_essence_element_in_attack_elements() -> None:
    """흡수 정수 element가 _get_attack_elements에 결합 (무기 없어도)."""
    ctx = ActionContext(
        current_hp=100, max_hp=100, inventory=[], location="1층",
        absorbed_essences=[{
            "essence_name": "용암거인 정수", "stat_bundle": {}, "skills": [],
            "grade": 5, "resistances": {}, "etc_abilities": [],
            "attack_elements": ["불"],
        }],
    )
    elements = _get_attack_elements(ctx)
    assert "물리" in elements
    assert "불" in elements  # ★ 정수 element 결합 (무기 X여도)


def test_fire_element_triggers_undead_weakness() -> None:
    """불 공격 → undead 약점 1.5x (★ 13deef0 정합)."""
    undead = enemy_from_dict({"name": "스켈레톤", "enemy_type": "undead"})
    # undead weakness_types = [신성력, 불] (13deef0 자동 유도)
    assert compute_damage_multiplier(undead, ["물리", "불"]) == 1.5


def test_cold_element_no_weakness() -> None:
    """냉기 공격 → undead 약점 아님 (1.0x) — thematic only."""
    undead = enemy_from_dict({"name": "스켈레톤", "enemy_type": "undead"})
    assert compute_damage_multiplier(undead, ["물리", "냉기"]) == 1.0
