"""Tier 2 state API (★ Phase 7a + 7j).

본 router 본격:
- GET /api/v2/state — 현재 (party + world + location) JSON 본격
- GET /api/v2/state/recent_actions — 최근 N 행동 본격
- POST /api/v2/state/reset — 새 본격 default 본격
- POST /api/v2/action — 13 PlayerActionType 본격 execute (★ Phase 7j)

본격 본질:
- singleton holder (★ 본격 단순 — 후속 session-aware 본격)
- default party/world/location (★ E2E 본격 패턴 동일):
  비요른 (바바리안) + 에르웬 (요정), 1층 진입점 DUNGEON
- recent_actions 본격 빈 list (★ 본 commit /action 시 본격 append)

frontend 본격 (Phase 7b 이하 + 본 commit).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.state_v2_serialize import game_state_v2_to_dict
from service.sim.sim_runner import _execute_action
from service.sim.types import PlayerAction, PlayerActionType

router = APIRouter(prefix="/api/v2", tags=["tier2-state"])


# ─── singleton holder (★ 단순, 후속 session 본격) ───


class _V2StateHolder:
    """본격 in-process (party, world, location, recent_actions) holder."""

    def __init__(self) -> None:
        self.party: dict[str, Character] = {}
        self.world: WorldState = WorldState()
        self.location: Location = Location(realm=Realm.DUNGEON)
        self.recent_actions: list[dict[str, Any]] = []
        self.turn: int = 0
        self._init_default()

    def _init_default(self) -> None:
        """E2E 패턴 동일 default — 비요른 + 에르웬, 1층 진입점."""
        self.party = {
            "비요른": Character(
                name="비요른",
                race=Race.BARBARIAN,
                hp=150,
                hp_max=150,
                physical=14,
                strength=16,
                bone_strength=12,
                is_player=True,
            ),
            "에르웬": Character(
                name="에르웬",
                race=Race.FAERIE,
                hp=90,
                hp_max=90,
                soul_power=60,
                soul_power_max=60,
            ),
        }
        self.world = WorldState(party_members=["비요른", "에르웬"])
        self.location = Location(
            realm=Realm.DUNGEON,
            floor=1,
            sub_area="진입점",
            visibility_meters=10,
            has_light=False,
        )
        self.recent_actions = []
        self.turn = 0

    def reset(self) -> None:
        """default 본격 재초기화."""
        self._init_default()


_HOLDER: _V2StateHolder | None = None


def get_holder() -> _V2StateHolder:
    """본격 singleton holder."""
    global _HOLDER
    if _HOLDER is None:
        _HOLDER = _V2StateHolder()
    return _HOLDER


# ─── response models ───


class StateResponse(BaseModel):
    """현재 Tier 2 state 본격."""

    state: dict[str, Any] = Field(
        description="characters + world + location 본격 JSON-serializable dict"
    )
    turn: int = Field(description="현재 turn 본격")


class RecentActionsResponse(BaseModel):
    """최근 N 행동 본격."""

    actions: list[dict[str, Any]] = Field(description="최근 행동 list")
    count: int = Field(description="반환 본격 횟수")
    total: int = Field(description="전체 누적 횟수")


class ResetResponse(BaseModel):
    """reset 응답."""

    status: str = Field(description="'reset' 본격")
    turn: int = Field(description="reset 본격 turn (★ 0)")


# ─── endpoints ───


@router.get("/state", response_model=StateResponse)
async def get_current_state() -> StateResponse:
    """현재 Tier 2 GameState V2 본격 본격.

    응답 본격:
    - state.characters: party 본격 본격 Character V2 (★ HP/스탯/슬롯)
    - state.world: WorldState (★ active_rifts, hours_in_dungeon, party_members)
    - state.location: Location (★ realm/floor/sub_area/rift_id)
    - turn: 현재 turn
    """
    h = get_holder()
    return StateResponse(
        state=game_state_v2_to_dict(h.party, h.world, h.location),
        turn=h.turn,
    )


@router.get("/state/recent_actions", response_model=RecentActionsResponse)
async def get_recent_actions(n: int = 10) -> RecentActionsResponse:
    """최근 N 행동 본격.

    args:
        n: 1-100 본격 (★ default 10)
    """
    if n < 1 or n > 100:
        raise HTTPException(
            status_code=400,
            detail="n must be 1-100",
        )
    h = get_holder()
    sliced = h.recent_actions[-n:]
    # holder는 dict 본격 저장 — 본격 본격 그대로 본격
    return RecentActionsResponse(
        actions=list(sliced),
        count=len(sliced),
        total=len(h.recent_actions),
    )


@router.post("/state/reset", response_model=ResetResponse)
async def reset_state() -> ResetResponse:
    """state 본격 default 본격 재초기화."""
    h = get_holder()
    h.reset()
    return ResetResponse(status="reset", turn=h.turn)


# ─── Phase 7j: action endpoint ───


class ActionRequest(BaseModel):
    """Player action 본격 request (★ Phase 7j)."""

    action_type: str = Field(
        description="13 PlayerActionType (★ value 본격, e.g. 'attack', 'enter_rift')"
    )
    actor: str | None = Field(
        default=None,
        description="실행 캐릭터 이름 (★ 본격 X 시 첫 party member)",
    )
    target: str | None = Field(
        default=None,
        description="target (★ monster/rift_id/sub_area/essence 본격)",
    )
    rationale: str = Field(default="", description="선택 이유 (★ LLM 본격 분석용)")


class ActionResponse(BaseModel):
    """action 본격 response."""

    success: bool = Field(description="_execute_action 본격 성공")
    message: str = Field(description="결과 메시지 (★ turn_handler 본격)")
    side_effects: list[str] = Field(description="state side effects 본격")
    state: dict[str, Any] = Field(description="post-action state 본격")
    turn: int = Field(description="post-action turn 본격")


def _resolve_actor(holder: _V2StateHolder, actor: str | None) -> str:
    """actor 본격 — None 시 첫 party member 본격."""
    if actor and actor in holder.party:
        return actor
    if holder.party:
        return next(iter(holder.party.keys()))
    return ""


@router.post("/action", response_model=ActionResponse)
async def post_action(req: ActionRequest) -> ActionResponse:
    """Player action 본격 execute + state mutation (★ Phase 7j).

    flow:
    1. action_type 본격 PlayerActionType 본격 검증 (★ 400 unknown)
    2. PlayerAction 본격 build
    3. sim_runner._execute_action(action, party, world, location)
    4. holder.turn++, recent_actions 본격 append
    5. ActionResponse 본격 반환
    """
    # ★ PlayerActionType StrEnum 본격 — value 본격 lookup
    try:
        action_type = PlayerActionType(req.action_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action_type: {req.action_type}",
        ) from exc

    h = get_holder()
    actor_name = _resolve_actor(h, req.actor)
    if not actor_name:
        raise HTTPException(
            status_code=400,
            detail="No actor available (★ party empty)",
        )

    action = PlayerAction(
        action_type=action_type,
        actor_name=actor_name,
        target=req.target,
        rationale=req.rationale,
    )

    success, message, side_effects = _execute_action(
        action, h.party, h.world, h.location
    )

    # ★ recent_actions 본격 append (★ frontend recent_actions API 본격)
    h.turn += 1
    h.recent_actions.append(
        {
            "turn": h.turn,
            "actor": actor_name,
            "action_type": action_type.value,
            "target": req.target,
            "success": success,
            "message": message,
            "side_effects": side_effects,
        }
    )

    return ActionResponse(
        success=success,
        message=message,
        side_effects=side_effects,
        state=game_state_v2_to_dict(h.party, h.world, h.location),
        turn=h.turn,
    )
