"""Plan → GameState 변환 (★ 자료 Stage 5 일부).

W2 D3에서 만든 Plan을 Tier 0 GameState로 변환.
Plan의 main_character / supporting_characters / opening_scene 활용.

★ Tier 2 D12+ 보강 (2026-05-07):
state_v2 진짜 service 통합 (Made But Never Used 차단).
build_game_context()가 v2 character 정보를 GM context에 포함.
"""

from typing import Any

from service.pipeline.types import CharacterPlan, Plan

from .state import Character, GameState, PhaseProgress
from .state_v2 import BeastkinTribe, Location, Race, Realm, WorldState
from .state_v2 import Character as CharacterV2


def init_game_state_from_plan(
    plan: Plan,
    scenario_id: str | None = None,
) -> GameState:
    """Plan → GameState 초기화."""
    sid = scenario_id or plan.work_name or "unknown"

    characters: dict[str, Character] = {}

    mc = Character(
        name=plan.main_character.name,
        role=plan.main_character.role,
        hp=100,
        inventory=[],
    )
    characters[mc.name] = mc

    for sc in plan.supporting_characters:
        characters[sc.name] = Character(
            name=sc.name,
            role=sc.role,
            hp=100,
            inventory=[],
        )

    location = _extract_initial_location(plan.opening_scene)

    return GameState(
        scenario_id=sid,
        turn=0,
        location=location,
        characters=characters,
        history=[],
        phase_progress=PhaseProgress(
            current_phase_id="phase_1_opening",
            completed_triggers=[],
            phase_started_turn=0,
        ),
        selected_ending=None,
    )


def _extract_initial_location(opening_scene: str) -> str:
    """opening_scene에서 위치 추출 (간단 휴리스틱)."""
    if not opening_scene:
        return "unknown"

    first_sentence = opening_scene.split(".")[0].split("。")[0]

    location_keywords = [
        "던전", "마을", "성", "숲", "산", "강", "바다",
        "도시", "왕국", "사원", "동굴", "탑",
        "입구", "광장", "거리", "여관",
    ]

    for kw in location_keywords:
        if kw in first_sentence:
            idx = first_sentence.find(kw)
            start = max(0, idx - 10)
            end = min(len(first_sentence), idx + len(kw) + 5)
            return first_sentence[start:end].strip()

    return first_sentence[:30].strip()


def _detect_race_from_plan(role: str) -> Race | None:
    """Plan character role에서 종족 추정 (★ 작품 매칭).

    예: "바바리안 전사" → Race.BARBARIAN
        "적묘족 수인" → Race.BEASTKIN
        명시 X → None (★ 호환).
    """
    role_lower = role.lower()
    if "바바리안" in role or "barbarian" in role_lower:
        return Race.BARBARIAN
    if "드워프" in role or "dwarf" in role_lower:
        return Race.DWARF
    if "수인" in role or "beastkin" in role_lower:
        return Race.BEASTKIN
    if "요정" in role or "faerie" in role_lower or "fairy" in role_lower:
        return Race.FAERIE
    if "용인" in role or "dragon" in role_lower:
        return Race.DRAGONKIN
    if "인간" in role or "human" in role_lower:
        return Race.HUMAN
    return None


def _detect_sub_race_from_plan(role: str) -> BeastkinTribe | None:
    """수인 부족 추정 (★ 5개 명시)."""
    if "적묘" in role:
        return BeastkinTribe.RED_CAT
    if "백랑" in role:
        return BeastkinTribe.WHITE_WOLF
    if "흑곰" in role:
        return BeastkinTribe.BLACK_BEAR
    if "청랑" in role:
        return BeastkinTribe.BLUE_WOLF
    if "백토" in role:
        return BeastkinTribe.WHITE_RABBIT
    return None


def _race_base_stats(race: Race) -> dict[str, int]:
    """종족별 기본 스탯 (★ 1차 자료 본질).

    바바리안: 신체 강력 (★ 평균 2m 10cm), 멘탈 강함
    수인: 민첩 + 감각 ↑, 육감 예민
    드워프: 골강도 ↑, 체구 작음
    요정: 마법 ↑
    용인족: 전반 ↑
    인간: 평균 (★ 170cm 70kg).

    Returns: 종족별 기본값 dict (★ 메인 3대 + 1티어 + 신체 + 자원 + 육감).
    """
    if race == Race.BARBARIAN:
        return {
            "physical": 14, "mental": 14, "special": 8,
            "strength": 16, "agility": 10, "flexibility": 8,
            "height": 210, "weight": 110,
            "hp": 150, "soul_power": 30,
            "sixth_sense": 5,
        }
    if race == Race.BEASTKIN:
        return {
            "physical": 12, "mental": 10, "special": 10,
            "strength": 12, "agility": 14, "flexibility": 12,
            "height": 175, "weight": 65,
            "hp": 110, "soul_power": 40,
            "sixth_sense": 10,
        }
    if race == Race.DWARF:
        return {
            "physical": 13, "mental": 11, "special": 9,
            "strength": 13, "agility": 9, "flexibility": 9,
            "height": 140, "weight": 70,
            "hp": 130, "soul_power": 30,
            "sixth_sense": 5,
        }
    if race == Race.FAERIE:
        return {
            "physical": 8, "mental": 12, "special": 14,
            "strength": 8, "agility": 12, "flexibility": 12,
            "height": 165, "weight": 50,
            "hp": 90, "soul_power": 60,
            "sixth_sense": 8,
        }
    if race == Race.DRAGONKIN:
        return {
            "physical": 14, "mental": 12, "special": 14,
            "strength": 14, "agility": 12, "flexibility": 12,
            "height": 185, "weight": 90,
            "hp": 140, "soul_power": 50,
            "sixth_sense": 10,
        }
    # HUMAN (기본)
    return {
        "physical": 10, "mental": 10, "special": 10,
        "strength": 10, "agility": 10, "flexibility": 10,
        "height": 170, "weight": 70,
        "hp": 100, "soul_power": 30,
        "sixth_sense": 0,
    }


def plan_character_to_v2(cp: CharacterPlan) -> CharacterV2:
    """CharacterPlan → CharacterV2 (★ 진짜 service 통합).

    종족별 기본값 적응 (★ ROADMAP V2 1차 자료 본질):
    - 바바리안: 신체 강력 (★ 평균 2m 10cm)
    - 수인: 민첩 + 감각 + sixth_sense
    - 드워프: 골강도 + 체구 작음
    - 요정: 마법 ↑
    - 용인족: 전반 ↑
    - 인간: 평균
    """
    race = _detect_race_from_plan(cp.role) or Race.HUMAN
    sub_race = (
        _detect_sub_race_from_plan(cp.role)
        if race == Race.BEASTKIN
        else None
    )

    base = _race_base_stats(race)

    return CharacterV2(
        name=cp.name,
        race=race,
        sub_race=sub_race,
        is_player=(cp.role == "주인공"),
        physical=base["physical"],
        mental=base["mental"],
        special=base["special"],
        strength=base["strength"],
        agility=base["agility"],
        flexibility=base["flexibility"],
        height=base["height"],
        weight=base["weight"],
        hp=base["hp"],
        hp_max=base["hp"],
        soul_power=base["soul_power"],
        soul_power_max=base["soul_power"],
        sixth_sense=base["sixth_sense"],
    )


def _detect_initial_realm_from_plan(plan: Plan) -> Realm:
    """Plan opening_scene → 초기 Realm 추정 (★ Stage 1).

    예: 미궁/동굴/N층 → DUNGEON
        도시/라프도니아/노아르크 → CITY
        균열 → RIFT
        지하 → UNDERGROUND
    기본: DUNGEON (★ 작품 본질, 시작 시 미궁 진입).
    """
    scene = plan.opening_scene or ""
    if "미궁" in scene or "동굴" in scene:
        return Realm.DUNGEON
    if any(f"{f}층" in scene for f in range(1, 11)):
        return Realm.DUNGEON
    if "도시" in scene or "라프도니아" in scene or "노아르크" in scene:
        return Realm.CITY
    if "균열" in scene:
        return Realm.RIFT
    if "지하" in scene:
        return Realm.UNDERGROUND
    return Realm.DUNGEON


def _detect_initial_floor_from_plan(plan: Plan) -> int | None:
    """Plan opening_scene → 초기 층 추정 (1-10)."""
    scene = plan.opening_scene or ""
    for f in range(1, 11):
        if f"{f}층" in scene:
            return f
    return 1  # ★ 작품 시작 = 1층 진입


def init_world_state_from_plan(plan: Plan) -> WorldState:
    """Plan → 초기 WorldState (★ Stage 1).

    - current_round 1
    - is_dark_zone = True (★ DUNGEON일 때만)
    - party_members = main + supporting
    """
    realm = _detect_initial_realm_from_plan(plan)
    party = [plan.main_character.name]
    for sc in plan.supporting_characters:
        party.append(sc.name)

    return WorldState(
        current_round=1,
        hours_in_dungeon=0,
        is_dimension_collapse=False,
        active_rifts=[],
        is_dark_zone=(realm == Realm.DUNGEON),
        party_members=party,
        party_share_ratios={},
    )


def init_initial_location_from_plan(plan: Plan) -> Location:
    """Plan → 초기 Location (★ Stage 1).

    - 1차 자료: DUNGEON 시작 = 어둠 + 가시거리 10m
    - CITY/UNDERGROUND = 빛 활성, 가시거리 100m
    """
    realm = _detect_initial_realm_from_plan(plan)
    floor = _detect_initial_floor_from_plan(plan)

    is_dungeon_like = realm in (Realm.DUNGEON, Realm.RIFT, Realm.HIDDEN_FIELD)
    return Location(
        realm=realm,
        floor=floor if is_dungeon_like else None,
        sub_area=None,
        rift_id=None,
        visibility_meters=10 if realm == Realm.DUNGEON else 100,
        has_light=(realm != Realm.DUNGEON),
    )


def init_v2_characters_from_plan(plan: Plan) -> dict[str, CharacterV2]:
    """Plan → v2 Character dict (★ state_v2 진짜 사용).

    main_character + supporting_characters 진짜 변환.
    """
    result: dict[str, CharacterV2] = {
        plan.main_character.name: plan_character_to_v2(plan.main_character)
    }
    for sc in plan.supporting_characters:
        result[sc.name] = plan_character_to_v2(sc)
    return result


def build_game_context(plan: Plan, state: GameState) -> dict[str, Any]:
    """GM Agent용 Plan + State 컨텍스트.

    ★ Tier 2 D12: v2_characters 포함 (★ state_v2 진짜 service 사용).
    ★ Stage 1 (2026-05-07): v2_world_state + v2_initial_location 진짜 포함.
    """
    v2_chars = init_v2_characters_from_plan(plan)
    v2_world = init_world_state_from_plan(plan)
    v2_loc = init_initial_location_from_plan(plan)
    return {
        "work_name": plan.work_name,
        "work_genre": plan.work_genre,
        "world_setting": plan.world.setting_name,
        "world_tone": plan.world.tone,
        "world_rules": plan.world.rules,
        "main_character_name": plan.main_character.name,
        "main_character_role": plan.main_character.role,
        "supporting_characters": [
            {"name": sc.name, "role": sc.role}
            for sc in plan.supporting_characters
        ],
        "current_location": state.location,
        "current_turn": state.turn,
        "user_preferences": plan.user_preferences,
        "ip_masking_applied": plan.ip_masking_applied,
        "language": "ko",
        "character_response": True,
        # ★ v2 schema 진짜 통합 (★ Made But Never Used 차단)
        # 메인 + 1티어 + 감각 + 방어 + 행운/기술 + 신체 + 마법 + 특이
        # → prompt에 진짜 노출 (★ Layer 4 본질)
        "v2_characters": {
            name: {
                "race": c.race.value,
                "sub_race": c.sub_race.value if c.sub_race else None,
                # 메인 3대
                "physical": c.physical,
                "mental": c.mental,
                "special": c.special,
                # 1티어
                "strength": c.strength,
                "agility": c.agility,
                "flexibility": c.flexibility,
                # 감각
                "sight": c.sight,
                "smell": c.smell,
                "hearing": c.hearing,
                "cognitive_speed": c.cognitive_speed,
                "accuracy": c.accuracy,
                "evasion": c.evasion,
                "jump_power": c.jump_power,
                # 방어
                "bone_strength": c.bone_strength,
                "bone_density": c.bone_density,
                "physical_resistance": c.physical_resistance,
                "durability": c.durability,
                "pain_resistance": c.pain_resistance,
                "poison_resistance": c.poison_resistance,
                "fire_resistance": c.fire_resistance,
                "cold_resistance": c.cold_resistance,
                "lightning_resistance": c.lightning_resistance,
                "dark_resistance": c.dark_resistance,
                # 행운/기술
                "luck": c.luck,
                "dexterity": c.dexterity,
                "cutting_power": c.cutting_power,
                "fighting_spirit": c.fighting_spirit,
                "endurance": c.endurance,
                "stamina": c.stamina,
                # 신체
                "height": c.height,
                "weight": c.weight,
                "regen_rate": c.regen_rate,
                "natural_regen": c.natural_regen,
                # 마법
                "magic_resistance": c.magic_resistance,
                "mental_power": c.mental_power,
                # 자원
                "hp": c.hp,
                "hp_max": c.hp_max,
                "soul_power": c.soul_power,
                "soul_power_max": c.soul_power_max,
                # ★ 특이 스탯 (★ 본인 짚은 본질)
                "obsession": c.obsession,
                "sixth_sense": c.sixth_sense,
                "support_rating": c.support_rating,
                "perception_interference": c.perception_interference,
                # 슬롯
                "essence_slot_max": c.essence_slot_max(),
                "is_player": c.is_player,
            }
            for name, c in v2_chars.items()
        },
        # ★ Stage 1: WorldState 진짜 노출 (★ Layer 4 본질)
        "v2_world_state": {
            "current_round": v2_world.current_round,
            "hours_in_dungeon": v2_world.hours_in_dungeon,
            "is_dimension_collapse": v2_world.is_dimension_collapse,
            "active_rifts": list(v2_world.active_rifts),
            "is_dark_zone": v2_world.is_dark_zone,
            "party_members": list(v2_world.party_members),
            "party_share_ratios": dict(v2_world.party_share_ratios),
        },
        # ★ Stage 1: Location 진짜 노출
        "v2_initial_location": {
            "realm": v2_loc.realm.value,
            "floor": v2_loc.floor,
            "sub_area": v2_loc.sub_area,
            "rift_id": v2_loc.rift_id,
            "visibility_meters": v2_loc.visibility_meters,
            "has_light": v2_loc.has_light,
        },
    }
