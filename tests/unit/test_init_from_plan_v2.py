"""init_from_plan + state_v2 통합 테스트.

본인 본질 (2026-05-07):
'state_v2 진짜 service 통합' → Made But Never Used 차단.
"""

from __future__ import annotations

from service.game.init_from_plan import (
    _detect_race_from_plan,
    _detect_sub_race_from_plan,
    build_game_context,
    init_game_state_from_plan,
    init_v2_characters_from_plan,
    plan_character_to_v2,
)
from service.game.state_v2 import BeastkinTribe, Race
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


def _make_barbarian_plan() -> Plan:
    return Plan(
        work_name="barbarian_test",
        work_genre="판타지",
        main_character=CharacterPlan(
            name="투르윈",
            role="바바리안 부족장",
            description="주인공",
        ),
        supporting_characters=[
            CharacterPlan(
                name="미샤",
                role="적묘족 수인",
                description="동료",
            ),
            CharacterPlan(
                name="이름없음",
                role="알 수 없는 존재",
                description="미스터리",
            ),
        ],
        world=WorldSetting(
            setting_name="라스카니아",
            genre="판타지",
            tone="진지",
            rules=["미궁 존재"],
        ),
        opening_scene="투르윈은 미궁 1층에 서 있다.",
        initial_choices=["내려가기"],
        ip_masking_applied=True,
    )


# ─── _detect_race_from_plan ───


def test_detect_race_barbarian() -> None:
    assert _detect_race_from_plan("바바리안 전사") == Race.BARBARIAN
    assert _detect_race_from_plan("Barbarian Warrior") == Race.BARBARIAN


def test_detect_race_beastkin() -> None:
    assert _detect_race_from_plan("수인 도적") == Race.BEASTKIN
    assert _detect_race_from_plan("적묘족 수인") == Race.BEASTKIN


def test_detect_race_dwarf_human() -> None:
    assert _detect_race_from_plan("드워프 대장장이") == Race.DWARF
    assert _detect_race_from_plan("인간 마법사") == Race.HUMAN


def test_detect_race_unknown_returns_none() -> None:
    assert _detect_race_from_plan("미스터리한 존재") is None


# ─── _detect_sub_race_from_plan ───


def test_detect_sub_race_red_cat() -> None:
    assert _detect_sub_race_from_plan("적묘족 수인") == BeastkinTribe.RED_CAT


def test_detect_sub_race_known_tribes() -> None:
    assert _detect_sub_race_from_plan("백랑족") == BeastkinTribe.WHITE_WOLF
    assert _detect_sub_race_from_plan("흑곰족") == BeastkinTribe.BLACK_BEAR
    assert _detect_sub_race_from_plan("청랑족") == BeastkinTribe.BLUE_WOLF
    assert _detect_sub_race_from_plan("백토족") == BeastkinTribe.WHITE_RABBIT


def test_detect_sub_race_generic_returns_none() -> None:
    assert _detect_sub_race_from_plan("일반 수인") is None


# ─── plan_character_to_v2 ───


def test_plan_character_to_v2_barbarian() -> None:
    cp = CharacterPlan(name="비요른", role="주인공", description="바바리안")
    v2 = plan_character_to_v2(cp)
    assert v2.name == "비요른"
    assert v2.is_player is True
    assert v2.hp == 100
    assert v2.hp_max == 100
    # role에 "바바리안" 직접 명시 X (★ "주인공"만) → race=HUMAN fallback
    assert v2.race == Race.HUMAN


def test_plan_character_to_v2_explicit_barbarian() -> None:
    cp = CharacterPlan(
        name="투르윈", role="바바리안 부족장", description="주인공"
    )
    v2 = plan_character_to_v2(cp)
    assert v2.race == Race.BARBARIAN
    assert v2.sub_race is None
    assert v2.is_player is False  # role != "주인공"


def test_plan_character_to_v2_beastkin_with_tribe() -> None:
    cp = CharacterPlan(name="미샤", role="적묘족 수인", description="동료")
    v2 = plan_character_to_v2(cp)
    assert v2.race == Race.BEASTKIN
    assert v2.sub_race == BeastkinTribe.RED_CAT


# ─── init_v2_characters_from_plan ───


def test_init_v2_characters_from_plan_main_and_supporting() -> None:
    plan = _make_barbarian_plan()
    v2 = init_v2_characters_from_plan(plan)
    assert "투르윈" in v2
    assert "미샤" in v2
    assert "이름없음" in v2
    assert v2["투르윈"].race == Race.BARBARIAN
    assert v2["미샤"].race == Race.BEASTKIN
    assert v2["미샤"].sub_race == BeastkinTribe.RED_CAT
    assert v2["이름없음"].race == Race.HUMAN  # fallback


# ─── build_game_context — v2_characters 진짜 포함 ───


def test_build_game_context_includes_v2_characters() -> None:
    """★ 진짜 service 통합 검증 — Made But Never Used 차단."""
    plan = _make_barbarian_plan()
    state = init_game_state_from_plan(plan)
    ctx = build_game_context(plan, state)

    assert "v2_characters" in ctx
    v2c = ctx["v2_characters"]
    assert "투르윈" in v2c
    assert v2c["투르윈"]["race"] == "바바리안"
    assert v2c["투르윈"]["essence_slot_max"] == 5
    assert v2c["투르윈"]["hp"] == 100
    assert v2c["미샤"]["sub_race"] == "적묘족"
