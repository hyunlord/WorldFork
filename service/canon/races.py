"""종족 base stat + 특성 (Phase E-1).

wiki 012 (종족 설정) + episode 정합:
- 바바리안: 생명력 최고, 근력 ↑, 마법 재능 X, 수영 불가 (ep_0003, wiki 012)
- 인간: 균형, 오러 가능성, 후반 포텐 (wiki 012)
- 드워프: 방어 ↑, 무구의 축복 (넘버스 아이템 1.5×), 소형 (wiki 012)
- 수인: 민첩 유별나게 높음, 후각 ↑, 기감 예민 (wiki 012)
- 요정: 정령술, 기감 ↑, 청각 발달, 수풀 무음 이동 (wiki 012)

용인족 제외 (★ 사용자 결정 — 종족 선택 불가 설정 정합).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Race(StrEnum):
    """플레이어 선택 종족 5종."""

    BARBARIAN = "barbarian"
    HUMAN = "human"
    DWARF = "dwarf"
    BEASTKIN = "beastkin"
    FAIRY = "fairy"


@dataclass(frozen=True)
class RaceConfig:
    """종족 base stat + 특성 정의.

    L1 시작 시 적용 — 레벨업은 별도 계산.
    traits는 설명용 문자열 목록이며 이 commit에서 combat 영향 X.
    """

    name_ko: str
    name_en: str
    hp_base: int
    soul_power_base: int
    max_essences_base: int
    attack_base: int
    defense_base: int
    dex_base: int
    luck_base: int
    traits: list[str] = field(default_factory=list)
    description: str = ""
    # ★ phase-e-4 — NEW_EXPLORER 시나리오 종족별 default inventory
    starting_inventory_default: tuple[str, ...] = field(default_factory=tuple)


# ── 본문 정합 base stat table ────────────────────────────────────────────────

RACE_CONFIGS: dict[Race, RaceConfig] = {
    Race.BARBARIAN: RaceConfig(
        name_ko="바바리안",
        name_en="Barbarian",
        hp_base=120,         # wiki: "생명력이 가장 높은 데다가"
        soul_power_base=10,
        max_essences_base=1,
        attack_base=14,      # wiki: "근력 기댓값도 높아서 아다만티움 장비 착용 가능"
        defense_base=6,
        dex_base=8,          # wiki: "수영을 할 수 없다" — 거구 + 민첩 trade-off
        luck_base=5,
        traits=[
            "근력 +5",
            "체력 +3",
            "유연성 -2",
            "수영 불가",
        ],
        description="거대한 체구와 강한 근력을 지닌 종족. 마법 재능 X.",
        # ★ ep_0002: 카락 성인식 → "양손도끼라! 훌륭하다!" — 바바리안 정합 기본 무기
        starting_inventory_default=("도끼",),
    ),
    Race.HUMAN: RaceConfig(
        name_ko="인간",
        name_en="Human",
        hp_base=100,
        soul_power_base=10,
        max_essences_base=1,
        attack_base=10,
        defense_base=5,
        dex_base=10,
        luck_base=10,        # wiki: "후반 포텐이 좋다" — 행운 균형
        traits=[
            "균형 stat",
            "정수 흡수 +10%",
        ],
        description="라스카니아에서 가장 흔한 종족. 모든 stat 균형, 후반 포텐.",
        # ★ wiki 012: "오러는 무조건 도검류. '검'은 오러를 가장 활용하기 좋은 무기"
        starting_inventory_default=("검",),
    ),
    Race.DWARF: RaceConfig(
        name_ko="드워프",
        name_en="Dwarf",
        hp_base=110,
        soul_power_base=10,
        max_essences_base=1,
        attack_base=11,
        defense_base=9,      # wiki: "사기적인 특수 능력" + 야금술 방어
        dex_base=6,          # wiki: 소형 체구, 작은 키
        luck_base=7,
        traits=[
            "방어력 +4",
            "회피 +5%",
            "무구의 축복 — 장비 효율 ↑",
        ],
        description="장인과 광부의 종족. 야금술과 건축 특화.",
        # ★ wiki 012: "'내 망치를 걸고 맹세', '두모카' = 판결하는 망치 (부족장 칭호)
        starting_inventory_default=("망치",),
    ),
    Race.BEASTKIN: RaceConfig(
        name_ko="수인",
        name_en="Beastkin",
        hp_base=105,
        soul_power_base=10,
        max_essences_base=1,
        attack_base=12,
        defense_base=5,
        dex_base=15,         # wiki: "기본 민첩 스탯이 유별나게 높으며" — 5종 최고
        luck_base=8,
        traits=[
            "민첩성 +5",
            "후각 — 어둠 탐지 ↑",
            "발톱 — 비무장 공격 +3",
        ],
        description="동물귀를 지닌 종족. 민첩성과 감각 능력 특화.",
        # ★ wiki 012: "발톱 — 비무장 공격 +3" traits 정합 — 비무장 출발
        starting_inventory_default=(),
    ),
    Race.FAIRY: RaceConfig(
        name_ko="요정",
        name_en="Fairy",
        hp_base=80,
        soul_power_base=20,  # wiki: 정령술 자원 (엘리멘탈/자연력) — 마력 기반
        max_essences_base=2, # wiki: 기감 뛰어남 — 정수 친화력 ↑
        attack_base=7,
        defense_base=3,
        dex_base=14,         # wiki: "수풀 사이에서 소리를 내지 않은채 이동"
        luck_base=11,
        traits=[
            "영혼력 +10",
            "정수 슬롯 +1",
            "회피 +10%",
            "체력 낮음",
        ],
        description="정령술을 쓰는 종족. 뛰어난 기감과 정수 친화력.",
        # ★ 정령술 마법 위주 + 기동성 정합 — 근접 보조 단검 (wiki 명시 없음)
        starting_inventory_default=("단검",),
    ),
}


# ── lookup helpers ────────────────────────────────────────────────────────────


def get_race_config(race: Race) -> RaceConfig:
    """Race → RaceConfig."""
    return RACE_CONFIGS[race]


def race_from_string(value: str) -> Race | None:
    """string → Race enum (한/영 모두 허용).

    - "바바리안" / "barbarian" / "BARBARIAN" / "Barbarian" → Race.BARBARIAN
    - 빈 문자열 / 미존재 → None
    """
    if not value:
        return None
    lower = value.strip().lower()
    for race in Race:
        if race.value == lower:
            return race
    stripped = value.strip()
    for race, config in RACE_CONFIGS.items():
        if config.name_ko == stripped or config.name_en.lower() == lower:
            return race
    return None


def apply_race_base_stats(state: dict[str, object], race: Race) -> dict[str, object]:
    """SessionState dict에 race base stat 적용.

    commit 2 의 CharacterConfig endpoint에서 호출 예정.
    이 commit에서는 helper 정의만 — 실제 호출은 commit 2.
    """
    config = get_race_config(race)
    return {
        **state,
        "race": race.value,
        "current_hp": config.hp_base,
        "max_hp": config.hp_base,
        "soul_power": config.soul_power_base,
        "max_essences": config.max_essences_base,
    }
