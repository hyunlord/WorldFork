"""handle_explore — canon location description 활용 검증 (I-F1)."""

from __future__ import annotations

import asyncio

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Location
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_explore


def _ctx(location: str) -> ActionContext:
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location=location,
        user_input="주변을 살핀다",
    )


def _facts_with_location() -> CanonFacts:
    return CanonFacts(
        essences=[],
        characters=[],
        locations=[
            Location(
                name="라스카니아",
                location_type="dungeon",
                description="재상이 과거 재상이었던 국가/도시.",
                sub_locations=["도시 아래 (상하수도 설비)", "집무실", "차원광장"],
            ),
            Location(
                name="빈 장소",
                location_type="dungeon",
                description=None,
                sub_locations=[],
            ),
        ],
        races=[],
        mechanisms=[],
    )


@pytest.fixture(autouse=True)
def _index() -> object:
    set_entity_index(EntityIndex(_facts_with_location()))
    yield
    clear_entity_index()


def test_explore_uses_canon_description() -> None:
    """canon description → narrative에 포함."""
    result = asyncio.run(
        handle_explore(_ctx("라스카니아"))
    )
    assert "라스카니아" in result.narrative
    assert "재상" in result.narrative


def test_explore_includes_sub_locations() -> None:
    """sub_locations → narrative hint 포함."""
    result = asyncio.run(
        handle_explore(_ctx("라스카니아"))
    )
    assert "집무실" in result.narrative or "차원광장" in result.narrative


def test_explore_fallback_no_description() -> None:
    """description=None → fallback narrative."""
    result = asyncio.run(
        handle_explore(_ctx("빈 장소"))
    )
    assert "빈 장소" in result.narrative
    assert "세세한 것들을 포착" in result.narrative


def test_explore_fallback_unknown_location() -> None:
    """canon 없는 location → fallback narrative."""
    result = asyncio.run(
        handle_explore(_ctx("알 수 없는 위치"))
    )
    assert "알 수 없는 위치" in result.narrative
    assert "세세한 것들을 포착" in result.narrative


def test_explore_time_advance_two() -> None:
    """time_advance=2 고정."""
    result = asyncio.run(
        handle_explore(_ctx("라스카니아"))
    )
    assert result.time_advance == 2
