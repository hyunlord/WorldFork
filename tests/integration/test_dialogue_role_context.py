"""handle_dialogue role context 정합 통합 테스트 (★ I-E2 runtime)."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Character
from service.sim.action_context import ActionContext
from service.sim.action_handlers import ROLE_TONE_HINTS, handle_dialogue


def _make_index_with_roles() -> EntityIndex:
    facts = CanonFacts(
        essences=[],
        characters=[
            Character(name="에르웬", role="동료", background="요정족 파티원"),
            Character(name="DC 유저", role="메타", background="커뮤니티 작성자"),
            Character(name="대장장이 한스", role="주민",
                      background="라스카니아 대장장이"),
        ],
        locations=[], races=[], mechanisms=[],
    )
    return EntityIndex(facts)


def _ctx_with_npc(npc_name: str, user_input: str = "안녕") -> ActionContext:
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="라스카니아",
        encounters=[{"name": npc_name, "hostile": False, "is_hostile": False}],
        user_input=user_input,
    )


@pytest.fixture(autouse=True)
def _cleanup_index() -> object:
    yield
    clear_entity_index()


@pytest.mark.asyncio
async def test_meta_character_dialogue_rejected() -> None:
    """메타 character → dialogue 거부 narrative."""
    set_entity_index(_make_index_with_roles())
    ctx = _ctx_with_npc("DC 유저")
    result = await handle_dialogue(ctx)
    assert result.success is False
    assert result.fail_reason == "meta_character"
    assert "본문 외" in result.narrative


@pytest.mark.asyncio
async def test_companion_dialogue_proceeds() -> None:
    """동료 character → 정상 dialogue (template fallback)."""
    set_entity_index(_make_index_with_roles())
    ctx = _ctx_with_npc("에르웬", user_input="안녕")
    result = await handle_dialogue(ctx)
    # 짧은 인사 → template path
    assert result.success is not False
    assert "에르웬" in result.narrative
    assert result.affinity_changes == {"에르웬": 1}


def test_role_tone_hints_taxonomy_coverage() -> None:
    """ROLE_TONE_HINTS dict — 메타/주인공 제외 4 taxonomy 정합."""
    assert "동료" in ROLE_TONE_HINTS
    assert "주요 NPC" in ROLE_TONE_HINTS
    assert "주민" in ROLE_TONE_HINTS
    assert "엑스트라" in ROLE_TONE_HINTS
    # 주인공 / 메타 — dialogue 대상 X
    assert "주인공" not in ROLE_TONE_HINTS
    assert "메타" not in ROLE_TONE_HINTS
