"""버그4 — 추천이 실행 가능 행동만 (결정적 단위 테스트).

'더 깊이 나아간다'(MOVE_CHAMBER)는 균열 내(rift_sub_area)에서만 유효하다.
균열 밖 던전 floor에서 추천하면 handle_move_chamber가 '균열 안에 있지 않거나…'
실행 불가 응답을 낸다 — 그래서 균열 밖에서는 항상 실행 가능한 탐색을 추천한다.
"""

from __future__ import annotations

from typing import Any

from service.api.v2_freeform_router import _suggest_actions
from service.sim.session_manager import SessionState


def _state(**over: Any) -> SessionState:
    base = dict(
        session_id="t",
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="던전 1층",
        encounters=[],
        turn_count=3,
        created_at=0.0,
        last_active=0.0,
        floor_number=1,
        story_phase="dungeon",
    )
    base.update(over)
    return SessionState(**base)  # type: ignore[arg-type]


def test_outside_rift_no_deeper_suggestion() -> None:
    # 균열 밖 던전 floor — '더 깊이 나아간다'(실행 불가) 추천 안 함
    sugg = _suggest_actions(_state(rift_sub_area=None))
    assert "더 깊이 나아간다" not in sugg
    # 대신 실행 가능한 탐색 추천
    assert any("탐색" in s for s in sugg)


def test_inside_rift_offers_deeper() -> None:
    # 균열 내 — '더 깊이 나아간다'(MOVE_CHAMBER) 유효
    sugg = _suggest_actions(_state(rift_sub_area="ch_1"))
    assert "더 깊이 나아간다" in sugg


def test_outside_rift_with_npc_no_deeper() -> None:
    # 비적대 NPC 동반 + 균열 밖 — tail도 실행 불가 행동 회피
    state = _state(
        rift_sub_area=None,
        encounters=[{"name": "동료", "hostile": False}],
    )
    sugg = _suggest_actions(state)
    assert "더 깊이 나아간다" not in sugg


def test_hostile_returns_combat() -> None:
    # 적대 조우는 전투 추천(단계 무관) — 실행 가능
    state = _state(encounters=[{"name": "고블린", "hostile": True}])
    sugg = _suggest_actions(state)
    assert "적을 공격한다" in sugg
