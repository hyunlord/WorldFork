"""Phase D — 자연어 input → intent or fallback schema.

본 commit 본 base — 본 후속 commit 본 deterministic action handler / canon
context augmentation / move endpoint / dungeon mechanism.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FreeformActionRequest(BaseModel):
    """자연어 input + 세션 ID (Phase D step 4).

    session_id 존재 시 서버사이드 세션 상태 사용.
    session_id 없을 시 inline context 기반 stateless 모드 (하위 호환).
    """

    user_input: str = Field(..., min_length=1, max_length=500)
    rationale: str | None = Field(default=None, max_length=500)
    session_id: str | None = Field(default=None)

    current_hp: int = Field(default=100, ge=0)
    max_hp: int = Field(default=100, ge=1)
    inventory: list[str] = Field(default_factory=list)
    location: str = Field(default="1층 입구", max_length=100)
    encounters: list[dict[str, object]] = Field(default_factory=list)


class ExtractedEntities(BaseModel):
    """9B intent classifier가 추출한 entity (Phase D step 5)."""

    actor: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    item: str | None = Field(default=None, max_length=100)
    direction: str | None = Field(default=None)  # north/south/east/west or None


class IntentMatch(BaseModel):
    """9B intent classifier 결과."""

    matched_action: str | None = Field(
        default=None,
        description="PlayerActionType value 또는 null (★ free-form)",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., max_length=200)
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)


class StateDelta(BaseModel):
    """action 결과 state 변화."""

    hp_change: int = Field(default=0)
    inventory_add: list[str] = Field(default_factory=list, max_length=10)
    inventory_remove: list[str] = Field(default_factory=list, max_length=10)
    location: str | None = Field(default=None, max_length=100)
    time_advance: int = Field(default=1, ge=0, le=24)
    affinity_changes: dict[str, int] = Field(default_factory=dict)
    encounter_resolved: bool = Field(default=False)
    xp_gain: int = Field(default=0)
    level_up: bool = Field(default=False)
    new_level: int | None = Field(default=None)
    floor_number: int | None = Field(default=None)
    floor_change: int | None = Field(default=None)
    stone_change: int = Field(default=0)
    rift_id: str | None = Field(default=None)
    rift_sub_area: str | None = Field(default=None)
    rift_is_variant: bool | None = Field(default=None)


ResolvedPath = Literal["intent", "fallback"]


class SessionSummary(BaseModel):
    """freeform_action 응답에 포함되는 세션 요약."""

    current_hp: int
    max_hp: int
    inventory: list[str]
    location: str
    turn_count: int


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
    session_id: str | None = Field(default=None)
    session_state: SessionSummary | None = Field(default=None)
    # ★ 추천 행동 — frontend 추천 버튼(3항목). 현재 상황(전투/마을/던전) 정합.
    suggested_actions: list[str] = Field(default_factory=list, max_length=5)
    # ★ 서빙 3단계 — GM 라우팅 관측: "9b"(단순 서사) / "27b"(pivotal 품질) / None.
    #   하이브리드 라우팅 투명성 + 결정적 E2E 검증용(영속 X — 응답 전용).
    gm_model: str | None = Field(default=None)
