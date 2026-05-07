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
from .state_v2 import BeastkinTribe, Race
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


def plan_character_to_v2(cp: CharacterPlan) -> CharacterV2:
    """CharacterPlan → CharacterV2 (★ 진짜 service 통합).

    메인 3대 + 종족 + 기본 자원 채움.
    일반 세부 스탯 30+ / 특이 스탯 5는 다음 commit (2차 schema 보강).
    """
    race = _detect_race_from_plan(cp.role) or Race.HUMAN
    sub_race = (
        _detect_sub_race_from_plan(cp.role)
        if race == Race.BEASTKIN
        else None
    )

    return CharacterV2(
        name=cp.name,
        race=race,
        sub_race=sub_race,
        is_player=(cp.role == "주인공"),
        physical=10,
        mental=10,
        special=10,
        hp=100,
        hp_max=100,
        soul_power=0,
        soul_power_max=0,
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
    """
    v2_chars = init_v2_characters_from_plan(plan)
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
        "v2_characters": {
            name: {
                "race": c.race.value,
                "sub_race": c.sub_race.value if c.sub_race else None,
                "physical": c.physical,
                "mental": c.mental,
                "special": c.special,
                "hp": c.hp,
                "hp_max": c.hp_max,
                "essence_slot_max": c.essence_slot_max(),
                "is_player": c.is_player,
            }
            for name, c in v2_chars.items()
        },
    }
