"""Tier 2 D12 — game-loop turn handler.

Stage 7 schema 진짜 production mutate (★ 본 commit 3차 — 12 ActionType 본격):
- Character.light_state (빛 자원 활성/소진/회복/consumables)
- Character.has_active_light (호출)
- Character.absorb_essence (호출)
- Character.is_alive / hp (HP 변동)
- WorldState.active_rifts / hours_in_dungeon

본 모듈은 LLM 호출 X — Mechanical mutate만.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .floors.floor1 import get_floor1_definition
from .state_v2 import (
    Character,
    Essence,
    EssenceColor,
    EssenceGrade,
    EssenceOrigin,
    EssenceType,
    Location,
    WorldState,
)


@dataclass
class TurnResult:
    """Turn 처리 결과."""

    success: bool
    action_type: str
    message: str
    side_effects: list[str] = field(default_factory=list)


# ─── 1. WAIT / 시간 흐름 ───


def advance_time(
    characters: list[Character],
    world: WorldState,
    elapsed_hours: float,
) -> TurnResult:
    """시간 흐름 — 빛 자원 차감 + cooldown 회복 + 미궁 시간 누적.

    - light_state.remaining_duration_hours 차감
    - 정령 자원 소진 시 cooldown 2h 진입 (★ 11화)
    - 사망자는 처리 X
    """
    side: list[str] = []

    for c in characters:
        if not c.is_alive():
            continue

        ls = c.light_state

        # 기존 cooldown 먼저 차감 (신규 cooldown 진입 분리)
        if ls.cooldown_remaining_hours > 0:
            ls.cooldown_remaining_hours = max(
                0.0, ls.cooldown_remaining_hours - elapsed_hours
            )
            if ls.cooldown_remaining_hours == 0.0:
                side.append(f"{c.name}의 정령 회복 완료.")

        if ls.active_source_name and ls.remaining_duration_hours > 0:
            ls.remaining_duration_hours = max(
                0.0, ls.remaining_duration_hours - elapsed_hours
            )
            if ls.remaining_duration_hours == 0.0:
                spent = ls.active_source_name
                ls.active_source_name = None
                if "정령" in spent:
                    ls.cooldown_remaining_hours = 2.0  # ★ 11화
                side.append(f"{c.name}의 {spent} 소진.")

    world.hours_in_dungeon += int(elapsed_hours)

    return TurnResult(
        success=True,
        action_type="wait",
        message=f"{elapsed_hours}시간 경과.",
        side_effects=side,
    )


# ─── 2. 빛 활성 ───


def activate_light(
    character: Character,
    source_name: str,
) -> TurnResult:
    """빛 자원 활성 (★ Floor1Definition 검색 + 종족 한정).

    - 횃불 (★ 누구나, 72h, 1만 스톤)
    - 정령 등불 (★ 요정 한정, 10h, 회복 2h)
    - 조명탄 (★ 50m 단발)
    """
    f1 = get_floor1_definition()
    source = next((ls for ls in f1.light_sources if ls.name == source_name), None)

    if source is None:
        return TurnResult(
            success=False,
            action_type="activate_light",
            message=(
                f"{source_name} 자원 없음 "
                "(★ 1층 빛 자원: 횃불/정령 등불/조명탄)."
            ),
        )

    if source.requires_race is not None:
        if character.race.value != source.requires_race:
            return TurnResult(
                success=False,
                action_type="activate_light",
                message=(
                    f"{character.name}({character.race.value})는 "
                    f"{source.name} 사용 X ({source.requires_race} 한정)."
                ),
            )

    if source.is_consumable:
        cur = character.light_state.consumables.get(source.name, 0)
        if cur <= 0:
            return TurnResult(
                success=False,
                action_type="activate_light",
                message=f"{source.name} 보유 X.",
            )
        character.light_state.consumables[source.name] = cur - 1

    character.light_state.active_source_name = source.name
    character.light_state.remaining_duration_hours = source.duration_hours or 0.0

    side: list[str] = [f"가시거리 {source.radius_meters}m"]
    if source.duration_hours:
        side.append(f"지속 {source.duration_hours}h")
    else:
        side.append("단발")

    return TurnResult(
        success=True,
        action_type="activate_light",
        message=f"{character.name}이(가) {source.name} 활성.",
        side_effects=side,
    )


# ─── 3. 이동 ───


def move_to_sub_area(
    party: list[Character],
    world: WorldState,
    current_location: Location,
    target_sub_area: str,
) -> TurnResult:
    """sub_area 이동 — Floor1 정의 본격 활용 + 인접 검증.

    accessible_from semantic = OUTBOUND (현재 영역에서 갈 수 있는 곳).
    """
    f1 = get_floor1_definition()
    target = next(
        (sa for sa in f1.sub_areas if sa.name == target_sub_area), None
    )

    if target is None:
        return TurnResult(
            success=False,
            action_type="move",
            message=f"{target_sub_area} sub_area 없음 (★ 1층 6 영역).",
        )

    current_name = current_location.sub_area
    if current_name:
        current_sa = next(
            (sa for sa in f1.sub_areas if sa.name == current_name), None
        )
        if current_sa is None:
            return TurnResult(
                success=False,
                action_type="move",
                message=f"현재 위치 {current_name} 정의 X.",
            )
        if target_sub_area not in current_sa.accessible_from:
            return TurnResult(
                success=False,
                action_type="move",
                message=(
                    f"{current_name} → {target_sub_area} 인접 X "
                    f"(인접: {', '.join(current_sa.accessible_from) or '없음'})."
                ),
            )

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="move",
        message=f"{current_name or '시작'} → {target_sub_area}.",
        side_effects=[
            f"target_sub_area={target_sub_area}",
            "시간 0.5h 경과",
        ],
    )


# ─── 4. 전투 ───


def execute_attack(
    attacker: Character,
    target_monster_name: str,
    party: list[Character],
    world: WorldState,
) -> TurnResult:
    """전투 — 단순 공식 (★ 본 commit 본격, LLM 평가 X).

    공식:
    - 공격 = strength + physical
    - 9등급 몬스터 HP 30
    - 공격 < 30이면 처치 X + 받는 데미지 = max(0, 10 - bone_strength//2)
    """
    f1 = get_floor1_definition()
    monster = next(
        (m for m in f1.monsters if m.name == target_monster_name), None
    )

    if monster is None:
        return TurnResult(
            success=False,
            action_type="attack",
            message=f"{target_monster_name} 1층 몬스터 X.",
        )

    grade_value = int(monster.grade)

    attacker_dmg = attacker.strength + attacker.physical
    if attacker_dmg < 30:
        received = max(0, 10 - attacker.bone_strength // 2)
        attacker.hp = max(0, attacker.hp - received)
        return TurnResult(
            success=False,
            action_type="attack",
            message=(
                f"{attacker.name} → {target_monster_name} 공격 "
                f"(데미지 {attacker_dmg}). 처치 X. 받은 데미지 {received}."
            ),
            side_effects=[
                f"{attacker.name} HP {attacker.hp}/{attacker.hp_max}"
            ],
        )

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="attack",
        message=(
            f"{attacker.name}이(가) {target_monster_name} 처치 "
            f"({grade_value}등급)."
        ),
        side_effects=[f"드롭: {grade_value}등급 마석", "시간 0.5h 경과"],
    )


# ─── 5. 정수 흡수 ───


def absorb_floating_essence(
    character: Character,
    essence_name: str,
) -> TurnResult:
    """정수 흡수 (★ 13/14화 본문, Character.absorb_essence 진짜 호출).

    본 commit 단순화:
    - 1층 9등급 정수 매핑 (★ Floor1 monsters drops)
    - 살이 닿음 가정 (★ 후속 commit에 거리 시뮬)
    """
    f1 = get_floor1_definition()
    found = None
    for m in f1.monsters:
        for d in m.drops:
            if d.essence_name == essence_name:
                found = d
                break
        if found is not None:
            break

    if found is None:
        return TurnResult(
            success=False,
            action_type="absorb_essence",
            message=f"{essence_name} 1층 정수 X.",
        )

    color = found.color_pool[0] if found.color_pool else EssenceColor.GREEN
    essence = Essence(
        name=essence_name,
        grade=EssenceGrade.GRADE_9,
        color=color,
        essence_type=EssenceType.DPS_MELEE,
        origin=EssenceOrigin.MONSTER_DROP,
        monster_source=essence_name.replace(" 정수", ""),
    )

    success = character.absorb_essence(essence)

    if not success:
        return TurnResult(
            success=False,
            action_type="absorb_essence",
            message=(
                f"{character.name}이(가) {essence_name} 흡수 X "
                f"(슬롯 {character.essence_slots_used()}/"
                f"{character.essence_slot_max()})."
            ),
        )

    return TurnResult(
        success=True,
        action_type="absorb_essence",
        message=f"{character.name}이(가) {essence_name} 흡수.",
        side_effects=[
            f"슬롯 {character.essence_slots_used()}/"
            f"{character.essence_slot_max()}",
        ],
    )


# ─── 6. 휴식 ───


def rest(
    party: list[Character],
    world: WorldState,
    hours: float = 4.0,
) -> TurnResult:
    """휴식 — 4시간 교대 (★ 27화 본문)."""
    advance_time(party, world, elapsed_hours=hours)
    return TurnResult(
        success=True,
        action_type="rest",
        message=f"{hours}시간 휴식.",
        side_effects=[f"미궁 시간 {world.hours_in_dungeon}h / 168h"],
    )


# ─── 7. 메시지 스톤 ───


def send_message_stone(
    sender: Character,
    target_name: str,
    message_text: str,
) -> TurnResult:
    """메시지 스톤 통신 — 300m 본질 (★ 10화)."""
    return TurnResult(
        success=True,
        action_type="communicate",
        message=f"{sender.name} → {target_name}: '{message_text[:50]}'.",
        side_effects=["300m 반경 통신", "공명 stone 필수"],
    )


# ─── 8. 도주 ───


def flee_from_threat(
    party: list[Character],
    world: WorldState,
    threat_description: str,
) -> TurnResult:
    """도주 — 단순 시간 흐름 (★ 14화)."""
    advance_time(party, world, elapsed_hours=0.5)
    return TurnResult(
        success=True,
        action_type="flee",
        message=f"위협({threat_description}) 도주.",
        side_effects=["시간 0.5h", "다른 sub_area로 이동 가능"],
    )


# ─── 9. 비석 공물 ───


def offer_to_stone(
    character: Character,
    rift_id: str,
    world: WorldState,
) -> TurnResult:
    """비석 공물 — 8등급 마석 → 균열 진입 가능 (★ 374화).

    본 commit 단순화: rift_id 검증만 (★ 마석 차감은 inventory 통합 시).
    """
    f1 = get_floor1_definition()
    rift = next((r for r in f1.rifts if r.rift_id == rift_id), None)

    if rift is None:
        return TurnResult(
            success=False,
            action_type="offer_to_stone",
            message=f"균열 {rift_id} X (★ 1층 4 균열).",
        )

    if rift_id not in world.active_rifts:
        world.active_rifts.append(rift_id)

    return TurnResult(
        success=True,
        action_type="offer_to_stone",
        message=(
            f"{character.name}이(가) 비석에 8등급 마석 공물 → "
            f"{rift.name} 균열 활성."
        ),
        side_effects=[f"active_rifts={world.active_rifts}"],
    )


# ─── 10. 균열 진입 ───


def enter_rift(
    party: list[Character],
    world: WorldState,
    rift_id: str,
) -> TurnResult:
    """균열 진입 — Location 변경은 caller가 (★ side_effect 명시)."""
    if rift_id not in world.active_rifts:
        return TurnResult(
            success=False,
            action_type="enter_rift",
            message=f"균열 {rift_id} 비활성 (먼저 비석 공물).",
        )

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="enter_rift",
        message=f"균열 {rift_id} 진입.",
        side_effects=[
            "target_realm=RIFT",
            f"target_rift_id={rift_id}",
            "시간 0.5h",
        ],
    )


# ─── 11. 균열 탈출 ───


def exit_rift(
    party: list[Character],
    world: WorldState,
    rift_id: str,
) -> TurnResult:
    """균열 탈출 — 1층 복귀."""
    if rift_id in world.active_rifts:
        world.active_rifts.remove(rift_id)

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="exit_rift",
        message=f"균열 {rift_id} 탈출 → 1층.",
        side_effects=["target_realm=DUNGEON", "시간 0.5h"],
    )


# ─── 12. 탐색 ───


def explore_area(
    party: list[Character],
    world: WorldState,
) -> TurnResult:
    """탐색 — 시간 흐름 + 가능성 발견."""
    advance_time(party, world, elapsed_hours=0.5)
    return TurnResult(
        success=True,
        action_type="explore",
        message="주변 탐색.",
        side_effects=["시간 0.5h"],
    )


# ─── 13. 아이템 사용 ───


def use_item(
    character: Character,
    item_name: str,
) -> TurnResult:
    """아이템 사용 — 본 commit 단순화 (★ 후속 commit에 inventory 통합)."""
    return TurnResult(
        success=True,
        action_type="use_item",
        message=f"{character.name}이(가) {item_name} 사용.",
        side_effects=[],
    )
