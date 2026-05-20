"""Phase D step 3 — handler I/O types (stateless, session_id는 step 4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from service.api.schemas.freeform_action import ExtractedEntities


@dataclass
class ActionContext:
    """핸들러 입력 — 현재 턴 상태 스냅샷.

    Phase D step 4에서 session_id 기반 서버사이드 state holder로 교체.
    현재는 request body에서 받은 값을 그대로 사용.
    """

    current_hp: int
    max_hp: int
    inventory: list[str]
    location: str
    encounters: list[dict[str, object]] = field(default_factory=list)
    user_input: str = ""
    extracted_entities: ExtractedEntities | None = None


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
    encounters_update: list[dict[str, object]] | None = None  # ★ 6a: enemy hp 갱신
