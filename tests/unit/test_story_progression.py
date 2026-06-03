"""스토리 진전 Rule Engine — 단계/플래그 전진 검증 (07 정합)."""

from __future__ import annotations

from service.sim.story_progression import (
    PHASE_DECLARATION,
    PHASE_DEPARTURE,
    PHASE_DUNGEON,
    PHASE_WEAPON_CHOICE,
    advance_story,
    phase_suggestions,
)
from service.sim.types import PlayerActionType


def test_weapon_chosen_advances_to_departure() -> None:
    phase, flags = advance_story(
        PHASE_WEAPON_CHOICE,
        {"chief_talked": True},
        PlayerActionType.EQUIP,
        None,
        chose_weapon=True,
    )
    assert flags["weapon_chosen"] is True
    assert phase == PHASE_DEPARTURE


def test_chief_dialogue_advances_to_weapon_choice() -> None:
    phase, flags = advance_story(
        PHASE_DECLARATION, {}, PlayerActionType.DIALOGUE, "부족장"
    )
    assert flags["chief_talked"] is True
    assert phase == PHASE_WEAPON_CHOICE


def test_non_chief_dialogue_no_advance() -> None:
    phase, flags = advance_story(
        PHASE_DECLARATION, {}, PlayerActionType.DIALOGUE, "행상인"
    )
    assert "chief_talked" not in flags
    assert phase == PHASE_DECLARATION


def test_dungeon_entry_jumps_to_dungeon() -> None:
    phase, _ = advance_story(
        PHASE_WEAPON_CHOICE, {}, PlayerActionType.ENTER_DUNGEON, None
    )
    assert phase == PHASE_DUNGEON


def test_phase_does_not_regress() -> None:
    # 던전 단계에서 부족장 대화해도 마을 단계로 되돌아가지 않음
    phase, _ = advance_story(
        PHASE_DUNGEON, {"chief_talked": True}, PlayerActionType.WAIT, None
    )
    assert phase == PHASE_DUNGEON


def test_phase_suggestions_differ_by_phase() -> None:
    decl = phase_suggestions(PHASE_DECLARATION, "부족장")
    weap = phase_suggestions(PHASE_WEAPON_CHOICE, "부족장")
    dep = phase_suggestions(PHASE_DEPARTURE, None)
    assert decl is not None and weap is not None and dep is not None
    # 단계마다 추천이 달라 정적 반복이 아님
    assert decl != weap != dep
    # weapon_choice 추천은 실제 무기명(추천 버튼 = 무기 선택지)
    assert any("도끼" in s or "검" in s or "창" in s for s in weap)
    assert any("미궁" in s for s in dep)
    # 던전 단계는 None → encounters 기반 fallback
    assert phase_suggestions(PHASE_DUNGEON, None) is None
