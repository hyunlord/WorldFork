"""Phase D step 6c — SpawnTable location-type + grade extended tests."""

from __future__ import annotations

from service.canon.schema import CanonFacts, Character, Location, Race
from service.canon.spawn import SpawnTable


def _facts(
    characters: list[dict[str, object]] | None = None,
    races: list[dict[str, object]] | None = None,
    locations: list[dict[str, object]] | None = None,
) -> CanonFacts:
    chars = [
        Character(
            name=str(c["name"]),
            role=str(c.get("role", "")),
            race=str(c["race"]) if c.get("race") else None,
        )
        for c in (characters or [])
    ]
    race_objs = [
        Race(
            name=str(r["name"]),
            description=str(r.get("description", "")) or None,
        )
        for r in (races or [])
    ]
    loc_objs = [
        Location(
            name=str(lc["name"]),
            location_type=str(lc.get("location_type", "dungeon")),  # type: ignore[arg-type]
            description=str(lc.get("description", "")) or None,
        )
        for lc in (locations or [])
    ]
    return CanonFacts(characters=chars, races=race_objs, locations=loc_objs)


# ─── _by_location_type via race description ───


def test_race_habitat_dungeon_builds_pool() -> None:
    facts = _facts(
        characters=[{"name": "굴 도적", "role": "도적", "race": "두더지족"}],
        races=[{"name": "두더지족", "description": "지하 동굴에 서식한다"}],
    )
    table = SpawnTable(facts)
    enemies = table.spawn_for_location("마탑", "dungeon", 1)
    assert len(enemies) >= 1


def test_race_template_enemy_in_wilderness() -> None:
    facts = _facts(
        races=[{"name": "늑대인간", "description": "숲과 산악에서 활동"}],
    )
    table = SpawnTable(facts)
    enemies = table.spawn_for_location("어느 숲", "wilderness", 1)
    assert len(enemies) >= 1


def test_spawn_for_location_type_fallback_to_floor() -> None:
    facts = _facts(
        characters=[{"name": "고블린 전사", "role": "적", "race": "고블린"}],
    )
    table = SpawnTable(facts)
    # 고블린 race → 1층/2층 floor mapping — dungeon type 요청 시 floor fallback
    enemies = table.spawn_for_location("마탑 1층", "dungeon", 1)
    assert len(enemies) >= 1


def test_spawn_for_location_default_fallback() -> None:
    facts = _facts()
    table = SpawnTable(facts)
    enemies = table.spawn_for_location("알 수 없는 장소", "rift", 1)
    assert len(enemies) >= 1  # fallback enemy


# ─── get_location_grade ───


def test_get_location_grade_exact_match() -> None:
    facts = _facts(locations=[{"name": "심층 구역", "location_type": "dungeon"}])
    table = SpawnTable(facts)
    grade = table.get_location_grade("심층 구역")
    assert grade == 7


def test_get_location_grade_partial_match() -> None:
    facts = _facts(locations=[{"name": "마탑 입구", "location_type": "dungeon"}])
    table = SpawnTable(facts)
    grade = table.get_location_grade("마탑 입구 앞")
    assert grade == 1


def test_get_location_grade_unknown_returns_3() -> None:
    facts = _facts()
    table = SpawnTable(facts)
    assert table.get_location_grade("완전 미지의 장소") == 3


def test_location_grades_built_for_all_locations() -> None:
    facts = _facts(
        locations=[
            {"name": "1층 입구", "location_type": "dungeon"},
            {"name": "5층 복도", "location_type": "dungeon"},
            {"name": "심층 코어", "location_type": "dungeon"},
        ]
    )
    table = SpawnTable(facts)
    assert table.get_location_grade("1층 입구") == 1
    assert table.get_location_grade("5층 복도") == 4
    assert table.get_location_grade("심층 코어") == 7


# ─── deep copy safety ───


def test_spawn_returns_independent_copies() -> None:
    facts = _facts(
        characters=[{"name": "오크", "role": "적", "race": "오크"}],
    )
    table = SpawnTable(facts)
    e1 = table.spawn_for_location("2층", n=1)[0]
    e2 = table.spawn_for_location("2층", n=1)[0]
    e1.hp = 0
    assert e2.hp > 0  # 독립 복사본


# ─── backward-compat: old single-arg signature ───


def test_spawn_for_location_single_arg_still_works() -> None:
    facts = _facts(
        characters=[{"name": "고블린", "role": "변이종 몬스터", "race": "고블린"}],
    )
    table = SpawnTable(facts)
    enemies = table.spawn_for_location("1층 입구")
    assert len(enemies) >= 1
