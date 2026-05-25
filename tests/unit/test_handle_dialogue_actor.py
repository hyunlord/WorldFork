"""handle_dialogue actor field 우선 NPC 선택 검증 (I-C1)."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from service.api.schemas.freeform_action import ExtractedEntities
from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Character
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_dialogue


def _facts() -> CanonFacts:
    return CanonFacts(
        essences=[],
        characters=[
            Character(name="셰인", aliases=[], role="동료", race="인간",
                      background="전직 기사"),
            Character(name="난쟁이놈", aliases=[], role="대장장이"),
        ],
        locations=[],
        races=[],
        mechanisms=[],
    )


@pytest.fixture(autouse=True)
def _index() -> object:
    set_entity_index(EntityIndex(_facts()))
    yield
    clear_entity_index()


def _ctx(
    user_input: str,
    actor: str | None = None,
    encounters: list[dict[str, object]] | None = None,
) -> ActionContext:
    ents = ExtractedEntities(actor=actor)
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층 입구",
        user_input=user_input,
        extracted_entities=ents,
        encounters=encounters or [],
    )


def test_actor_selects_matching_npc() -> None:
    """actor='셰인' → encounters 중 셰인 우선 선택."""
    ctx = _ctx(
        "셰인에게 인사한다",
        actor="셰인",
        encounters=[
            {"name": "난쟁이놈", "role": "대장장이", "hostile": False},
            {"name": "셰인", "role": "동료", "hostile": False},
        ],
    )
    result = asyncio.run(handle_dialogue(ctx))
    assert "셰인" in result.narrative
    assert result.success is True


def test_actor_skips_hostile() -> None:
    """actor 이름 NPC가 hostile=True 시 fallback."""
    ctx = _ctx(
        "셰인에게 인사한다",
        actor="셰인",
        encounters=[
            {"name": "셰인", "hostile": True},
            {"name": "난쟁이놈", "hostile": False},
        ],
    )
    result = asyncio.run(handle_dialogue(ctx))
    assert result.success is True
    # hostile 셰인 건너뛰고 난쟁이놈 선택
    assert "셰인" not in result.narrative or "난쟁이놈" in result.narrative


def test_actor_none_fallback_to_first_npc() -> None:
    """actor=None → 첫 비적대 NPC fallback."""
    ctx = _ctx(
        "인사한다",
        actor=None,
        encounters=[{"name": "난쟁이놈", "hostile": False}],
    )
    result = asyncio.run(handle_dialogue(ctx))
    assert "난쟁이놈" in result.narrative
    assert result.success is True


def test_actor_no_encounters_fail() -> None:
    """actor 있어도 encounters X → fail."""
    ctx = _ctx("셰인에게 인사한다", actor="셰인", encounters=[])
    result = asyncio.run(handle_dialogue(ctx))
    assert result.success is False
    assert result.fail_reason == "no_npc"


def test_actor_fuzzy_match_normalized() -> None:
    """actor='셰인을' (조사 포함) → fuzzy로 셰인 매칭."""
    ctx = _ctx(
        "셰인을 찾아간다",
        actor="셰인을",
        encounters=[{"name": "셰인", "hostile": False}],
    )
    result = asyncio.run(handle_dialogue(ctx))
    assert "셰인" in result.narrative
    assert result.success is True


def test_actor_affinity_increases() -> None:
    """dialogue 성공 → 선택된 NPC affinity +1."""
    ctx = _ctx(
        "셰인에게 인사한다",
        actor="셰인",
        encounters=[{"name": "셰인", "hostile": False}],
    )
    result = asyncio.run(handle_dialogue(ctx))
    assert result.affinity_changes.get("셰인") == 1


def test_deep_dialogue_with_actor_calls_27b() -> None:
    """actor + 깊은 대화 → 27B 호출."""
    ctx = _ctx(
        "셰인에게 던전 소식을 물어본다",
        actor="셰인",
        encounters=[{"name": "셰인", "hostile": False}],
    )
    with patch("service.sim.action_handlers.asyncio.to_thread") as mock_t:
        mock_t.return_value = "셰인이 조용히 입을 열었다."
        result = asyncio.run(handle_dialogue(ctx))
    mock_t.assert_called_once()
    assert result.narrative == "셰인이 조용히 입을 열었다."
