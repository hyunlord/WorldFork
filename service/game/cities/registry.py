"""마을 본격 production constant (★ Phase 8 (a-2)+(a-3)).

본 sim 본격 1 city (라프도니아) — apply_time_limit_village_return 본격
DEFAULT_CITY_ID + DEFAULT_CITY_ENTRY_SUB_AREA 사용.

★ CITY_REGISTRY dict + DEFAULT_CITY instance 본격 — production caller X (★ codex YAGNI
선례 정합, R2 22d4607 get_floor_definition 패턴). 본격 multi-city 본격 (★ 노아르크
vs 라프도니아 / 카루이) 발현 시 재도입.
"""

from __future__ import annotations

from typing import Final

from .rapdonia import RAPDONIA

# (a-3) production constants — apply_time_limit_village_return 본격 사용처.
DEFAULT_CITY_ID: Final[str] = RAPDONIA.city_id
DEFAULT_CITY_ENTRY_SUB_AREA: Final[str] = RAPDONIA.entry_sub_area
