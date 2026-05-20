"""Phase D step 5 — EntityIndex unit tests."""

from __future__ import annotations

from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Character, Essence, Location, Mechanism, Race


def _make_facts() -> CanonFacts:
    return CanonFacts(
        essences=[
            Essence(
                name="마석 정수",
                grade=3,
                skills_granted=["강화", "방어"],
                absorption_mechanism="흡수 시 체력 +10",
            ),
        ],
        characters=[
            Character(
                name="투르윈",
                aliases=["바바리안", "주인공"],
                role="주인공",
                race="인간",
                grade=None,
                background="이계에서 전이된 바바리안",
            ),
        ],
        locations=[
            Location(
                name="1층 입구",
                location_type="dungeon",
                description="균열 던전 1층 입구",
            ),
        ],
        races=[
            Race(name="정령", description="자연 정령 종족"),
        ],
        mechanisms=[
            Mechanism(
                name="정수 흡수",
                category="magic",
                description="몬스터 정수를 흡수해 능력치 강화",
            ),
        ],
    )


def test_lookup_by_name_essence() -> None:
    idx = EntityIndex(_make_facts())
    ref = idx.lookup_by_name("마석 정수")
    assert ref is not None
    assert ref.entity_type == "essence"
    assert ref.name == "마석 정수"


def test_lookup_by_name_character() -> None:
    idx = EntityIndex(_make_facts())
    ref = idx.lookup_by_name("투르윈")
    assert ref is not None
    assert ref.entity_type == "character"


def test_lookup_by_alias() -> None:
    idx = EntityIndex(_make_facts())
    ref = idx.lookup_by_name("바바리안")
    assert ref is not None
    assert ref.name == "투르윈"


def test_lookup_by_name_missing() -> None:
    idx = EntityIndex(_make_facts())
    assert idx.lookup_by_name("없는캐릭터") is None


def test_lookup_many() -> None:
    idx = EntityIndex(_make_facts())
    refs = idx.lookup_many(["투르윈", "1층 입구", "없는것"])
    assert len(refs) == 2


def test_keyword_match_single() -> None:
    idx = EntityIndex(_make_facts())
    refs = idx.keyword_match("투르윈이 마석 정수를 흡수한다", limit=5)
    names = [r.name for r in refs]
    assert "투르윈" in names
    assert "마석 정수" in names


def test_keyword_match_limit() -> None:
    idx = EntityIndex(_make_facts())
    refs = idx.keyword_match("투르윈 바바리안 마석 정수 1층 입구 정령", limit=2)
    assert len(refs) <= 2


def test_keyword_match_longest_first() -> None:
    """긴 name이 먼저 반환되는지 확인."""
    facts = CanonFacts(
        essences=[],
        characters=[
            Character(
                name="투르윈 더 바바리안",
                aliases=[],
                role=None,
                race=None,
                grade=None,
                background=None,
            ),
            Character(
                name="투르윈",
                aliases=[],
                role=None,
                race=None,
                grade=None,
                background=None,
            ),
        ],
        locations=[],
        races=[],
        mechanisms=[],
    )
    idx = EntityIndex(facts)
    refs = idx.keyword_match("투르윈 더 바바리안의 이야기", limit=5)
    assert refs[0].name == "투르윈 더 바바리안"


def test_size() -> None:
    idx = EntityIndex(_make_facts())
    # 1 essence + 1 character (+ 2 aliases) + 1 location + 1 race + 1 mechanism
    assert idx.size() == 7


def test_empty_facts() -> None:
    idx = EntityIndex(CanonFacts(essences=[], characters=[], locations=[], races=[], mechanisms=[]))
    assert idx.size() == 0
    assert idx.keyword_match("anything") == []
    assert idx.lookup_by_name("x") is None
