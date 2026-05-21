"""Phase D step 6d — essence_to_slot unit tests (canon effects 정합)."""

from __future__ import annotations

from service.canon.effects import essence_to_slot


def _raw(
    name: str = "테스트 정수",
    abilities: object = None,
    side_effects: object = None,
    skills_granted: object = None,
    grade: object = None,
) -> dict[str, object]:
    d: dict[str, object] = {"name": name}
    if abilities is not None:
        d["abilities"] = abilities
    if side_effects is not None:
        d["side_effects"] = side_effects
    if skills_granted is not None:
        d["skills_granted"] = skills_granted
    if grade is not None:
        d["grade"] = grade
    return d


def test_abilities_text_parsed() -> None:
    raw = _raw(abilities={"text": "절삭력+12, 민첩성+5"})
    slot = essence_to_slot(raw)
    assert slot.stat_bundle.get("attack_bonus", 0) == 12
    assert slot.stat_bundle.get("agility", 0) == 5


def test_skills_granted_mapped() -> None:
    raw = _raw(skills_granted=["도둑걸음 (P)", "독화살 (A)"])
    slot = essence_to_slot(raw)
    assert "도둑걸음 (P)" in slot.skills
    assert "독화살 (A)" in slot.skills


def test_grade_set() -> None:
    raw = _raw(grade=7)
    slot = essence_to_slot(raw)
    assert slot.grade == 7


def test_side_effects_negative_stats() -> None:
    raw = _raw(
        abilities={"text": "물리 내성+30"},
        side_effects=["민첩성-20"],
    )
    slot = essence_to_slot(raw)
    assert slot.stat_bundle.get("defense_bonus", 0) == 30
    assert slot.stat_bundle.get("agility", 0) == -20


def test_empty_essence_no_crash() -> None:
    slot = essence_to_slot({"name": "미지의 정수"})
    assert slot.essence_name == "미지의 정수"
    assert slot.stat_bundle == {}
    assert slot.skills == []


def test_abilities_empty_dict() -> None:
    slot = essence_to_slot(_raw(abilities={}))
    assert slot.stat_bundle == {}
