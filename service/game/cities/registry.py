"""마을 production constant (★ Phase 8 (a-2)+(a-3)).

현재 1 city (라스카니아) — apply_time_limit_village_return 사용처.
DEFAULT_CITY_ID + DEFAULT_CITY_ENTRY_SUB_AREA.

CITY_REGISTRY dict + DEFAULT_CITY instance — production caller X (★ codex YAGNI
선례 정합, R2 22d4607 get_floor_definition 패턴). multi-city (★ 노아르크
vs 라스카니아 / 카루이) 진입 시 재도입.
"""

from __future__ import annotations

from typing import Final

from .rascania import RASCANIA

# (a-3) production constants — apply_time_limit_village_return 사용처.
DEFAULT_CITY_ID: Final[str] = RASCANIA.city_id
DEFAULT_CITY_ENTRY_SUB_AREA: Final[str] = RASCANIA.entry_sub_area
