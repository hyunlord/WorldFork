"""Tier 2 D12 — game-loop turn handler (★ Stage 7 schema 진짜 production mutate).

직전 backout 본질 해소:
- ctx 노출 X = Made But Never Used (★ codex Layer 4)
- → 본 모듈이 진짜 production code에서 schema mutate
- = Stage 7 schema 더 이상 'Made But Never Used' X

LLM 호출 X — Mechanical mutate만. 후속 commit이 LLM 통합.

진짜 mutate 영역:
- Character.light_state (활성/소진/회복/consumables)
- Character.has_active_light (★ 호출)
- Character.consume_essence_at_position (★ 호출)
- Character.hp / is_alive
- WorldState.active_bounties
- WorldState.hours_in_dungeon
- FloatingEssence.is_decayed (★ 30분 소멸 체크)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .state_v2 import (
    BountyEntry,
    Character,
    FloatingEssence,
    LightSource,
    WorldState,
)

# ─── Turn 결과 ───

ActionType = Literal[
    "activate_light",
    "wait",
    "absorb_essence",
    "issue_bounty",
    "resolve_bounty",
    "take_damage",
]


@dataclass
class TurnResult:
    """Turn 처리 결과."""

    success: bool
    action_type: ActionType
    message: str
    side_effects: list[str] = field(default_factory=list)


# ─── Light Source 처리 ───


def activate_light_source(
    character: Character,
    source: LightSource,
) -> TurnResult:
    """캐릭터가 빛 자원 활성 (★ Stage 4/7 본질).

    - 종족 한정 (★ 정령 등불 = 요정 한정, 11화)
    - 단발 자원은 consumables 차감 (★ 조명탄)
    - 활성 시 Character.light_state 진짜 mutate
    """
    if source.requires_race is not None:
        if character.race.value != source.requires_race:
            return TurnResult(
                success=False,
                action_type="activate_light",
                message=(
                    f"{character.name}는(은) {source.name}을(를) 사용할 수 없다 "
                    f"({source.requires_race} 한정)."
                ),
            )

    if source.is_consumable:
        current = character.light_state.consumables.get(source.name, 0)
        if current <= 0:
            return TurnResult(
                success=False,
                action_type="activate_light",
                message=f"{source.name} 보유 X.",
            )
        character.light_state.consumables[source.name] = current - 1

    character.light_state.active_source_name = source.name
    character.light_state.remaining_duration_hours = source.duration_hours or 0.0

    side: list[str] = [f"가시거리 {source.radius_meters}m"]
    if source.duration_hours:
        side.append(f"지속 {source.duration_hours}시간")
    else:
        side.append("단발")

    return TurnResult(
        success=True,
        action_type="activate_light",
        message=f"{character.name}이(가) {source.name} 활성화.",
        side_effects=side,
    )


def advance_time(
    characters: list[Character],
    world: WorldState,
    elapsed_hours: float,
) -> TurnResult:
    """시간 흐름 (★ 빛 자원 소진 + cooldown 회복 + 미궁 시간 누적).

    - light_state.remaining_duration_hours 차감
    - 정령 자원 소진 시 cooldown 2h 진입 (★ 11화)
    - 사망자는 처리 X
    """
    side: list[str] = []

    for c in characters:
        if not c.is_alive():
            continue

        ls = c.light_state

        # ★ 기존 cooldown 먼저 차감 (★ 신규 cooldown 진입 분리)
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


# ─── 정수 흡수 ───


def attempt_essence_absorb(
    character: Character,
    floating: FloatingEssence,
    can_reach: bool,
    current_hours: int,
    current_minutes: int,
) -> TurnResult:
    """정수 흡수 시도 (★ Stage 7 schema 진짜 호출, 13/14화 본문).

    - 30분 자연 소멸 검증 (★ FloatingEssence.is_decayed)
    - 살이 닿아야 (★ can_reach)
    - 슬롯/중복 체크 (★ Character.consume_essence_at_position)
    """
    if floating.is_decayed(current_hours, current_minutes):
        return TurnResult(
            success=False,
            action_type="absorb_essence",
            message=f"{floating.essence.name}이(가) 자연 소멸했다.",
        )

    if not can_reach:
        return TurnResult(
            success=False,
            action_type="absorb_essence",
            message=f"{character.name}이(가) {floating.essence.name}에 닿지 못했다.",
        )

    success = character.consume_essence_at_position(
        floating.essence, can_reach=True
    )

    if not success:
        return TurnResult(
            success=False,
            action_type="absorb_essence",
            message=(
                f"{character.name}이(가) {floating.essence.name} 흡수 실패 "
                "(슬롯 만석 또는 중복)."
            ),
        )

    return TurnResult(
        success=True,
        action_type="absorb_essence",
        message=f"{character.name}이(가) {floating.essence.name} 흡수.",
        side_effects=[
            f"슬롯 사용 {character.essence_slots_used()}/"
            f"{character.essence_slot_max()}"
        ],
    )


# ─── 현상금 동적 ───


def issue_bounty(
    world: WorldState,
    bounty: BountyEntry,
) -> TurnResult:
    """현상금 발령 (★ Stage 7 동적, 11화 본문)."""
    world.active_bounties.append(bounty)
    return TurnResult(
        success=True,
        action_type="issue_bounty",
        message=(
            f"{bounty.issuer_name}이(가) {bounty.target_name} 현상금 "
            f"{bounty.amount_stones:,}스톤 발령."
        ),
    )


def resolve_bounty(
    world: WorldState,
    target_name: str,
) -> TurnResult:
    """현상금 해소 (★ 표적 처치 또는 만료)."""
    matched = [b for b in world.active_bounties if b.target_name == target_name]
    if not matched:
        return TurnResult(
            success=False,
            action_type="resolve_bounty",
            message=f"{target_name} 현상금 X.",
        )

    world.active_bounties = [
        b for b in world.active_bounties if b.target_name != target_name
    ]

    total = sum(b.amount_stones for b in matched)
    return TurnResult(
        success=True,
        action_type="resolve_bounty",
        message=f"{target_name} 현상금 {len(matched)}건 해소 (총 {total:,}스톤).",
    )


# ─── HP 변동 ───


def apply_damage(
    character: Character,
    damage: int,
) -> TurnResult:
    """HP 손상 (★ 작품 본질 영구사망 — 시신 = 사물).

    이미 사망자에게 추가 손상 X.
    """
    if not character.is_alive():
        return TurnResult(
            success=False,
            action_type="take_damage",
            message=f"{character.name}은(는) 이미 사망.",
        )

    character.hp = max(0, character.hp - damage)

    if not character.is_alive():
        return TurnResult(
            success=True,
            action_type="take_damage",
            message=f"{character.name}이(가) 영구사망 (★ HP 0).",
            side_effects=["시신은 사물, 미궁 연료 (작품 본질)."],
        )

    return TurnResult(
        success=True,
        action_type="take_damage",
        message=f"{character.name} HP {character.hp}/{character.hp_max}.",
    )
