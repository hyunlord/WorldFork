"""CharacterConfig request/response schema (Phase E-2)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CharacterConfigRequest(BaseModel):
    scenario_mode: str = Field(default="bjorn", description="시나리오 모드 (bjorn | new_explorer)")
    race: str | None = Field(default=None, description="종족 (new_explorer 전용, bjorn은 무시)")
    inventory: list[str] = Field(default_factory=list)
    location: str | None = Field(default=None, description="시작 위치 (None = 시나리오 기본값)")


class CharacterConfigResponse(BaseModel):
    session_id: str
    scenario_mode: str
    race: str
    starting_location: str
    starting_floor: int
    hp: int
    max_hp: int
    soul_power: int
    max_essences: int
    race_traits: list[str]
    scenario_description: str
    # ★ phase-e-5: 시나리오 + 종족 정합 시작 narrative
    starting_narrative: str
