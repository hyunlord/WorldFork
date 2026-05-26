"""EntityIndex source_monster lookup 단위 테스트."""

from __future__ import annotations

from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Essence


def _make_facts() -> CanonFacts:
    return CanonFacts(
        essences=[
            Essence(name="고블린 정수", grade=2, source_monster="고블린"),
            Essence(name="고블린", grade=1, source_monster="고블린"),
            Essence(name="오크 정수", grade=3, source_monster="오크"),
            Essence(name="고블린 궁수 정수", grade=3, source_monster="고블린 궁수"),
            Essence(name="서리늑대의 정수", grade=4, source_monster="서리늑대"),
            Essence(name="서리늑대 정수", grade=5, source_monster="서리늑대"),
        ],
        characters=[],
        locations=[],
        races=[],
        mechanisms=[],
    )


def test_get_essences_by_source_monster_basic() -> None:
    idx = EntityIndex(_make_facts())
    result = idx.get_essences_by_source_monster("고블린")
    assert len(result) == 2
    names = {r["name"] for r in result}
    assert names == {"고블린 정수", "고블린"}


def test_get_essences_by_source_monster_unknown() -> None:
    idx = EntityIndex(_make_facts())
    assert idx.get_essences_by_source_monster("드래곤") == []


def test_get_primary_essence_prefers_jeongsoo() -> None:
    idx = EntityIndex(_make_facts())
    primary = idx.get_primary_essence_for_monster("고블린")
    assert primary is not None
    assert "정수" in str(primary["name"])


def test_get_primary_essence_no_match() -> None:
    idx = EntityIndex(_make_facts())
    assert idx.get_primary_essence_for_monster("드래곤") is None


def test_get_primary_essence_single() -> None:
    idx = EntityIndex(_make_facts())
    primary = idx.get_primary_essence_for_monster("오크")
    assert primary is not None
    assert primary["name"] == "오크 정수"


def test_get_primary_essence_highest_grade() -> None:
    idx = EntityIndex(_make_facts())
    primary = idx.get_primary_essence_for_monster("서리늑대")
    assert primary is not None
    assert primary["grade"] == 5
    assert primary["name"] == "서리늑대 정수"
