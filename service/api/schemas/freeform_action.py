"""Phase D — 자연어 input → intent or fallback schema.

본 commit 본 base — 본 후속 commit 본 deterministic action handler / canon
context augmentation / move endpoint / dungeon mechanism.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FreeformActionRequest(BaseModel):
    """자연어 input + 현재 턴 context (stateless).

    Phase D step 4에서 session_id 기반 서버사이드 state holder로 교체.
    현재는 프론트엔드가 context를 직접 전송.
    """

    user_input: str = Field(..., min_length=1, max_length=500)
    rationale: str | None = Field(default=None, max_length=500)

    current_hp: int = Field(default=100, ge=0)
    max_hp: int = Field(default=100, ge=1)
    inventory: list[str] = Field(default_factory=list)
    location: str = Field(default="1층 입구", max_length=100)
    encounters: list[dict[str, object]] = Field(default_factory=list)


class IntentMatch(BaseModel):
    """9B intent classifier 본 결과."""

    matched_action: str | None = Field(
        default=None,
        description="PlayerActionType value 또는 null (★ free-form)",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., max_length=200)


class StateDelta(BaseModel):
    """action 결과 state 변화."""

    hp_change: int = Field(default=0)
    inventory_add: list[str] = Field(default_factory=list, max_length=10)
    inventory_remove: list[str] = Field(default_factory=list, max_length=10)
    location: str | None = Field(default=None, max_length=100)
    time_advance: int = Field(default=1, ge=0, le=24)
    affinity_changes: dict[str, int] = Field(default_factory=dict)
    encounter_resolved: bool = Field(default=False)


ResolvedPath = Literal["intent", "fallback"]


class FreeformActionResponse(BaseModel):
    """backend 응답."""

    resolved_path: ResolvedPath
    matched_action: str | None = Field(
        default=None,
        description="intent path의 PlayerActionType value",
    )
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    narrative: str = Field(..., min_length=10, max_length=2000)
    state_delta: StateDelta
    action_success: bool = Field(default=True)
    fail_reason: str | None = Field(default=None, max_length=200)
    fallback_reason: str | None = Field(default=None, max_length=200)
