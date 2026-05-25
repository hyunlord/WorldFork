"""EntityIndex.fuzzy_lookup 검증 (I-C2) — 조사 제거 + partial match."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex, _normalize
from service.canon.schema import CanonFacts, Character, Essence, Location, Mechanism, Race


def _facts() -> CanonFacts:
    return CanonFacts(
        essences=[
            Essence(name="고블린의 정수", grade=3, skills_granted=["덫 생성"]),
            Essence(name="오크 정수", grade=4),
        ],
        characters=[
            Character(name="셰인", aliases=["에쉬드"], role="동료", race="인간"),
            Character(name="투르윈", aliases=[], role="주인공"),
        ],
        locations=[
            Location(name="1층 입구", location_type="dungeon", description="시작 지점"),
        ],
        races=[Race(name="고블린", description="소형 마물")],
        mechanisms=[
            Mechanism(name="정수 흡수", category="progression", description="능력 획득"),
        ],
    )


@pytest.fixture(autouse=True)
def _index() -> object:
    idx = EntityIndex(_facts())
    set_entity_index(idx)
    yield idx
    clear_entity_index()


# ── _normalize ────────────────────────────────────────────────────────────────


def test_normalize_removes_ui_particle() -> None:
    assert _normalize("고블린의") == "고블린"


def test_normalize_removes_eul() -> None:
    assert _normalize("정수를") == "정수"


def test_normalize_removes_i_particle() -> None:
    assert _normalize("정수가") == "정수"


def test_normalize_removes_whitespace() -> None:
    assert _normalize("고블린 의 정수") == "고블린의정수"


def test_normalize_lowercase() -> None:
    assert _normalize("ABC") == "abc"


def test_normalize_empty() -> None:
    assert _normalize("") == ""


# ── fuzzy_lookup — exact ──────────────────────────────────────────────────────


def test_fuzzy_exact_match(request: pytest.FixtureRequest) -> None:
    """exact name → 즉시 반환."""
    idx: EntityIndex = request.getfixturevalue("_index")
    ref = idx.fuzzy_lookup("고블린의 정수")
    assert ref is not None
    assert ref.name == "고블린의 정수"


def test_fuzzy_exact_alias(request: pytest.FixtureRequest) -> None:
    """alias exact match."""
    idx: EntityIndex = request.getfixturevalue("_index")
    ref = idx.fuzzy_lookup("에쉬드")
    assert ref is not None
    assert ref.name == "셰인"


# ── fuzzy_lookup — normalized ─────────────────────────────────────────────────


def test_fuzzy_particle_missing(request: pytest.FixtureRequest) -> None:
    """'고블린 정수' → '고블린의 정수' (normalized 매칭)."""
    idx: EntityIndex = request.getfixturevalue("_index")
    ref = idx.fuzzy_lookup("고블린 정수")
    assert ref is not None
    assert ref.name == "고블린의 정수"


def test_fuzzy_no_space(request: pytest.FixtureRequest) -> None:
    """'고블린정수' → normalized 매칭."""
    idx: EntityIndex = request.getfixturevalue("_index")
    ref = idx.fuzzy_lookup("고블린정수")
    assert ref is not None
    assert "고블린" in ref.name


def test_fuzzy_short_name(request: pytest.FixtureRequest) -> None:
    """'셰인' → 셰인 character."""
    idx: EntityIndex = request.getfixturevalue("_index")
    ref = idx.fuzzy_lookup("셰인")
    assert ref is not None
    assert ref.name == "셰인"
    assert ref.entity_type == "character"


# ── fuzzy_lookup — partial ────────────────────────────────────────────────────


def test_fuzzy_partial_goblin(request: pytest.FixtureRequest) -> None:
    """'고블린' → 가장 긴 partial 매칭."""
    idx: EntityIndex = request.getfixturevalue("_index")
    ref = idx.fuzzy_lookup("고블린")
    assert ref is not None
    assert "고블린" in ref.name


# ── fuzzy_lookup — no match ───────────────────────────────────────────────────


def test_fuzzy_no_match(request: pytest.FixtureRequest) -> None:
    """완전 미매칭 → None."""
    idx: EntityIndex = request.getfixturevalue("_index")
    assert idx.fuzzy_lookup("xyzqwerty12345") is None


def test_fuzzy_empty_query(request: pytest.FixtureRequest) -> None:
    """빈 string → None."""
    idx: EntityIndex = request.getfixturevalue("_index")
    assert idx.fuzzy_lookup("") is None
