"""Tier 2 D12 — game-loop turn handler (★ Stage 7 schema 진짜 production mutate).

직전 backout 본질 해소:
- ctx 노출 X = Made But Never Used (★ codex Layer 4)
- → 본 모듈이 진짜 production code (game_routes.process_turn)에서 schema mutate

본 commit 범위 (★ YAGNI 진짜):
- advance_time 1개만 (★ FastAPI process_turn에서 진짜 호출)
- 다른 핸들러 (activate_light / absorb_essence / bounty / damage)는
  실제 트리거 (LLM 자연어 판단 등) 추가 시 함께 도입.

진짜 mutate 영역:
- Character.light_state (활성 자원 차감 + 정령 cooldown 진입/회복)
- Character.has_active_light (★ 호출)
- Character.is_alive (★ 사망자 skip)
- WorldState.hours_in_dungeon (시간 누적)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .state_v2 import Character, WorldState


@dataclass
class TurnResult:
    """Turn 처리 결과."""

    success: bool
    message: str
    side_effects: list[str] = field(default_factory=list)


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
        message=f"{elapsed_hours}시간 경과.",
        side_effects=side,
    )
