"""ScenarioMode + 시나리오 설정 (Phase E-2/3, 성인식 마을 재검토).

두 가지 시나리오 — 둘 다 20살 성년 성인식부터 (★ 본문 ep_0002 고증):
- BJORN: 바바리안 고정, 부족 성지 성인식 시작 (ep_0002 anchor)
- NEW_EXPLORER: 5종 종족 자유 선택, 종족별 성년 의식 시작

★ IP 정책: 코드/데이터는 IP 안전 명칭(라스카니아) — git push 안전.
  게임 화면 출력만 원작 명칭으로 역변환 (frontend 어댑터 unmaskIp).
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
    starting_floor: int  # ★ 0 = 성인식 마을/성지, 1+ = 던전
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
        starting_location="라스카니아 · 부족 성지",
        starting_floor=0,  # ★ 성인식 마을 (★ 던전 1층 X — 본문 ep_0002)
        fixed_race=Race.BARBARIAN,
        description="바바리안의 20살 성년 성인식, 부족 성지에서 시작.",
        canon_anchor="ep_0002",
        # ★ 본문 정합 (ep_0002-0005):
        # - ep_0002: 성지 성인식 — 부족장이 어린 전사들의 성년 선언, 무기 선택
        # - ep_0003: 비요른 → 방패 선택 (되팔 때 가장 비싸다)
        # - ep_0004-0005: "방패 하나만 달랑 가진 좆밥 바바리안"
        starting_inventory=("방패",),
        # ★ 1인칭 + ep_0002 성인식 고증 (코드는 IP 안전 명칭, 게임 화면은 어댑터 역변환)
        starting_narrative=(
            "나는 부족 성지에 서 있다. "
            "어두운 숲속 공터, 일렁이는 횃불 사이로 근육질 야만인들이 둘러섰다. "
            "부족장이 외친다 — 어린 전사들이여, 오늘 성지를 떠나 진정한 전사로 거듭나리라. "
            "성년의 증표로 시작 무기를 골라야 한다. 내 손에는 방패 하나가 들려 있다."
        ),
    ),
    ScenarioMode.NEW_EXPLORER: ScenarioConfig(
        name_ko="새로운 탐험가",
        starting_location="라스카니아 · 성년 의식장",
        starting_floor=0,  # ★ 성년 의식 마을 (★ 던전 X)
        fixed_race=None,
        description="5종 종족 중 하나를 골라 20살 성년 의식부터 탐험.",
        canon_anchor="ep_0002",
        # ★ commit 4의 종족별 default inventory 적용
        starting_inventory=(),
        # ★ NEW_EXPLORER narrative는 race별 — build_starting_narrative() 사용
        starting_narrative="",
    ),
}

# ★ phase-e-5 / 성인식 재검토: NEW_EXPLORER 종족별 성년 의식 narrative (1인칭)
RACE_STARTING_NARRATIVES: dict[str, str] = {
    "barbarian": (
        "나는 스무 살 봄, 부족 성지에서 성년을 맞는다. "
        "도끼 한 자루를 받아 들고 성지를 떠날 채비를 한다."
    ),
    "human": (
        "나는 스무 살 성년식 날, 변경 마을 광장에 섰다. "
        "검을 허리에 차고 성년의 첫걸음을 내디딘다."
    ),
    "dwarf": (
        "나는 성년의 의식을 마치고 산악 대장간을 나선다. "
        "직접 벼린 망치를 어깨에 메고 길을 떠난다."
    ),
    "beastkin": (
        "나는 성년을 맞아 숲의 성소에 섰다. "
        "발톱 외에 다른 무기는 없다. 본능만이 의지다."
    ),
    "fairy": (
        "나는 스무 살 성년 의식 날, 정령숲에서 깨어난다. "
        "단검을 손에 쥐고 정령의 속삭임을 따라간다."
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
