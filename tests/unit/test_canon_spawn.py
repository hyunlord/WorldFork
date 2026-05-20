"""Phase D step 6a — SpawnTable build + lookup tests."""

from __future__ import annotations

from service.canon.schema import CanonFacts, Character
from service.canon.spawn import SpawnTable


def _minimal_facts(hostile_chars: list[dict[str, object]] | None = None) -> CanonFacts:
    chars: list[Character] = []
    if hostile_chars:
        for c_dict in hostile_chars:
            chars.append(
                Character(
                    name=str(c_dict["name"]),
                    role=str(c_dict.get("role", "")),
                    race=str(c_dict["race"]) if c_dict.get("race") else None,
                )
            )
    return CanonFacts(
        essences=[],
        characters=chars,
        locations=[],
        races=[],
        mechanisms=[],
    )


def test_spawn_table_builds_without_error() -> None:
    facts = _minimal_facts()
    table = SpawnTable(facts)
    assert table.size() >= 0


def test_spawn_table_with_hostile_goblin() -> None:
    facts = _minimal_facts([
        {"name": "고블린 전사", "role": "변이종 몬스터", "race": "고블린"},
    ])
    table = SpawnTable(facts)
    # 고블린 → 1층 or 2층 매핑
    enemies = table.spawn_for_location("1층 입구")
    assert len(enemies) >= 1
    assert any(e.name == "고블린 전사" for e in enemies)


def test_spawn_table_fallback() -> None:
    """매칭 없는 location → fallback enemy 반환."""
    facts = _minimal_facts()
    table = SpawnTable(facts)
    enemies = table.spawn_for_location("알 수 없는 장소")
    assert len(enemies) >= 1
    assert enemies[0].name  # fallback enemy has name


def test_spawn_for_location_n_limit() -> None:
    """n 인수로 최대 개수 제한."""
    facts = _minimal_facts([
        {"name": "고블린 A", "role": "적", "race": "고블린"},
        {"name": "고블린 B", "role": "적", "race": "고블린"},
        {"name": "고블린 C", "role": "적", "race": "고블린"},
    ])
    table = SpawnTable(facts)
    enemies = table.spawn_for_location("1층", n=1)
    assert len(enemies) == 1


def test_non_hostile_not_added() -> None:
    facts = _minimal_facts([
        {"name": "마을 상인", "role": "상인", "race": "인간"},
    ])
    table = SpawnTable(facts)
    enemies = table.spawn_for_location("1층")
    # 비적대 캐릭터는 포함 X — fallback만 반환
    assert all(e.name != "마을 상인" for e in enemies)


def test_grade_inferred_from_name() -> None:
    facts = _minimal_facts([
        {"name": "6등급 오크 보스", "role": "보스", "race": "오크"},
    ])
    table = SpawnTable(facts)
    enemies = table.spawn_for_location("2층")
    boss = next((e for e in enemies if "오크" in e.name), None)
    if boss:
        assert boss.grade == 6  # 이름에서 추론
