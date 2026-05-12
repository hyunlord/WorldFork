"""Tier 2 GameState V2 → JSON-serializable dict (★ Phase 7a).

본 모듈 본격:
- frozen dataclass (★ state_v2.py 본격) → dict
- Enum → value 본격
- nested list/tuple/dict 본격
- frontend 본격 (★ /api/v2/state) JSON 본격 본격

본격 본격 X:
- 외부 dependency (★ pydantic/dataclasses-json 본격 X)
- backward compat shim (★ Phase 7a 첫 commit)
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from service.game.state_v2 import Character, Location, WorldState


def state_to_dict(obj: Any) -> dict[str, Any] | list[Any] | str | int | float | bool | None:
    """임의 객체 → JSON-serializable 본격.

    본격 본질 본격:
    - dataclass → {field_name: convert(value)} 본격
    - Enum → .value (★ StrEnum/IntEnum 모두 본격)
    - list/tuple → list 본격
    - dict → key=str 본격 dict
    - primitive (str/int/float/bool/None) → 그대로
    - 본격 X → str(obj) fallback (★ 본문 안전)
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Enum):
        value = obj.value
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: state_to_dict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [state_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): state_to_dict(v) for k, v in obj.items()}
    return str(obj)


def game_state_v2_to_dict(
    party: dict[str, Character],
    world: WorldState,
    location: Location,
) -> dict[str, Any]:
    """Tier 2 (party + world + location) → JSON-serializable 본격 본격.

    frontend 본격 (★ Phase 7b 이하):
    - characters: party 본격 본격 Character V2 dict
    - world: WorldState dict (★ active_rifts 본격)
    - location: Location dict (★ realm/sub_area/rift_id 본격)
    """
    characters_dict: dict[str, Any] = {
        name: state_to_dict(c) for name, c in party.items()
    }
    world_dict = state_to_dict(world)
    location_dict = state_to_dict(location)
    return {
        "characters": characters_dict,
        "world": world_dict,
        "location": location_dict,
    }
