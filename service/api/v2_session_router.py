"""Phase D step 4 — 세션 관리 endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from service.sim.session_manager import SessionState, get_session_manager

router = APIRouter(prefix="/api/v2/session", tags=["tier2-session"])


class SessionStartRequest(BaseModel):
    current_hp: int = Field(default=100, ge=0)
    max_hp: int = Field(default=100, ge=1)
    inventory: list[str] = Field(default_factory=list)
    location: str = Field(default="1층 입구", max_length=100)


class SessionStartResponse(BaseModel):
    session_id: str
    current_hp: int
    max_hp: int
    inventory: list[str]
    location: str
    turn_count: int


class SessionStateResponse(BaseModel):
    session_id: str
    created_at: float
    last_active: float
    # 기본 stat
    current_hp: int
    max_hp: int
    # inventory + location
    inventory: list[str]
    location: str
    # turn
    turn_count: int
    last_spawn_turn: int
    # status / equipment
    status_effects: list[dict[str, object]]
    equipment: dict[str, object]
    # 캐릭터 진행
    player_level: int
    player_xp: int
    max_essences: int
    soul_power: int
    absorbed_essences: list[dict[str, object]]
    defeated_monster_types: list[str]
    # 감응도 소비 아이템 누적 (element → bonus)
    player_sensitivities: dict[str, int]
    # dungeon floor / clock
    floor_number: int
    hours_in_dungeon: float
    # 마석 잔액
    stone_balance: int
    # rift 상태
    rift_id: str | None
    rift_sub_area: str | None
    rift_is_variant: bool
    # 최초 포탈 개방 여부
    portal_first_opened: bool
    # encounters (in-memory only)
    encounters: list[dict[str, object]]
    # 게임 내 경과 시간 (minute 단위)
    time_elapsed: int
    # 종족 (★ phase-e-1)
    race: str
    # 시나리오 모드 (★ phase-e-2)
    scenario_mode: str
    # ★ 게임 엔진 2단계 — 스토리 진전(단계 + 플래그). frontend 단계 표시/검증용.
    story_phase: str
    story_flags: dict[str, bool]


def _to_start_resp(s: SessionState) -> SessionStartResponse:
    return SessionStartResponse(
        session_id=s.session_id,
        current_hp=s.current_hp,
        max_hp=s.max_hp,
        inventory=s.inventory,
        location=s.location,
        turn_count=s.turn_count,
    )


def _to_state_resp(s: SessionState) -> SessionStateResponse:
    return SessionStateResponse(
        session_id=s.session_id,
        created_at=s.created_at,
        last_active=s.last_active,
        current_hp=s.current_hp,
        max_hp=s.max_hp,
        inventory=list(s.inventory),
        location=s.location,
        turn_count=s.turn_count,
        last_spawn_turn=s.last_spawn_turn,
        status_effects=list(s.status_effects),
        equipment=dict(s.equipment),
        player_level=s.player_level,
        player_xp=s.player_xp,
        max_essences=s.max_essences,
        soul_power=s.soul_power,
        absorbed_essences=list(s.absorbed_essences),
        defeated_monster_types=list(s.defeated_monster_types),
        player_sensitivities=dict(s.player_sensitivities),
        floor_number=s.floor_number,
        hours_in_dungeon=s.hours_in_dungeon,
        stone_balance=s.stone_balance,
        rift_id=s.rift_id,
        rift_sub_area=s.rift_sub_area,
        rift_is_variant=s.rift_is_variant,
        portal_first_opened=s.portal_first_opened,
        encounters=list(s.encounters),
        time_elapsed=s.time_elapsed,
        race=s.race,
        scenario_mode=s.scenario_mode,
        story_phase=s.story_phase,
        story_flags=dict(s.story_flags),
    )


@router.post("/start", response_model=SessionStartResponse)
async def session_start(req: SessionStartRequest) -> SessionStartResponse:
    mgr = get_session_manager()
    state = await mgr.create_session(
        inventory=list(req.inventory),
        location=req.location or None,
        current_hp=req.current_hp,
        max_hp=req.max_hp,
    )
    return _to_start_resp(state)


@router.get("/{session_id}/state", response_model=SessionStateResponse)
async def session_state(session_id: str) -> SessionStateResponse:
    mgr = get_session_manager()
    state = await mgr.get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    return _to_state_resp(state)


@router.post("/{session_id}/end", response_model=dict)
async def session_end(session_id: str) -> dict[str, str]:
    mgr = get_session_manager()
    state = await mgr.get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    await mgr.end_session(session_id)
    return {"status": "ended", "session_id": session_id}
