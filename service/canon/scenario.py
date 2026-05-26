"""ScenarioMode + 시나리오 설정 (Phase E-2/3).

두 가지 시나리오:
- BJORN: 바바리안 고정, 라스카니아 · 차원광장 시작 (ep_0003 anchor)
- NEW_EXPLORER: 5종 종족 자유 선택, default HUMAN
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    # ★ phase-e-3: 시나리오 시작 inventory (frozen dataclass → tuple)
    starting_inventory: tuple[str, ...] = field(default_factory=tuple)
    # ★ phase-e-5: 시나리오 시작 narrative (BJORN hardcoded, NEW_EXPLORER race별)
    starting_narrative: str = ""


SCENARIO_CONFIGS: dict[ScenarioMode, ScenarioConfig] = {
    ScenarioMode.BJORN: ScenarioConfig(
        name_ko="바바리안으로 살아남기",
        starting_location="라스카니아 · 차원광장",
        starting_floor=1,
        fixed_race=Race.BARBARIAN,
        description="바바리안의 시점으로 라스카니아 차원광장에서 시작하는 시나리오.",
        canon_anchor="ep_0003",
        # ★ 본문 정합 (ep_0002-0005):
        # - ep_0002: 성인식에서 무기 하나 선택
        # - ep_0003: 비요른 → 방패 선택 ("시작 무기 중에서도 방패가 되팔았을 때 가장 비싸다")
        # - ep_0004: "야만인들도 전부 무기 하나만 달랑 들고 있어서"
        # - ep_0005: "방패 하나만 달랑 가진 좆밥 바바리안"
        starting_inventory=("방패",),
        # ★ 1인칭 + ep_0003 정합 (라프도니아 → 라스카니아 IP 치환)
        starting_narrative=(
            "나는 라스카니아 차원광장에 서 있다. "
            "미궁 입구가 멀리 보인다. "
            "방패 하나를 든 채로, 첫 미궁에 들어가야 한다."
        ),
    ),
    ScenarioMode.NEW_EXPLORER: ScenarioConfig(
        name_ko="새로운 탐험가",
        starting_location="라스카니아 · 관문 도시",
        starting_floor=1,
        fixed_race=None,
        description="5종 종족 중 원하는 종족을 선택해 라스카니아를 탐험하는 시나리오.",
        canon_anchor="",
        # ★ commit 4의 종족별 default inventory 적용
        starting_inventory=(),
        # ★ NEW_EXPLORER narrative는 race별 — build_starting_narrative() 사용
        starting_narrative="",
    ),
}

# ★ phase-e-5: NEW_EXPLORER 종족별 시작 narrative (1인칭 + 본문 정합)
RACE_STARTING_NARRATIVES: dict[str, str] = {
    "barbarian": (
        "나는 도끼를 들고 라스카니아 차원광장에 섰다. "
        "미궁을 향한 첫걸음이다."
    ),
    "human": (
        "나는 검을 차고 라스카니아 차원광장에 섰다. "
        "미궁의 어둠이 부른다."
    ),
    "dwarf": (
        "나는 망치를 어깨에 메고 라스카니아 차원광장에 섰다. "
        "미궁 깊은 곳을 향해 나아갈 때다."
    ),
    "beastkin": (
        "나는 라스카니아 차원광장에 섰다. "
        "발톱 외에 다른 무기는 없다. "
        "본능만이 의지다."
    ),
    "fairy": (
        "나는 단검을 손에 쥐고 라스카니아 차원광장에 섰다. "
        "정령의 속삭임이 들린다."
    ),
}


def build_starting_narrative(mode: ScenarioMode, race: Race) -> str:
    """시나리오 + 종족 정합 시작 narrative."""
    cfg = SCENARIO_CONFIGS[mode]
    if cfg.starting_narrative:
        return cfg.starting_narrative
    return RACE_STARTING_NARRATIVES.get(race.value, "")


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
