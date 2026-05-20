"""Phase D — POST /api/v2/freeform_action endpoint.

Phase D step 3: intent path → dispatch_action (deterministic handler).
Phase D step 2: intent path placeholder narrative (이전 commit).
fallback path: 27B free-form (변경 없음).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from service.api.schemas.freeform_action import (
    FreeformActionRequest,
    FreeformActionResponse,
    StateDelta,
)
from service.sim.action_context import ActionContext
from service.sim.action_handlers import dispatch_action
from service.sim.freeform_handler import freeform_action
from service.sim.intent_classifier import classify_intent
from service.sim.types import PlayerActionType

router = APIRouter(prefix="/api/v2", tags=["tier2-freeform"])

INTENT_THRESHOLD = 0.8


@router.post("/freeform_action", response_model=FreeformActionResponse)
async def freeform_action_endpoint(
    req: FreeformActionRequest,
) -> FreeformActionResponse:
    """자연어 input → intent dispatch 또는 free-form fallback.

    Step 1: 9B classifier 호출
    Step 2: confidence ≥ INTENT_THRESHOLD + matched_action 존재 시
            ActionContext 빌드 → dispatch_action → StateDelta 반환
    Step 3: 위 미충족 시 27B free-form fallback
    """
    try:
        intent = await asyncio.to_thread(classify_intent, req.user_input)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"intent classifier failed: {exc}",
        ) from exc

    if (
        intent.matched_action is not None
        and intent.confidence >= INTENT_THRESHOLD
    ):
        try:
            action_type = PlayerActionType(intent.matched_action)
        except ValueError:
            pass
        else:
            ctx = ActionContext(
                current_hp=req.current_hp,
                max_hp=req.max_hp,
                inventory=list(req.inventory),
                location=req.location,
                encounters=list(req.encounters),
                user_input=req.user_input,
            )
            try:
                result = await dispatch_action(action_type, ctx)
            except Exception as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"action handler failed: {exc}",
                ) from exc

            return FreeformActionResponse(
                resolved_path="intent",
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

    return FreeformActionResponse(
        resolved_path="fallback",
        confidence=intent.confidence,
        narrative=narrative,
        state_delta=state_delta,
        fallback_reason=intent.reason,
    )
