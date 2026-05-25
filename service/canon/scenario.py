"""ScenarioMode + 시나리오 설정 (Phase E-2).

두 가지 시나리오:
- BJORN: 바바리안 고정, 라스카니아 · 차원광장 시작 (ep_0003 anchor)
- NEW_EXPLORER: 5종 종족 자유 선택, default HUMAN
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from service.canon.races import Race


class ScenarioMode(StrEnum):
    BJORN = "bjorn"
    NEW_EXPLORER = "new_explorer"


@dataclass(frozen=True)
class ScenarioConfig:
    name_ko: str
    starting_location: str
    starting_floor: int
    fixed_race: Race | None
    description: str
    canon_anchor: str


SCENARIO_CONFIGS: dict[ScenarioMode, ScenarioConfig] = {
    ScenarioMode.BJORN: ScenarioConfig(
        name_ko="바바리안으로 살아남기",
        starting_location="라스카니아 · 차원광장",
        starting_floor=1,
        fixed_race=Race.BARBARIAN,
        description="바바리안의 시점으로 라스카니아 차원광장에서 시작하는 시나리오.",
        canon_anchor="ep_0003",
    ),
    ScenarioMode.NEW_EXPLORER: ScenarioConfig(
        name_ko="새로운 탐험가",
        starting_location="라스카니아 · 관문 도시",
        starting_floor=1,
        fixed_race=None,
        description="5종 종족 중 원하는 종족을 선택해 라스카니아를 탐험하는 시나리오.",
        canon_anchor="",
    ),
}


def resolve_race_for_scenario(
    mode: ScenarioMode,
    user_choice: Race | None = None,
) -> Race:
    """시나리오 모드 + 사용자 선택 → 최종 Race.

    BJORN: fixed_race=BARBARIAN (user_choice 무시).
    NEW_EXPLORER: user_choice → HUMAN fallback.
    """
    cfg = SCENARIO_CONFIGS[mode]
    if cfg.fixed_race is not None:
        return cfg.fixed_race
    return user_choice if user_choice is not None else Race.HUMAN


def scenario_from_string(value: str) -> ScenarioMode | None:
    """string → ScenarioMode (대소문자 무시)."""
    if not value:
        return None
    lower = value.strip().lower()
    for mode in ScenarioMode:
        if mode.value == lower:
            return mode
    return None
