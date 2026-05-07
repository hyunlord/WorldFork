"""init_from_plan + state_v2 통합 테스트.

본인 본질 (2026-05-07):
'state_v2 진짜 service 통합' → Made But Never Used 차단.
"""

from __future__ import annotations

from service.game.init_from_plan import (
    _detect_initial_floor_from_plan,
    _detect_initial_realm_from_plan,
    _detect_race_from_plan,
    _detect_sub_race_from_plan,
    _race_base_stats,
    build_game_context,
    init_game_state_from_plan,
    init_initial_location_from_plan,
    init_v2_characters_from_plan,
    init_world_state_from_plan,
    plan_character_to_v2,
)
from service.game.state_v2 import BeastkinTribe, Race, Realm
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


# ─── _race_base_stats (★ 2차 보강) ───


def test_race_base_stats_barbarian() -> None:
    """바바리안: 신체 강력 (★ 평균 2m 10cm, HP 150)."""
    base = _race_base_stats(Race.BARBARIAN)
    assert base["height"] == 210
    assert base["strength"] == 16
    assert base["mental"] == 14
    assert base["hp"] == 150


def test_race_base_stats_beastkin() -> None:
    """수인: 민첩 + 육감 ↑."""
    base = _race_base_stats(Race.BEASTKIN)
    assert base["agility"] >= 12
    assert base["sixth_sense"] >= 10


def test_race_base_stats_faerie() -> None:
    """요정: 마법 ↑ (★ special 14, soul_power 60)."""
    base = _race_base_stats(Race.FAERIE)
    assert base["special"] == 14
    assert base["soul_power"] == 60


def test_race_base_stats_human_default() -> None:
    """인간 기본 (★ 170cm 70kg)."""
    base = _race_base_stats(Race.HUMAN)
    assert base["height"] == 170
    assert base["weight"] == 70
    assert base["physical"] == 10


def test_plan_character_to_v2_barbarian_full_stats() -> None:
    """바바리안 변환 시 base 진짜 적용."""
    cp = CharacterPlan(
        name="비요른", role="바바리안 부족장", description="주인공"
    )
    v2 = plan_character_to_v2(cp)
    assert v2.race == Race.BARBARIAN
    assert v2.height == 210
    assert v2.strength == 16
    assert v2.hp == 150
    assert v2.hp_max == 150


def test_plan_character_to_v2_beastkin_sixth_sense() -> None:
    """수인 변환 시 sixth_sense 10."""
    cp = CharacterPlan(name="미샤", role="적묘족 수인", description="동료")
    v2 = plan_character_to_v2(cp)
    assert v2.sixth_sense == 10
    assert v2.agility == 14


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
    assert v2c["투르윈"]["hp"] == 150  # ★ 바바리안 HP
    assert v2c["미샤"]["sub_race"] == "적묘족"


def test_build_game_context_includes_general_and_special_stats() -> None:
    """★ 일반 30+ + 특이 5 진짜 노출 (★ Layer 4 본질)."""
    plan = _make_barbarian_plan()
    state = init_game_state_from_plan(plan)
    ctx = build_game_context(plan, state)

    v2c = ctx["v2_characters"]
    bar = v2c["투르윈"]
    # 1티어
    assert bar["strength"] == 16
    assert bar["agility"] == 10
    assert bar["flexibility"] == 8
    # 신체
    assert bar["height"] == 210
    assert bar["weight"] == 110
    # 특이 스탯 진짜 dict에 (★ 0 시작)
    assert bar["obsession"] == 0
    assert bar["sixth_sense"] == 5  # ★ 바바리안 base 5
    assert bar["support_rating"] == 0
    assert bar["perception_interference"] == 0


# ─── Stage 1: Realm / Location / WorldState (★ 2026-05-07) ───


def _make_dungeon_plan(opening: str = "1층 미궁") -> Plan:
    return Plan(
        work_name="dungeon_test",
        work_genre="판타지",
        main_character=CharacterPlan(
            name="비요른", role="바바리안 부족장", description="주인공"
        ),
        supporting_characters=[
            CharacterPlan(name="에르웬", role="요정 동료", description="동료"),
        ],
        world=WorldSetting(
            setting_name="라스카니아",
            genre="판타지",
            tone="진지",
            rules=["미궁 존재"],
        ),
        opening_scene=opening,
        initial_choices=["진입"],
        ip_masking_applied=True,
    )


def test_detect_realm_dungeon() -> None:
    plan = _make_dungeon_plan("비요른은 미궁 1층 동굴에서 깨어난다")
    assert _detect_initial_realm_from_plan(plan) == Realm.DUNGEON


def test_detect_realm_city() -> None:
    plan = _make_dungeon_plan("라프도니아 도시 광장에서 출발한다")
    assert _detect_initial_realm_from_plan(plan) == Realm.CITY


def test_detect_realm_rift() -> None:
    plan = _make_dungeon_plan("균열 입구에 들어선다")
    assert _detect_initial_realm_from_plan(plan) == Realm.RIFT


def test_detect_initial_floor() -> None:
    plan = _make_dungeon_plan("3층 마녀의 숲에서")
    assert _detect_initial_floor_from_plan(plan) == 3


def test_detect_initial_floor_default_1() -> None:
    plan = _make_dungeon_plan("미궁 진입")
    assert _detect_initial_floor_from_plan(plan) == 1


def test_init_world_state_dungeon_dark() -> None:
    """1층 시작 시 is_dark_zone 진짜 True."""
    plan = _make_dungeon_plan("1층 동굴에서 시작")
    ws = init_world_state_from_plan(plan)
    assert ws.is_dark_zone
    assert "비요른" in ws.party_members
    assert "에르웬" in ws.party_members


def test_init_world_state_city_no_dark() -> None:
    """도시 시작 시 is_dark_zone False."""
    plan = _make_dungeon_plan("라프도니아 도시")
    ws = init_world_state_from_plan(plan)
    assert not ws.is_dark_zone


def test_init_initial_location_dungeon_default_dark() -> None:
    """미궁 시작 시 어둠 + 가시거리 10m."""
    plan = _make_dungeon_plan("1층 미궁")
    loc = init_initial_location_from_plan(plan)
    assert loc.realm == Realm.DUNGEON
    assert loc.floor == 1
    assert not loc.has_light
    assert loc.visibility_meters == 10


def test_init_initial_location_city_with_light() -> None:
    """도시 시작 시 빛 활성 + 가시거리 100m."""
    plan = _make_dungeon_plan("라프도니아 도시 광장")
    loc = init_initial_location_from_plan(plan)
    assert loc.realm == Realm.CITY
    assert loc.has_light
    assert loc.visibility_meters == 100
    assert loc.floor is None  # 도시는 층 X


# ─── build_game_context — Stage 1 진짜 노출 ───


def test_build_game_context_includes_world_state() -> None:
    plan = _make_dungeon_plan("1층 미궁")
    state = init_game_state_from_plan(plan)
    ctx = build_game_context(plan, state)

    assert "v2_world_state" in ctx
    ws = ctx["v2_world_state"]
    assert ws["current_round"] == 1
    assert ws["is_dark_zone"]
    assert "비요른" in ws["party_members"]


def test_build_game_context_includes_initial_location() -> None:
    plan = _make_dungeon_plan("1층 미궁")
    state = init_game_state_from_plan(plan)
    ctx = build_game_context(plan, state)

    assert "v2_initial_location" in ctx
    loc = ctx["v2_initial_location"]
    assert loc["realm"] == "미궁"
    assert loc["floor"] == 1
    assert loc["visibility_meters"] == 10
    assert not loc["has_light"]
