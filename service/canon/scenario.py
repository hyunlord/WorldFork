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


@dataclass(frozen=True)
class StartingWeapon:
    """성인식 선택 무기 (★ 본문 ep_0002 — 부족장 앞 무기 선택)."""

    name: str
    attack_bonus: int
    description: str


# ★ 본문 ep_0002 무기 (★ "스스로에게 맞는 무기를 골라라" — 부족장, ep_0002:48)
#   후보(ep_0002:422): 한손 검/양손 대검/메이스/쇠곤봉/창/작살/양손 도끼/도리깨/
#   대형 망치. 비요른은 "그 누구도 고르지 않은 무기" = 방패(ep_0003 되팔기 비쌈).
#   element는 build 시 _parse_element(name) — 본문 무기는 평범(물리), 시스템은 연결.
COMING_OF_AGE_WEAPONS: tuple[StartingWeapon, ...] = (
    StartingWeapon("한손 검", 4, "균형 잡힌 한손 검 — 무난한 선택."),
    StartingWeapon("양손 대검", 6, "묵직한 양손 대검 — 한 방이 강하다."),
    StartingWeapon("메이스", 5, "타격용 둔기 — 둔중하나 확실하다."),
    StartingWeapon("쇠곤봉", 4, "단단한 쇠곤봉 — 다루기 쉽다."),
    StartingWeapon("창", 5, "긴 사거리의 창 — 거리를 벌린다."),
    StartingWeapon("작살", 4, "갈고리 달린 작살 — 끌어당긴다."),
    StartingWeapon("양손 도끼", 6, "위력적인 양손 도끼 — 묵직한 일격."),
    StartingWeapon("도리깨", 5, "사슬 달린 도리깨 — 변칙적이다."),
    StartingWeapon("대형 망치", 7, "강력한 대형 망치 — 가장 무겁다."),
    StartingWeapon(
        "방패", 1, "되팔 때 가장 비싸다 — 그 누구도 고르지 않은 선택(ep_0003)."
    ),
)

# ★ default 무기 (★ ep_0003 — 그 누구도 고르지 않은 방패, 되팔기 비쌈)
DEFAULT_COMING_OF_AGE_WEAPON = "방패"

_WEAPON_BY_NAME: dict[str, StartingWeapon] = {w.name: w for w in COMING_OF_AGE_WEAPONS}


def find_coming_of_age_weapon(name: str) -> StartingWeapon | None:
    """이름 → 성인식 무기 (★ 미등록 시 None — custom 무기 fallback)."""
    return _WEAPON_BY_NAME.get(name)


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
        # ★ ep_0001 빙의 발단 + ep_0002 성인식 (1인칭). 게임명/인물명은 IP 우회
        #   (코드는 비식별, 게임 화면 인물명은 어댑터가 역변환). 간략 도입(현실 풀 씬 X).
        starting_narrative=(
            "나는 그 게임의 진엔딩을 마주한 순간, 새하얀 빛에 시야를 빼앗겼다. "
            "정신을 차리니 낯선 천장과 일렁이는 횃불, 그리고 내 것이 아닌 거대한 손이 보였다. "
            "어느 신출내기 야만 전사의 몸에 빙의한 것이다 — 오늘이 그 부족의 성년식이라 한다.\n\n"
            "부족 성지의 어두운 숲속 공터, 근육질 야만인들이 둘러섰다. "
            "부족장이 외친다 — 어린 전사들이여, 오늘 성지를 떠나 진정한 전사로 거듭나리라. "
            "성년의 증표로 스스로에게 맞는 무기를 골라야 한다."
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


# ★ 성년 의식 주재자 NPC (★ ep_0002 부족장 — 종족별 정합).
#   성인식 마을(floor 0) 시작 시 encounters에 seed → 대화 대상 + 추천 정합.
COMING_OF_AGE_NPC: dict[str, str] = {
    "barbarian": "부족장",
    "human": "마을 촌장",
    "dwarf": "씨족 장로",
    "beastkin": "숲의 장로",
    "fairy": "정령 장로",
}


def get_coming_of_age_npc(race: Race) -> str:
    """종족별 성년 의식 주재 NPC 이름 (★ 기본 부족장)."""
    return COMING_OF_AGE_NPC.get(race.value, "부족장")


def _eul_reul(word: str) -> str:
    """한국어 목적격 조사 — 받침 有 '을', 無 '를'."""
    if not word:
        return "를"
    last = word[-1]
    if not ("가" <= last <= "힣"):
        return "를"
    return "을" if (ord(last) - 0xAC00) % 28 != 0 else "를"


def build_starting_narrative(
    mode: ScenarioMode, race: Race, weapon: str | None = None
) -> str:
    """시나리오 + 종족 정합 시작 narrative (★ 선택 무기 동적 반영).

    weapon 지정 시 성인식 무기 선택 결과를 narrative에 잇는다 (★ ep_0002 고증).
    """
    cfg = SCENARIO_CONFIGS[mode]
    base = (
        cfg.starting_narrative
        if cfg.starting_narrative
        else RACE_STARTING_NARRATIVES.get(race.value, "")
    )
    if weapon:
        josa = _eul_reul(weapon)
        base = f"{base} 나는 {weapon}{josa} 골라 손에 쥐고 성지를 떠날 채비를 한다."
    return base


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
