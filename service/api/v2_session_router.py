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
    current_hp: int
    max_hp: int
    inventory: list[str]
    location: str
    turn_count: int
    created_at: float
    last_active: float


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
        current_hp=s.current_hp,
        max_hp=s.max_hp,
        inventory=s.inventory,
        location=s.location,
        turn_count=s.turn_count,
        created_at=s.created_at,
        last_active=s.last_active,
    )


@router.post("/start", response_model=SessionStartResponse)
async def session_start(req: SessionStartRequest) -> SessionStartResponse:
    mgr = get_session_manager()
    state = await mgr.create_session(
        current_hp=req.current_hp,
        max_hp=req.max_hp,
        inventory=list(req.inventory),
        location=req.location,
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
