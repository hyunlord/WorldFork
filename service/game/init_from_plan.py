"""Plan → GameState 변환 (★ 자료 Stage 5 일부).

W2 D3에서 만든 Plan을 Tier 0 GameState로 변환.
Plan의 main_character / supporting_characters / opening_scene 활용.
"""

from typing import Any

from service.pipeline.types import Plan

from .state import Character, GameState, PhaseProgress


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


def build_game_context(plan: Plan, state: GameState) -> dict[str, Any]:
    """GM Agent용 Plan + State 컨텍스트."""
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
    }
