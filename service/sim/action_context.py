"""Phase D step 3/6b — handler I/O types."""

from __future__ import annotations

from dataclasses import dataclass, field

from service.api.schemas.freeform_action import ExtractedEntities
from service.sim.equipment import EquipmentSet


@dataclass
class ActionContext:
    """핸들러 입력 — 현재 턴 상태 스냅샷."""

    current_hp: int
    max_hp: int
    inventory: list[str]
    location: str
    encounters: list[dict[str, object]] = field(default_factory=list)
    user_input: str = ""
    extracted_entities: ExtractedEntities | None = None
    status_effects: list[dict[str, object]] = field(default_factory=list)  # ★ 6b
    equipment: EquipmentSet | None = None  # ★ 6b


@dataclass
class ActionResult:
    """핸들러 출력 — 내러티브 + state delta."""

    narrative: str
    hp_change: int = 0
    inventory_add: list[str] = field(default_factory=list)
    inventory_remove: list[str] = field(default_factory=list)
    location: str | None = None
    time_advance: int = 1
    affinity_changes: dict[str, int] = field(default_factory=dict)
    encounter_resolved: bool = False
    success: bool = True
    fail_reason: str | None = None
    encounters_update: list[dict[str, object]] | None = None  # ★ 6a
    status_update: list[dict[str, object]] | None = None  # ★ 6b
    equipment_update: dict[str, object] | None = None  # ★ 6b slot → equipment dict
