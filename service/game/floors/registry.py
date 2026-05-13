"""FLOOR_REGISTRY — floor_number → FloorDefinition mapping (★ Phase 8 R2).

N층 enabler: 2층 본격 본격 FLOOR_REGISTRY[2] = FLOOR_2 추가만 본격.

본 commit 본격 1층만 등록 (★ 2층 콘텐츠 본격 후속 commit).
"""

from __future__ import annotations

from typing import Final

from service.game.state_v2 import FloorDefinition, Location

from .floor1 import FLOOR1_DEFINITION

# ★ floor_number (int) → FloorDefinition 본격. 본 commit 본격 1층만.
# 후속 commit 본격 본격: 2: FLOOR2_DEFINITION 등 추가.
FLOOR_REGISTRY: Final[dict[int, FloorDefinition]] = {
    1: FLOOR1_DEFINITION,
}


def get_current_floor_definition(location: Location) -> FloorDefinition:
    """Location 본격 본격 FloorDefinition 본격.

    Location.floor가 None 또는 registry 본격 없으면 default 1 본격 fallback.
    본 fallback은 R2 본격 backward compat (★ R3+R4 본격 본격 location.floor
    본격 명시 보장).

    ★ get_floor_definition(N) explicit lookup helper는 R3+R4 본격 ENTER_NEXT_FLOOR
    (★ current+1 lookup) 본격 실제 사용처 발현 시 재도입 (YAGNI — 854c796 /
    2fc1695 선례 정합).
    """
    floor_num = location.floor if location.floor is not None else 1
    if floor_num not in FLOOR_REGISTRY:
        return FLOOR_REGISTRY[1]
    return FLOOR_REGISTRY[floor_num]
