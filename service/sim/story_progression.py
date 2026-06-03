"""스토리 진전 — 행동 결과로 단계/플래그를 전진시키는 Rule Engine (07 정합).

문서 07 '상태는 코드, 묘사는 LLM, 분기는 flags로' 정합:
- GM(gm_narrator)은 단계/플래그를 읽기만 한다(State Contract).
- 여기(Rule Engine)서만 행동 결과로 단계·플래그를 전진시킨다.

게임 엔진 2단계: 1단계(GM 루프)로 narrative는 맥락 따라 달라졌으나 세계가
정적이던 것을 해소 — 행동이 성인식 단계를 실제로 전진시킨다.
"""

from __future__ import annotations

from service.sim.types import PlayerActionType

# 성인식 단계 (★ ep_0002): 부족장 선언 → 무기 선택 → 성지 떠남 → 던전
PHASE_DECLARATION = "declaration"  # 부족장이 성년 선언, 무기 고르라 함
PHASE_WEAPON_CHOICE = "weapon_choice"  # 무기 선택 단계
PHASE_DEPARTURE = "departure"  # 무기 들고 성지 떠날 채비
PHASE_DUNGEON = "dungeon"  # 미궁 진입

PHASE_ORDER = (
    PHASE_DECLARATION,
    PHASE_WEAPON_CHOICE,
    PHASE_DEPARTURE,
    PHASE_DUNGEON,
)

# 던전 진입 계열 — 단계를 dungeon으로 점프
_DUNGEON_ENTRY = frozenset(
    {
        PlayerActionType.ENTER_DUNGEON,
        PlayerActionType.ENTER_RIFT,
        PlayerActionType.ENTER_NEXT_FLOOR,
    }
)

# 단계별 한국어 라벨 (GM 컨텍스트 / 추천용)
PHASE_LABEL: dict[str, str] = {
    PHASE_DECLARATION: "성인식 — 부족장의 성년 선언",
    PHASE_WEAPON_CHOICE: "성인식 — 무기 선택",
    PHASE_DEPARTURE: "성인식 — 성지를 떠날 채비",
    PHASE_DUNGEON: "미궁 탐험",
}


def advance_story(
    phase: str,
    flags: dict[str, bool],
    action_type: PlayerActionType,
    npc_name: str | None = None,
    chose_weapon: bool = False,
) -> tuple[str, dict[str, bool]]:
    """행동 결과 → (다음 단계, 갱신 플래그).

    - 부족장과 대화 → flags['chief_talked'] → declaration에서 weapon_choice로
    - 무기 선택(chose_weapon) → flags['weapon_chosen'] → departure로
    - 던전 진입 계열 → dungeon으로 점프
    플래그는 한 방향으로만 진행(되돌리지 않음).
    """
    new_flags = dict(flags)

    if (
        action_type == PlayerActionType.DIALOGUE
        and npc_name
        and ("부족장" in npc_name or "촌장" in npc_name or "장로" in npc_name)
    ):
        new_flags["chief_talked"] = True
    if chose_weapon:
        new_flags["weapon_chosen"] = True

    new_phase = phase
    if action_type in _DUNGEON_ENTRY:
        new_phase = PHASE_DUNGEON
    elif chose_weapon and phase == PHASE_WEAPON_CHOICE:
        new_phase = PHASE_DEPARTURE
    elif phase == PHASE_DECLARATION and new_flags.get("chief_talked"):
        new_phase = PHASE_WEAPON_CHOICE

    return new_phase, new_flags


def phase_suggestions(phase: str, npc_name: str | None) -> list[str] | None:
    """단계별 추천 행동(있으면). 단계 진전을 유도하는 동적 추천.

    None 반환 시 호출자가 encounters 기반 기본 추천으로 fallback.
    """
    if phase == PHASE_DECLARATION:
        talk = f"{npc_name}에게 말을 건다" if npc_name else "부족장에게 말을 건다"
        return [talk, "주변을 둘러본다", "성년식을 지켜본다"]
    if phase == PHASE_WEAPON_CHOICE:
        # 추천 버튼이 곧 무기 선택지 — 대표 3종(별도 UI 없이 선택)
        return ["양손 도끼를 고른다", "한손 검을 고른다", "창을 고른다"]
    if phase == PHASE_DEPARTURE:
        return ["미궁으로 향한다", "마지막으로 성지를 둘러본다", "부족장에게 인사한다"]
    return None
