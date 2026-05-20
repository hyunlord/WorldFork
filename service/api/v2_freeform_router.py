"""Phase D — POST /api/v2/freeform_action endpoint.

★ Frontend (Phase B commit 55896af) 의 InputBar 자연어 input 본 backend
연결. intent path (★ score ≥ threshold) 또는 free-form fallback.

본 commit 본 base — intent path 본 placeholder narrative (★ deterministic
action handler 본 후속 commit). canon_facts 본 미의존.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from service.api.schemas.freeform_action import (
    FreeformActionRequest,
    FreeformActionResponse,
    StateDelta,
)
from service.sim.freeform_handler import freeform_action
from service.sim.intent_classifier import (
    _ACTION_DESCRIPTIONS,
    classify_intent,
)
from service.sim.types import PlayerActionType

router = APIRouter(prefix="/api/v2", tags=["tier2-freeform"])

INTENT_THRESHOLD = 0.8


def _action_description(action_value: str) -> str:
    try:
        action = PlayerActionType(action_value)
    except ValueError:
        return action_value
    return _ACTION_DESCRIPTIONS.get(action, action_value)


@router.post("/freeform_action", response_model=FreeformActionResponse)
async def freeform_action_endpoint(
    req: FreeformActionRequest,
) -> FreeformActionResponse:
    """자연어 input → intent 또는 free-form fallback.

    Step 1: 9B classifier 호출
    Step 2: confidence ≥ INTENT_THRESHOLD + matched_action 존재 시 intent
            path (★ 본 commit 본 placeholder narrative, 후속 commit 본
            deterministic action handler)
    Step 3: 위 미충족 시 27B free-form fallback (★ narrative + state_delta)
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
        description = _action_description(intent.matched_action)
        narrative = (
            f"비요른은 {description}을 시도합니다.\n"
            f"(★ Phase D base — deterministic handler 본 후속 commit)"
        )
        return FreeformActionResponse(
            resolved_path="intent",
            matched_action=intent.matched_action,
            confidence=intent.confidence,
            narrative=narrative,
            state_delta=StateDelta(time_advance=1),
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
