"""Phase D — POST /api/v2/freeform_action endpoint.

Phase D step 4: session_id 기반 서버사이드 state holder.
Phase D step 3: intent path → dispatch_action (deterministic handler).
fallback path: 27B free-form (변경 없음).
"""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException

from service.api.schemas.freeform_action import (
    FreeformActionRequest,
    FreeformActionResponse,
    SessionSummary,
    StateDelta,
)
from service.sim.action_context import ActionContext
from service.sim.action_handlers import dispatch_action
from service.sim.freeform_handler import freeform_action
from service.sim.intent_classifier import classify_intent
from service.sim.session_manager import SessionState, get_session_manager
from service.sim.types import PlayerActionType

router = APIRouter(prefix="/api/v2", tags=["tier2-freeform"])

INTENT_THRESHOLD = 0.8


def _build_context(req: FreeformActionRequest, state: SessionState | None) -> ActionContext:
    """세션 상태 우선, 없으면 inline request 값 사용."""
    if state is not None:
        return ActionContext(
            current_hp=state.current_hp,
            max_hp=state.max_hp,
            inventory=list(state.inventory),
            location=state.location,
            encounters=list(state.encounters),
            user_input=req.user_input,
        )
    return ActionContext(
        current_hp=req.current_hp,
        max_hp=req.max_hp,
        inventory=list(req.inventory),
        location=req.location,
        encounters=list(req.encounters),
        user_input=req.user_input,
    )


def _session_summary(state: SessionState) -> SessionSummary:
    return SessionSummary(
        current_hp=state.current_hp,
        max_hp=state.max_hp,
        inventory=state.inventory,
        location=state.location,
        turn_count=state.turn_count,
    )


@router.post("/freeform_action", response_model=FreeformActionResponse)
async def freeform_action_endpoint(
    req: FreeformActionRequest,
) -> FreeformActionResponse:
    """자연어 input → intent dispatch 또는 free-form fallback.

    Step 1: 9B classifier 호출
    Step 2: confidence ≥ INTENT_THRESHOLD + matched_action 존재 시
            ActionContext 빌드 → dispatch_action → StateDelta 반환
    Step 3: 위 미충족 시 27B free-form fallback
    Step 4: session_id 존재 시 결과를 세션 상태에 반영
    """
    # 세션 조회 (session_id 있을 때만)
    session_state: SessionState | None = None
    mgr = get_session_manager()

    if req.session_id is not None:
        session_state = await mgr.get_session(req.session_id)
        if session_state is None:
            # session_id 제공했지만 없으면 자동 생성
            session_state = await mgr.create_session(
                current_hp=req.current_hp,
                max_hp=req.max_hp,
                inventory=list(req.inventory),
                location=req.location,
            )

    try:
        intent = await asyncio.to_thread(classify_intent, req.user_input)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"intent classifier failed: {exc}",
        ) from exc

    ctx = _build_context(req, session_state)

    if (
        intent.matched_action is not None
        and intent.confidence >= INTENT_THRESHOLD
    ):
        try:
            action_type = PlayerActionType(intent.matched_action)
        except ValueError:
            pass
        else:
            try:
                result = await dispatch_action(action_type, ctx)
            except Exception as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"action handler failed: {exc}",
                ) from exc

            resolved_path: Literal["intent", "fallback"] = "intent"
            if session_state is not None:
                session_state = await mgr.apply_result(
                    session_state.session_id,
                    result,
                    user_input=req.user_input,
                    resolved_path=resolved_path,
                )

            return FreeformActionResponse(
                resolved_path=resolved_path,
                matched_action=intent.matched_action,
                confidence=intent.confidence,
                narrative=result.narrative,
                action_success=result.success,
                fail_reason=result.fail_reason,
                state_delta=StateDelta(
                    hp_change=result.hp_change,
                    inventory_add=result.inventory_add,
                    inventory_remove=result.inventory_remove,
                    location=result.location,
                    time_advance=min(result.time_advance, 24),
                    affinity_changes=result.affinity_changes,
                    encounter_resolved=result.encounter_resolved,
                ),
                session_id=session_state.session_id if session_state else None,
                session_state=_session_summary(session_state) if session_state else None,
            )

    try:
        narrative, state_delta = await asyncio.to_thread(
            freeform_action,
            req.user_input,
            req.rationale,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"free-form handler failed: {exc}",
        ) from exc

    resolved_path_fb: Literal["intent", "fallback"] = "fallback"
    if session_state is not None:
        from service.sim.action_context import ActionResult

        pseudo_result = ActionResult(
            narrative=narrative,
            hp_change=state_delta.hp_change,
            inventory_add=list(state_delta.inventory_add),
            inventory_remove=list(state_delta.inventory_remove),
            location=state_delta.location,
            time_advance=state_delta.time_advance,
            affinity_changes=dict(state_delta.affinity_changes),
        )
        session_state = await mgr.apply_result(
            session_state.session_id,
            pseudo_result,
            user_input=req.user_input,
            resolved_path=resolved_path_fb,
        )

    return FreeformActionResponse(
        resolved_path=resolved_path_fb,
        confidence=intent.confidence,
        narrative=narrative,
        state_delta=state_delta,
        fallback_reason=intent.reason,
        session_id=session_state.session_id if session_state else None,
        session_state=_session_summary(session_state) if session_state else None,
    )
