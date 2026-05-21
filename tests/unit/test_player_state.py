"""Phase D step 6d — player_state unit tests."""

from __future__ import annotations

from service.sim.player_state import (
    EssenceSlot,
    compute_total_skills,
    compute_total_stats,
    slot_from_dict,
    slot_to_dict,
)

# ─── serialize round-trip ───


def test_slot_round_trip() -> None:
    s = EssenceSlot(
        essence_name="고블린 정수",
        stat_bundle={"strength": 5, "agility": -3},
        skills=["도둑걸음 (P)"],
        grade=9,
    )
    d = slot_to_dict(s)
    restored = slot_from_dict(d)
    assert restored.essence_name == "고블린 정수"
    assert restored.stat_bundle == {"strength": 5, "agility": -3}
    assert restored.skills == ["도둑걸음 (P)"]
    assert restored.grade == 9


def test_slot_from_dict_missing_fields() -> None:
    s = slot_from_dict({"essence_name": "테스트"})
    assert s.stat_bundle == {}
    assert s.skills == []
    assert s.grade is None


# ─── compute_total_stats ───


def test_total_stats_sum_positive() -> None:
    slots = [
        EssenceSlot("A", stat_bundle={"strength": 10}),
        EssenceSlot("B", stat_bundle={"strength": 5, "agility": 20}),
    ]
    total = compute_total_stats(slots)
    assert total["strength"] == 15
    assert total["agility"] == 20


def test_total_stats_negative_reduces() -> None:
    slots = [
        EssenceSlot("킹슬라임 정수", stat_bundle={"strength": -5, "resistance": 20}),
    ]
    total = compute_total_stats(slots)
    assert total["strength"] == -5
    assert total["resistance"] == 20


def test_total_stats_empty_list() -> None:
    assert compute_total_stats([]) == {}


def test_total_stats_mixed_signs() -> None:
    slots = [
        EssenceSlot("A", stat_bundle={"agility": 30}),
        EssenceSlot("B", stat_bundle={"agility": -50}),
    ]
    total = compute_total_stats(slots)
    assert total["agility"] == -20


# ─── compute_total_skills ───


def test_total_skills_union_no_dup() -> None:
    slots = [
        EssenceSlot("A", skills=["스킬1", "스킬2"]),
        EssenceSlot("B", skills=["스킬2", "스킬3"]),
    ]
    skills = compute_total_skills(slots)
    assert set(skills) == {"스킬1", "스킬2", "스킬3"}
    assert len(skills) == 3


def test_total_skills_empty() -> None:
    assert compute_total_skills([]) == []
