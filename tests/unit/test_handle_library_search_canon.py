"""handle_library_search — canon entity keyword match 검증 (I-D1)."""

from __future__ import annotations

import asyncio

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Character, Essence, Location, Mechanism, Race
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_library_search


def _ctx(user_input: str) -> ActionContext:
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="도서관",
        user_input=user_input,
    )


def _facts_with_entities() -> CanonFacts:
    return CanonFacts(
        essences=[
            Essence(name="고블린 정수", grade=3, skills_granted=["덫 생성"]),
        ],
        characters=[
            Character(name="셰인", role="동료", race="인간", background="전직 기사"),
        ],
        locations=[
            Location(name="1층 입구", location_type="dungeon", description="던전 1층 시작점"),
        ],
        races=[Race(name="고블린", description="소형 마물")],
        mechanisms=[
            Mechanism(
                name="정수 흡수",
                category="progression",
                description="몬스터 정수를 흡수해 능력 획득",
            ),
        ],
    )


@pytest.fixture(autouse=True)
def _index() -> object:
    set_entity_index(EntityIndex(_facts_with_entities()))
    yield
    clear_entity_index()


def test_library_keyword_match_essence() -> None:
    """essence keyword → narrative에 entity name 포함."""
    result = asyncio.run(
        handle_library_search(_ctx("고블린에 대해 찾아본다"))
    )
    assert "고블린" in result.narrative


def test_library_keyword_match_mechanism() -> None:
    """mechanism keyword → narrative에 포함."""
    result = asyncio.run(
        handle_library_search(_ctx("정수 흡수에 대한 기록"))
    )
    assert "정수 흡수" in result.narrative


def test_library_no_match_fallback() -> None:
    """매칭 없는 input → fallback narrative."""
    result = asyncio.run(
        handle_library_search(_ctx("xyzqwerty12345"))
    )
    assert "별다른 관련 기록" in result.narrative


def test_library_time_advance_two() -> None:
    result = asyncio.run(
        handle_library_search(_ctx("정수 흡수 조사"))
    )
    assert result.time_advance == 2


def test_library_no_index_fallback() -> None:
    """entity_index=None → fallback."""
    clear_entity_index()
    result = asyncio.run(
        handle_library_search(_ctx("고블린 자료"))
    )
    assert "별다른 관련 기록" in result.narrative
