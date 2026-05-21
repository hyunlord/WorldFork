"""Phase D step 6c — turn-end encounter auto spawn."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from service.canon.schema import CanonFacts
from service.canon.spawn import LOCATION_SPAWN_RATE, SpawnTable, spawn_count_for_grade

if TYPE_CHECKING:
    from service.game.state_v2 import RiftDef, RiftSubAreaDef

SPAWN_COOLDOWN_TURNS = 2


def determine_location_type(
    location_name: str,
    facts: CanonFacts | None,
) -> str:
    """location name → location type (canon lookup → name heuristic)."""
    if facts is not None:
        for loc in facts.locations:
            if loc.name == location_name:
                return loc.location_type
            if loc.name and (loc.name in location_name or location_name in loc.name):
                return loc.location_type

    name = location_name.lower()
    if any(kw in name for kw in ("균열", "차원", "rift")):
        return "rift"
    if any(kw in name for kw in ("도시", "마을", "광장", "시장", "거리", "구역")):
        return "city"
    if any(kw in name for kw in ("탑", "성", "유적", "굴", "지하", "동굴", "미궁")):
        return "dungeon"
    return "wilderness"


def should_spawn(
    location_type: str,
    turn_count: int,
    last_spawn_turn: int,
) -> bool:
    """spawn 여부 결정 — rate check + cooldown check."""
    rate = LOCATION_SPAWN_RATE.get(location_type, 0.0)
    if rate <= 0.0:
        return False
    if turn_count - last_spawn_turn < SPAWN_COOLDOWN_TURNS:
        return False
    return random.random() < rate


def _find_rift_sub_area(
    rift_sub_area: str,
    rift_defs: dict[str, RiftDef],
) -> RiftSubAreaDef | None:
    """rift_defs에서 rift_sub_area id와 일치하는 RiftSubAreaDef 반환."""
    for rift_def in rift_defs.values():
        for sub in rift_def.sub_areas:
            if sub.id == rift_sub_area:
                return sub
    return None


def trigger_spawn(
    location_name: str,
    location_type: str,
    turn_count: int,
    last_spawn_turn: int,
    spawn_table: SpawnTable,
    rift_sub_area: str | None = None,
    rift_defs: dict[str, RiftDef] | None = None,
) -> list[dict[str, object]]:
    """spawn check 후 enemy dict 목록 반환 (비어 있으면 spawn 없음).

    rift_sub_area + rift_defs가 모두 있으면 RiftSubAreaDef.monsters 우선.
    """
    if not should_spawn(location_type, turn_count, last_spawn_turn):
        return []

    from service.sim.enemy import enemy_to_dict

    if rift_sub_area and rift_defs:
        sub_def = _find_rift_sub_area(rift_sub_area, rift_defs)
        if sub_def is not None:
            enemies = spawn_table.spawn_for_rift_sub_area(sub_def, n=1)
            return [enemy_to_dict(e) for e in enemies]

    grade = spawn_table.get_location_grade(location_name)
    n_min, n_max = spawn_count_for_grade(grade)
    n = random.randint(n_min, n_max)

    enemies = spawn_table.spawn_for_location(location_name, location_type, n)
    if not enemies:
        return []

    return [enemy_to_dict(e) for e in enemies]
