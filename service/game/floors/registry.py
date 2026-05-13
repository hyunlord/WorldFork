"""FLOOR_REGISTRY — floor_number → FloorDefinition mapping (★ Phase 8 R2).

N층 enabler: 2층 본격 본격 FLOOR_REGISTRY[2] = FLOOR_2 추가만 본격.

본 commit 본격 1층만 등록 (★ 2층 콘텐츠 본격 후속 commit).

호출 패턴:
- get_floor_definition(N): 명시적 floor_number 본격 정의
- get_current_floor_definition(location): Location.floor 본격 본격 정의 (★ default 1)
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


def get_floor_definition(floor_number: int) -> FloorDefinition:
    """본 floor_number 본격 FloorDefinition 본격.

    Raises:
        KeyError: floor_number 본격 registry에 없음 (★ 본격 2층 본격 후속 추가).
    """
    if floor_number not in FLOOR_REGISTRY:
        raise KeyError(
            f"floor {floor_number}은 FLOOR_REGISTRY 본격 등록 X. "
            f"등록 floor: {sorted(FLOOR_REGISTRY.keys())}"
        )
    return FLOOR_REGISTRY[floor_number]


def get_current_floor_definition(location: Location) -> FloorDefinition:
    """Location 본격 본격 FloorDefinition 본격.

    Location.floor가 None 또는 registry 본격 없으면 default 1 본격 fallback.
    본 fallback은 R2 본격 backward compat (★ R3+R4 본격 본격 location.floor
    본격 명시 보장).
    """
    floor_num = location.floor if location.floor is not None else 1
    if floor_num not in FLOOR_REGISTRY:
        return FLOOR_REGISTRY[1]
    return FLOOR_REGISTRY[floor_num]
