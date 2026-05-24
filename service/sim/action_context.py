"""Phase D step 3/6b/6d — handler I/O types."""

from __future__ import annotations

from dataclasses import dataclass, field

from service.api.schemas.freeform_action import ExtractedEntities
from service.sim.equipment import EquipmentSet
from service.sim.player_state import EssenceSlot, compute_total_stats, slot_from_dict


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
    status_effects: list[dict[str, object]] = field(default_factory=list)
    equipment: EquipmentSet | None = None
    # ★ 6d — player progression
    player_level: int = 1
    player_xp: int = 0
    max_essences: int = 1
    soul_power: int = 10
    absorbed_essences: list[dict[str, object]] = field(default_factory=list)
    defeated_monster_types: list[str] = field(default_factory=list)
    # ★ 7 — dungeon floor
    floor_number: int = 0          # 0 = 마을, 1+ = 던전 층
    # ★ audit-3 — rift state
    rift_id: str | None = None        # 현재 진입한 균열 id (None = 균열 밖)
    rift_sub_area: str | None = None  # 현재 chamber id
    rift_is_variant: bool = False     # 변종 균열 여부
    # ★ 6d-followup — 최초 포탈 개방 여부 (ep_0022)
    portal_first_opened: bool = False

    @property
    def essence_slots(self) -> list[EssenceSlot]:
        return [slot_from_dict(d) for d in self.absorbed_essences]

    @property
    def total_stats(self) -> dict[str, int]:
        return compute_total_stats(self.essence_slots)


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
    encounters_update: list[dict[str, object]] | None = None
    status_update: list[dict[str, object]] | None = None
    equipment_update: dict[str, object] | None = None
    # ★ 6d — progression delta
    xp_gain: int = 0
    level_up: bool = False
    new_level: int | None = None
    essence_slot_add: dict[str, object] | None = None
    essence_slot_remove: str | None = None
    defeated_monsters_add: list[str] = field(default_factory=list)
    # ★ 7 — floor transition
    floor_change: int | None = None  # None = no change, +1/-1 = floor transition
    # ★ 168h — dungeon clock reset (진입/탈출 시 0으로 초기화)
    hours_in_dungeon_reset: bool = False
    # ★ audit-c1 — 거래/환전 시 스톤 증감 (+획득 / -지출)
    stone_change: int = 0
    # ★ audit-3 — rift transition
    rift_transition: dict[str, object] | None = None
    # enter:  {"action": "enter", "rift_id": str, "rift_sub_area": str, "is_variant": bool}
    # move:   {"action": "move_to_chamber", "rift_sub_area": str}
    # exit:   {"action": "exit"}
    # ★ 6d-followup — 최초 포탈 개방 확정 (ep_0022: True 시 session에 flag set)
    portal_first_opened_set: bool = False
