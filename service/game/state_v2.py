"""Tier 2 D11+ — 작품 본질 매칭 state schema (★ 1차 commit).

본 파일 1차 commit 범위 (5 dataclass):
- Character: 메인 3대 + 기본 + 정수 슬롯
- Essence: 정수 (등급/색깔/타입/스킬/보너스)
- Skill: 스킬 (액티브/패시브/MP)
- Item: 아이템 (무기/방어구/소비/재료)
- Inventory: 소지품 (무게 + items)
- Equipment: 착용

기존 service/game/state.py는 그대로 보존.
2차 commit에 일반 세부 스탯 30+ + 특이 5 추가.
3차에 Location/World, 4차에 GameState 마이그레이션.

기준: docs/ROADMAP_V2_BARBARIAN.md (★ 작품 본질).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum

# ─── Enum 본질 ───


class Race(StrEnum):
    """6 대종족 (★ 1차 자료 진짜)."""

    HUMAN = "인간"
    DWARF = "드워프"
    BEASTKIN = "수인"
    FAERIE = "요정"
    BARBARIAN = "바바리안"
    DRAGONKIN = "용인족"


class BeastkinTribe(StrEnum):
    """수인 7부족 (★ 5개 명시 + 2개 미명시)."""

    RED_CAT = "적묘족"
    WHITE_WOLF = "백랑족"
    BLACK_BEAR = "흑곰족"
    BLUE_WOLF = "청랑족"
    WHITE_RABBIT = "백토족"
    UNKNOWN_6 = "미명시 6"
    UNKNOWN_7 = "미명시 7"


class EssenceGrade(IntEnum):
    """정수 등급 1(최강) ~ 9(최약), 계층군주 = 0."""

    GRADE_9 = 9
    GRADE_8 = 8
    GRADE_7 = 7
    GRADE_6 = 6
    GRADE_5 = 5
    GRADE_4 = 4
    GRADE_3 = 3
    GRADE_2 = 2
    GRADE_1 = 1
    LAYER_LORD = 0  # 계층군주 (★ 1캐릭 1개 한정)


class EssenceType(StrEnum):
    """정수 type 9개 (★ 본인 결정 1단계)."""

    TANK = "탱커"
    DPS_MELEE = "딜러근접"
    DPS_RANGED = "딜러원거리"
    MAGE = "마법사"
    SUPPORT = "서포터"
    STEALTH = "은신"
    SENSE = "감각"
    TRANSFORM_SUMMON = "변신소환"
    UTILITY = "유틸"


class EssenceColor(StrEnum):
    """정수 색깔 (★ 액티브 결정)."""

    RED = "빨강"
    BLUE = "파랑"
    GREEN = "초록"
    YELLOW = "노랑"
    WHITE = "흰색"
    BLACK = "검정"
    RAINBOW = "무지개"  # ★ 수호자 정수


class EssenceOrigin(StrEnum):
    """정수 획득 경로 (★ ROADMAP V2 진짜)."""

    MONSTER_DROP = "몬스터 드롭"  # 0.01%
    GUARDIAN_DROP = "수호자 드롭"  # 33%, 균열 보스
    LAYER_LORD_KILL = "계층군주 처치"  # 1캐릭 1개
    SYNTHETIC = "합성"  # 무지개섬
    VARIANT = "변종"  # 지하
    PURCHASE = "거래/구매"  # 길드/경매


class SkillType(StrEnum):
    """스킬 분류."""

    ACTIVE = "액티브"
    PASSIVE = "패시브"


class ItemCategory(StrEnum):
    """아이템 분류."""

    WEAPON = "무기"
    ARMOR = "방어구"
    ACCESSORY = "장신구"
    CONSUMABLE = "소비"
    MATERIAL = "재료"
    QUEST = "퀘스트"
    NUMBERS = "넘버스"  # ★ 균열 수호자만
    MAGIC_TOOL = "마도구"


class InjurySeverity(StrEnum):
    """부상 강도 (★ Phase 9.3 — 본문 23/25화 narrative 정합).

    severity 값 (★ Injury.severity string 본격 본격):
    - SCRATCH: 23화 '팔뚝에 스크래치'
    - MAJOR: 25화 '목 상처' + '흉터가 남겠군'
    """

    SCRATCH = "scratch"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class InjuryBodyPart(StrEnum):
    """부상 부위 (★ 본문 narrative 정합 — 23화 팔뚝 / 25화 목)."""

    HEAD = "head"
    NECK = "neck"
    TORSO = "torso"
    ARM = "arm"
    LEG = "leg"


class ClassType(StrEnum):
    """직업 분류 (★ Phase 9.9-b — 5/28화 본문 정합).

    본문 정합:
    - 28화: '6등급 마법사 아루아 레이븐' (★ MAGE)
    - 5화: 신관/마법사 = 중층 이상 직업 (★ PRIEST/MAGE)
    - 본 commit minimal — WARRIOR 본격 본격 wire (★ 9.9-a 신참 길드)
    - 후속 9.9-b2: MAGE/PRIEST/PALADIN 본격 별도 mechanism
    """

    WARRIOR = "warrior"  # ★ 전사 (★ 비요른 + 9.9-a 신참)
    MAGE = "mage"  # ★ 마법사 (★ 28화 — 후속)
    PRIEST = "priest"  # ★ 신관 (★ 5화 — 후속)
    PALADIN = "paladin"  # ★ 성기사 (★ 후속)
    SCOUT = "scout"  # ★ 탐색꾼 (★ 44화 '고블린 숲 필수' — Phase 9.17-b)


class Role(StrEnum):
    """파티 역할군 — Phase 9.17-b (★ 44화 본문 정합).

    44화: '역할군 세밀 / 층 올라갈수록 부재 치명적'.
    - 탱커 (★ 비요른 바바리안)
    - 탐색꾼 (★ 고블린 숲 필수)
    - 마법사 = 공격 (★ 28화 최강)
    - 신관 = 회복 (★ 5화 중층)
    - 성기사 = 본문 명시 X 추측 → SUPPORT
    """

    TANK = "tank"
    DPS = "dps"
    SCOUT = "scout"
    SUPPORT = "support"
    HEALER = "healer"


class Realm(StrEnum):
    """게임 영역 (★ 작품 본질, V4 분석 결과)."""

    DUNGEON = "미궁"  # 1-10층 일반
    RIFT = "균열"  # 균열 차원 (★ 미궁 속 미궁)
    HIDDEN_FIELD = "히든 필드"  # 라르카즈 / 불의 거울 등
    UNDERGROUND = "지하"  # 지하 1층 (무지개섬 / 도서관섬)
    CITY = "도시"  # 라프도니아 / 노아르크 / 카루이
    WILDERNESS = "야외"  # 도시 외 야외


class MonsterGrade(IntEnum):
    """몬스터 등급 (★ 정수와 동일 척도)."""

    GRADE_9 = 9
    GRADE_8 = 8
    GRADE_7 = 7
    GRADE_6 = 6
    GRADE_5 = 5
    GRADE_4 = 4
    GRADE_3 = 3
    GRADE_2 = 2
    GRADE_1 = 1
    LAYER_LORD = 0


# ─── Phase 8 B — 레벨 + 경험치 시스템 ───

# 본인 명시 (★ 2026-05-13 답): 몬스터 사냥 → 경험치, 같은 species 두 번째 0
# (★ "딱 한번 사냥하면 경험치"), 레벨 ↑ → 정수 슬롯 max ↑.
LEVEL_EXP_THRESHOLDS: tuple[int, ...] = (
    0,      # level 1 (★ 시작)
    100,    # level 2 (★ 9등급 2마리 또는 8등급 1마리)
    250,    # level 3
    500,    # level 4
    1000,   # level 5
    2000,   # level 6
    4000,   # level 7
    8000,   # level 8
    16000,  # level 9
    32000,  # level 10 (★ max)
)

# ★ Phase 8 A-2 — 22화 본문 정합 N=N 공식.
# 22화 본문 명시: "1레벨이었던 나는 딱 한 개의 정수만을 흡수할 수 있었지만 …
#  2레벨이 되며 최대 두 개까지 가능해졌다" + 시스템 메시지
#  "최대 흡수 가능 정수가 +1 증가합니다".
# → 레벨 N = 정수 N개 흡수.
# 3+ 레벨: 본문 명시 X — N=N 공식 추정 (★ 22화 정합).
# 7e finding "level 1 = 5 정수 슬롯" 본격 추측 → B commit 본격 정정.
LEVEL_TO_ESSENCE_SLOT_MAX: dict[int, int] = {
    n: n for n in range(1, 11)
}


def level_for_exp(exp: int) -> int:
    """누적 exp → level 계산 (★ 1-indexed, max len(LEVEL_EXP_THRESHOLDS))."""
    for lv in range(len(LEVEL_EXP_THRESHOLDS), 0, -1):
        if exp >= LEVEL_EXP_THRESHOLDS[lv - 1]:
            return lv
    return 1


def slot_max_for_level(level: int) -> int:
    """level → essence_slot_max 본격 (★ max level cap)."""
    max_lv = max(LEVEL_TO_ESSENCE_SLOT_MAX.keys())
    capped = min(max(level, 1), max_lv)
    return LEVEL_TO_ESSENCE_SLOT_MAX[capped]


def next_level_threshold(level: int) -> int:
    """현재 level의 다음 threshold (★ max level 시 자기 threshold)."""
    if level >= len(LEVEL_EXP_THRESHOLDS):
        return LEVEL_EXP_THRESHOLDS[-1]
    return LEVEL_EXP_THRESHOLDS[level]  # 0-indexed: idx=level = next 본격


class MonsterArea(StrEnum):
    """1층 몬스터 등장 영역 본질."""

    NORTH = "북쪽"
    SOUTH = "남쪽"  # ★ 노움 (27화 본문)
    EAST = "동쪽"
    WEST = "서쪽"
    GENERAL = "전역"  # ★ 일반 고블린 등
    NEAR_PORTAL = "포탈 근처"


class RiftEntryMethod(StrEnum):
    """균열 진입 방식 (★ 1차 자료 + 본문 27/102/374화)."""

    RANDOM_NATURAL = "무작위 자연"  # ★ 102화: 1일차 자동, 1층 전역 포탈
    INTENTIONAL_OFFERING = "의도적 공물"  # ★ 374화: 비석 + 8등급 마석


class RiftChamberType(StrEnum):
    """균열 sub_area (챕터) 유형 (★ Phase 8 A1 — namu 6장 챕터 구조).

    namu 본격 챕터 구조:
    - ENTRANCE: 진입 챕터 (외곽 검문소 / 동굴 입구 등)
    - CORRIDOR: 일반 진행 챕터 (외성벽 시가지 / 절벽 갱도 등)
    - MID_BOSS: 중간 보스 챕터 (★ 시체골렘 / 고블린 폭탄병 / 상위 변이종 예티)
    - BOSS: 수호자 챕터 (★ 일반 or 변종 수호자)
    """

    ENTRANCE = "진입"
    CORRIDOR = "일반"
    MID_BOSS = "중간보스"
    BOSS = "보스"


class BountyKillCondition(StrEnum):
    """현상금 처리 조건 (★ Stage 7 동적 시스템)."""

    DEAD_OR_ALIVE = "생사 무관"
    KILL_ONLY = "처치 한정"  # ★ 입막음
    CAPTURE_ONLY = "생포 한정"  # ★ 정보 추출


class LightSourceType(StrEnum):
    """빛 자원 종류 (★ 1층 본질, 본문 11/23/24화).

    ★ LIGHT_GEM / PORTAL 등은 자료 추가 검증 + 진짜 사용 시점에 추가 (YAGNI).
    """

    TORCH = "횃불"  # 23화 (3일 / 1만 스톤 마도구)
    SPIRIT = "정령 등불"  # 11화 (10시간 / 회복 2시간 / 요정 한정)
    FLARE = "조명탄"  # 24/419화 (50m 반경, 단발)


# ─── Skill ───


@dataclass(frozen=True, slots=True)
class Skill:
    """스킬 (액티브 or 패시브).

    예:
      Skill("긴급복원", SkillType.ACTIVE, "5분 전 장비 복원",
            soul_cost=20, cooldown_seconds=300)
      Skill("육체보존", SkillType.PASSIVE, "재생력 大")
    """

    name: str
    type: SkillType
    description: str
    soul_cost: int | None = None  # MP 소모 (액티브만)
    cooldown_seconds: int | None = None  # 액티브 쿨타임


# ─── Essence ───


@dataclass(frozen=True, slots=True)
class Essence:
    """정수 (★ 작품 본질 핵심).

    예:
      Essence(
          name="고블린 정수",
          grade=EssenceGrade.GRADE_9,
          color=EssenceColor.GREEN,
          essence_type=EssenceType.DPS_MELEE,
          origin=EssenceOrigin.MONSTER_DROP,
          monster_source="고블린",
      )
    """

    name: str
    grade: EssenceGrade
    color: EssenceColor
    essence_type: EssenceType
    origin: EssenceOrigin
    monster_source: str  # 출처 몬스터 (★ 합성/변종은 ?)

    active_skills: tuple[Skill, ...] = ()  # 수호자는 다수
    passive_skills: tuple[Skill, ...] = ()
    stat_bonuses: dict[str, int] = field(default_factory=dict)

    is_guardian: bool = False  # 수호자 정수 (★ 1.5x + 모든 액티브)
    is_layer_lord: bool = False  # 계층군주 (★ 1캐릭 1개)
    is_synthetic: bool = False  # 합성 정수
    is_variant: bool = False  # 변종 정수


# ─── Item ───


@dataclass(frozen=True, slots=True)
class Item:
    """아이템 (★ 무기/방어구/넘버스 등)."""

    name: str
    category: ItemCategory
    weight: int  # 무게 (소지품 한계)
    stat_bonuses: dict[str, int] = field(default_factory=dict)
    description: str = ""
    requires: dict[str, int] = field(
        default_factory=dict
    )  # 사용 요구치 (예: 근력 30+)

    is_numbers: bool = False  # 넘버스 아이템
    numbers_id: int | None = None  # 1~9999+
    is_soul_bound: bool = False  # 영혼 귀속

    # ★ Phase 8 village-schema-1 — 마석 등급 (★ 0=계층군주, 9=일반).
    # 환전 rate lookup 본격 사용처 (★ village-schema-2 commit 본격).
    grade: int | None = None


# ─── Phase 9.16-b — Shop catalog (★ BUY 본격 inventory) ───


@dataclass(frozen=True, slots=True)
class ShopItem:
    """상점 판매 catalog (★ Phase 9.16-b shop BUY).

    21화 본문 정합:
    - 하프 아머 36만 / 무기 25만 (★ 본문 직접)

    본 commit 대상:
    - blacksmith (★ 장비)
    - general_store (★ 포션/소모품)

    Item 본격 본격 차이:
    - ShopItem = 상점 catalog (★ name + base_price)
    - Item = 캐릭터 inventory instance (★ 구매 시 변환)
    """

    name: str
    item_category: ItemCategory
    base_price: int
    weight: int = 1
    grade: int | None = None


# ─── Inventory / Equipment ───


@dataclass
class Inventory:
    """소지품.

    무게 한계 = 근력 비례 (★ 2차 commit 추가).
    weight_max는 보유자 캐릭터 근력으로 외부에서 산출.
    """

    items: list[Item] = field(default_factory=list)
    weight_max: int = 100

    @property
    def weight_total(self) -> int:
        return sum(item.weight for item in self.items)

    @property
    def is_overweight(self) -> bool:
        return self.weight_total > self.weight_max

    def add(self, item: Item) -> bool:
        """추가 가능하면 True. 무게 초과 시 False."""
        if self.weight_total + item.weight > self.weight_max:
            return False
        self.items.append(item)
        return True

    def remove(self, item_name: str) -> Item | None:
        for i, item in enumerate(self.items):
            if item.name == item_name:
                return self.items.pop(i)
        return None


@dataclass
class Equipment:
    """착용 장비 (4 슬롯)."""

    weapon: Item | None = None
    armor: Item | None = None
    accessory_1: Item | None = None
    accessory_2: Item | None = None

    def all_equipped(self) -> list[Item]:
        return [
            it
            for it in (
                self.weapon,
                self.armor,
                self.accessory_1,
                self.accessory_2,
            )
            if it is not None
        ]

    def aggregated_bonuses(self) -> dict[str, int]:
        """착용 장비 stat_bonuses 합산."""
        result: dict[str, int] = {}
        for item in self.all_equipped():
            for stat, val in item.stat_bonuses.items():
                result[stat] = result.get(stat, 0) + val
        return result


# ─── Character (메인 3대 + 기본 + 정수 슬롯) ───


# ─── Injury dataclass + severity table (★ Phase 9.3) ───


@dataclass(frozen=True, slots=True)
class Injury:
    """부상 instance — 본인 답 '어떤 상처를 얻었냐에 따라 회복 기간 필요'.

    본문 정합 (★ 23/25화 narrative):
    - severity: InjurySeverity value 문자열
    - body_part: InjuryBodyPart value 문자열
    - recovery_days: 마을 본격 회복 본격 본격 본격
    - scar: 흉터 (★ 25화 '흉터가 남겠군' 본문 정합)

    Producer (★ ATTACK damage 본격 generation):
    - execute_attack 본격 hp_loss 본격 severity mapping
    - body_part random 본격 (★ rng inject)

    Consumer (★ WAIT_IN_VILLAGE recovery):
    - WAIT 본격 recovery_days-- mutation (★ frozen — 새 instance)
    - recovery_days<=0 본격 injury 제거 + injury_healed marker
    - 죽은 멤버 회복 X (★ 본인 답)
    """

    severity: str
    body_part: str
    recovery_days: int
    scar: bool = False


@dataclass(frozen=True, slots=True)
class Scar:
    """영구 흉터 — Phase 9.6 (★ 25화 '흉터가 남겠군' 본문 정합).

    Producer:
    - execute_wait_in_village: scar=True injury 회복 완료 시 Scar 생성
    - execute_heal_at_temple: 동일

    본 commit cosmetic only — 능력치/HP_max 영향 X (★ 본문 명시 X).
    후속 본격: 영향 mechanism (★ 본문 발견 시 보강).
    """

    body_part: str  # ★ 원 Injury.body_part
    origin_severity: str  # ★ 원 Injury.severity (major / critical 본격)


@dataclass(frozen=True, slots=True)
class Disability:
    """영구 신체 손상 — Phase 9.10 (★ 71/214화 절단 / 117/268화 회복 path).

    Scar (9.6) = cosmetic, Disability (9.10) = gameplay 영향 (★ HP_max penalty).

    Producer:
    - WAIT_IN_VILLAGE / HEAL_AT_TEMPLE 본격 critical injury 회복 완료 → Disability
    - 9.6 흉터 본격 별도 (★ scar = major+, disability = critical만)

    회복:
    - HEAL_AT_TEMPLE 본격 stone × DISABILITY_HEAL_COST (★ 268화 신성력)
    - 후속 9.9-b2: 재생 스킬 (★ 117화 직업 system)

    추측 (★ 본문 X — docstring 명시):
    - kind='amputation' default (★ 본문 narrative 다양화 후속)
    - hp_max_penalty 수치 (★ 본문 X)
    """

    body_part: str
    kind: str = "amputation"
    hp_max_penalty: int = 0


# severity별 recovery 본격 — 본문 X 추측 (★ 후속 발견 시 보강).
SEVERITY_RECOVERY_DEFAULT: dict[str, int] = {
    InjurySeverity.SCRATCH.value: 2,  # ★ 1-3일 본격
    InjurySeverity.MINOR.value: 7,  # ★ 1주
    InjurySeverity.MAJOR.value: 21,  # ★ 3주
    InjurySeverity.CRITICAL.value: 60,  # ★ 2개월
}


# severity별 흉터 본격 — 25화 본문 정합 (major+ 흉터).
SEVERITY_LEAVES_SCAR: dict[str, bool] = {
    InjurySeverity.SCRATCH.value: False,
    InjurySeverity.MINOR.value: False,
    InjurySeverity.MAJOR.value: True,  # ★ 25화 '흉터가 남겠군'
    InjurySeverity.CRITICAL.value: True,
}


@dataclass
class LightStateOnCharacter:
    """캐릭터의 빛 자원 사용 상태 (★ Stage 7, 게임 진행 중 변동).

    본문 본질:
    - 횃불: 머리 위 끼움 ('바바리안 캔들 모드' 23화) / 3일 지속
    - 정령 등불: 요정만, 10시간 후 회복 2시간
    - 조명탄: 단발
    """

    active_source_name: str | None = None  # 활성 빛 자원 이름
    remaining_duration_hours: float = 0.0  # 남은 지속 시간
    cooldown_remaining_hours: float = 0.0  # 회복 대기 (정령)
    consumables: dict[str, int] = field(default_factory=dict)  # {"조명탄": 3}


@dataclass
class Character:
    """게임 등장인물.

    1차 commit 범위:
    - 메인 3대 스탯 (육체/정신/이능)
    - 기본 (이름/종족/HP/MP)
    - 정수 슬롯 + 계층군주 정수
    - 인벤토리/장비

    2차 commit (★ 본 단계, 2026-05-07):
    - 일반 세부 스탯 30+ (★ 1티어 + 감각 + 방어 + 행운/기술 + 신체)
    - 마법/저항
    - 특이 스탯 5개 (★ 본인 짚은 본질 — 일상/대화/행동 영향)

    다음 commit:
    - 3차: 위치 (Location), World, GameState 통합
    """

    # 기본
    name: str
    race: Race
    level: int = 1
    experience: int = 0  # ★ Phase 8 B — 누적 exp (★ level_for_exp 본격)
    is_player: bool = False

    # 종족 하위 (수인 부족)
    sub_race: BeastkinTribe | None = None

    # 메인 스탯 3대 (★ 작품 본질)
    physical: int = 10
    mental: int = 10
    special: int = 10

    # ─── 일반 1티어 ───
    strength: int = 10  # 근력 (데미지 + 무게 한계)
    agility: int = 10  # 민첩 (이속 + 동체시력 + 반사신경)
    flexibility: int = 10  # 유연성 (회피 + 곡예 + 추락 흡수)

    # ─── 감각 ───
    sight: int = 10  # 시각
    smell: int = 10  # 후각
    hearing: int = 10  # 청각
    cognitive_speed: int = 10  # 인지력 (불릿 타임)
    accuracy: int = 10  # 명중률
    evasion: int = 10  # 회피율
    jump_power: int = 10  # 도약력

    # ─── 방어 ───
    bone_strength: int = 10  # 골강도 (베기/타격 감쇄)
    bone_density: int = 10  # 골밀도
    physical_resistance: int = 10  # 물리내성
    durability: int = 10  # 내구력
    pain_resistance: int = 10  # 고통저항
    poison_resistance: int = 10
    fire_resistance: int = 10
    cold_resistance: int = 10
    lightning_resistance: int = 10
    dark_resistance: int = 10

    # ─── 행운/기술 ───
    luck: int = 10  # 행운 (드롭률 + 크리)
    dexterity: int = 10  # 손재주
    cutting_power: int = 10  # 절삭력
    fighting_spirit: int = 10  # 투쟁심
    endurance: int = 10  # 인내심
    stamina: int = 10  # 지구력

    # ─── 신체 ───
    height: int = 170  # 신장 cm (★ 1차 자료: 인간 평균 170)
    weight: int = 70  # 체중 kg
    regen_rate: int = 10  # 재생력
    natural_regen: int = 10  # 자연재생력 (★ 5000+ 사실상 불사)

    # ─── 마법/저항 ───
    magic_resistance: int = 10  # 항마력 (★ 400+ 제압면역, 1500+ 마법면역)
    mental_power: int = 10  # 정신력 (정신계 마법/상태이상 저항)

    # ─── ★ 특이 스탯 (본인 짚은 본질 — 일상/대화/행동 영향) ───
    obsession: int = 0  # 집착 (★ 정신 산하, 미스터리, 맹목적 욕구)
    sixth_sense: int = 0  # 육감 (★ 0~50 시작, 위험 감지)
    support_rating: int = 0  # 지지도 (★ 우두머리 시 통솔력/부족 스킬)
    perception_interference: int = 0  # 인식방해 (★ 빙의 정체 은폐)
    # cognitive_speed는 일반 감각에 이미 포함 (★ 인지력)

    # 자원
    hp: int = 100
    hp_max: int = 100
    soul_power: int = 0  # 영혼력 (MP)
    soul_power_max: int = 0
    # ★ Phase 8 exchange — 화폐. 마석 환전 + 거래소 / 여관 / 길드 본격 사용처.
    # 본문 출처: 환전 9등급=20스톤, 2년차 세금=80만 스톤, 컴멜비 1박=9000 (namu §4).
    # 시작값 0 (★ 본문 시작값 명시 X, 보수적).
    stone: int = 0

    # 정수 (★ 종족별 슬롯, 인간 5개)
    essences: list[Essence] = field(default_factory=list)
    layer_lord_essence: Essence | None = None  # 계층군주 정수 1개 한정

    # 인벤토리/장비
    inventory: Inventory = field(default_factory=Inventory)
    equipment: Equipment = field(default_factory=Equipment)

    # ★ Stage 7: 빛 자원 상태 (1층 어둠 본질)
    light_state: LightStateOnCharacter = field(default_factory=LightStateOnCharacter)

    # ★ Phase 9.3 — 부상 schema (★ 23/25화 narrative 정합).
    # WAIT_IN_VILLAGE 본격 recovery_days-- mutation.
    injuries: list[Injury] = field(default_factory=list)

    # ★ Phase 9.6 — 영구 흉터 (★ 25화 '흉터가 남겠군' 본문 정합).
    # scar=True injury 회복 완료 시 Scar append (★ cosmetic only).
    scars: list[Scar] = field(default_factory=list)

    # ★ Phase 9.10 — 영구 disability (★ 71/214화 절단, gameplay 영향).
    # CRITICAL injury 회복 완료 시 transition (★ HP_max penalty).
    disabilities: list[Disability] = field(default_factory=list)

    # ★ Phase 9.9-b — 정수 등급 + 직업 (★ 28화 '6등급 마법사' / 5화 직업 본격).
    grade: int = 1  # ★ 정수 등급 1-9 (★ 본 commit default 신참)
    class_type: str = "warrior"  # ★ ClassType value (★ 본 commit default WARRIOR)

    # ★ Phase 9.14 — 명성 (★ 452화 '명성 → 기본 호감도' / 74화 '작은 발칸').
    # 보스 처치 / 균열 클리어 시 증가, 초면 NPC 호감도 bonus 본격 사용처.
    fame: int = 0

    # ★ Phase 9.17-c2 — 밤친구 marker (★ 6/111화 정합).
    # True 시 던전 출구 / 사망 시 sim_runner caller 자동 해산.
    # 본문 정합:
    # - 6화: '임시 협력 관계의 은어'
    # - 111화: 1층 한정 culture (★ NIGHT_COMPANION_FLOOR_LIMIT)
    is_temporary: bool = False

    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def effective_hp_max(self) -> int:
        """disability penalty 적용 HP_max (★ Phase 9.10, min 1)."""
        penalty = sum(d.hp_max_penalty for d in self.disabilities)
        return max(1, self.hp_max - penalty)

    def has_active_light(self) -> bool:
        """현재 활성화된 빛 자원이 있는가 (★ 1층 어둠 = 가시거리 10m 회피)."""
        return (
            self.light_state.active_source_name is not None
            and self.light_state.remaining_duration_hours > 0.0
        )

    def essence_slot_max(self) -> int:
        """정수 슬롯 max (★ Phase 8 B — level 본격).

        본질:
        - level 1 = 5 (★ 1차 자료 + 7e finding 정합)
        - level ↑ → slot ↑ (★ 본인 답 2026-05-13)
        - max level 10 = 20

        본격 X: 종족별 차이 (★ 1차 자료 명시 X — 인간 5 외 동일 가정).
        후속 정정 1차 자료 본격.
        """
        return slot_max_for_level(self.level)

    def essence_slots_used(self) -> int:
        return len(self.essences)

    def can_absorb_essence(self, essence: Essence) -> bool:
        """정수 흡수 가능 여부.

        - 슬롯 만석 X
        - 중복 X (★ 액티브/패시브 1개라도 겹치면 X)
        - 계층군주 정수는 별도 슬롯 (1캐릭 1개)
        """
        if essence.is_layer_lord:
            return self.layer_lord_essence is None

        if self.essence_slots_used() >= self.essence_slot_max():
            return False

        my_actives = {s.name for e in self.essences for s in e.active_skills}
        my_passives = {s.name for e in self.essences for s in e.passive_skills}
        new_actives = {s.name for s in essence.active_skills}
        new_passives = {s.name for s in essence.passive_skills}

        if my_actives & new_actives or my_passives & new_passives:
            return False

        return True

    def absorb_essence(self, essence: Essence) -> bool:
        """정수 흡수. 가능하면 True."""
        if not self.can_absorb_essence(essence):
            return False
        if essence.is_layer_lord:
            self.layer_lord_essence = essence
        else:
            self.essences.append(essence)
        return True


# ─── Location / WorldState (★ Stage 1, 2026-05-07) ───


@dataclass
class Location:
    """캐릭터 위치 + 환경.

    1차 자료 본질 (★ V4 분석):
    - 1층 = 어둠 기본 (★ 본문 11화 명시, 빛 없으면 가시거리 10m)
    - 빛 있으면 몬스터 활성화
    - 균열 = 별개 차원 (★ 27화 정의, 미궁 속 미궁)
    """

    realm: Realm
    floor: int | None = None  # 1-10 (★ DUNGEON/RIFT/HIDDEN_FIELD), 0 = 마을
    sub_area: str | None = None  # "수정동굴 북쪽" / "비석 공동" 등
    rift_id: str | None = None  # "bloody_castle" / "glacier_cave" 등
    # ★ Phase 8 A1 — 균열 내부 sub_area (RiftSubAreaDef.id) + 변종 표시
    rift_sub_area: str | None = None  # "bc_ch1" 등 (★ 균열 챕터 id)
    rift_is_variant: bool = False  # ★ 본 균열 인스턴스가 변종인지
    # 사이드뷰 좌표는 Tier 4 시점에 추가 — 현재 사용 X면 추가 X

    # ★ Phase 8 a-3 — 마을 식별자 (★ realm=CITY 시 — 본인 답 7.2 "별개 구역")
    city_id: str | None = None

    # ★ 환경
    visibility_meters: int = 10  # 가시거리 (★ 1차 자료 — 어둠 기본 10)
    has_light: bool = False  # 빛 활성 (★ 횃불/정령/포탈)


@dataclass
class BossEncounter:
    """균열 수호자 encounter (★ Phase 8 A3 — 1층 균열 핵심).

    rift_def.boss_chamber_id 도달 시 spawn. ATTACK으로 hp 감소,
    hp=0 도달 시 처치 — defeated_bosses + cleared_rifts append,
    active_boss_encounter=None, 보상 정수 marker + 마석 inventory append.

    boss_id 규칙: f"{rift_id}_{normal|variant}" (★ 변종 분기).
    weakness_*: namu spot 정보 (★ A1 BossWeakness 본격 inherit).
    """

    rift_id: str
    boss_id: str
    boss_name: str
    boss_grade: int
    is_variant: bool

    hp: int
    hp_max: int

    weakness_element: str | None = None
    weakness_strategy: str | None = None


class SimulationStatus(StrEnum):
    """1층 simulation 상태 (★ Phase 8 A4 / C).

    1층 종료 / 전환 조건:
    - 7일 (168h) 만료 → TIME_LIMIT_REACHED → 자동 마을 귀환 (★ A4)
    - 전원 사망 (HP=0) → PARTY_DEFEATED (★ A4)
    - 2층 진입 → FLOOR_TRANSITION (★ C — 본 sim 본격 종료, 후속 2층 sim)
    """

    ACTIVE = "active"
    TIME_LIMIT_REACHED = "time_limit"
    PARTY_DEFEATED = "party_defeated"
    FLOOR_TRANSITION = "transition"


@dataclass
class FloorState:
    """본 generic floor state (★ Phase 8 R4 — N층 enabler).

    본질:
    - 본 층 transition state 추적 (★ floor_number 본격 어느 층인지)
    - entry_sub_area_from_prev: 이전 층 어느 sub_area에서 진입했는지
      (★ EXIT_TO_PREV_FLOOR 본격 복귀 지점)
    - returned_to_prev: 한 번이라도 이전 층 복귀한 적 있는가
    - current_sub_area: 본 층 내부 현재 sub_area (★ 콘텐츠 본격 후속)

    Phase 8 R4:
    - FloorTwoState → FloorState generic rename
    - floor_number field 본격 어느 층 state인지 명시 (★ floor_states[N] key 본격)
    """

    floor_number: int  # ★ 본 state 본격 어느 층 (★ floor_states[N] key 본격)
    entered: bool = False
    entry_sub_area_from_prev: str | None = None
    current_sub_area: str = ""  # ★ 본 층 default — caller 본격 본격 본격
    returned_to_prev: bool = False


@dataclass
class WorldState:
    """게임 진행 상태 (★ 작품 본질, V4 분석).

    - current_round: 라프도니아 차원광장 N번째 도전
    - hours_in_dungeon: 1층 168시간 한도 (★ 1차 자료)
    - is_dimension_collapse: 100판 1번 진짜 재앙
    """

    current_round: int = 1
    hours_in_dungeon: int = 0
    is_dimension_collapse: bool = False  # ★ 100판 1번 (1차 자료)

    # ★ 균열 시스템
    active_rifts: list[str] = field(default_factory=list)  # rift_id list

    # ★ Phase 8 A3 — 보스 + 클리어 추적
    defeated_bosses: list[str] = field(default_factory=list)  # boss_id list
    cleared_rifts: list[str] = field(default_factory=list)  # rift_id list
    active_boss_encounter: BossEncounter | None = None

    # ★ Phase 9 rift-cooldown — rift_id → period (month_number) 본격 본격.
    # 27화 본문 정합 cooldown counter (★ 자연 활성 + 의도적 활성 둘 다 기록).
    rift_last_opened_periods: dict[str, int] = field(default_factory=dict)

    # ★ Phase 9.7 — NPC 호감도 (★ runtime state, NPCDef frozen 본격 별도).
    # 19화/643화 정합: DIALOGUE 본격 ±, 0-100 cap, LIBRARY_SEARCH 등 효과 trigger.
    npc_affinities: dict[str, int] = field(default_factory=dict)

    # ★ 환경 본질
    is_dark_zone: bool = True  # ★ 1층 기본 True (어둠)

    # ★ 파티 / 분배
    party_members: list[str] = field(default_factory=list)  # CharacterV2 name
    # "비요른": 0.9 등 (분배 비율)
    party_share_ratios: dict[str, float] = field(default_factory=dict)
    # ★ Phase 9.9-a — 파티 정원 (★ 본인 답 기본 5, 9.9-b/c 본격 본격).
    max_party_members: int = 5

    # ★ Stage 7: 동적 현상금 (약탈자 PvP 진행 중 발령/해제)
    active_bounties: list[BountyEntry] = field(default_factory=list)

    # ★ Phase 8 A4 — 1층 simulation 종료 조건 mechanism
    simulation_status: SimulationStatus = SimulationStatus.ACTIVE
    simulation_over_reason: str | None = None  # "7일 (168h) 만료..." 등
    simulation_over_turn: int | None = None  # 종료 trigger turn

    # ★ Phase 8 B — "딱 한번" 경험치 mechanism (★ 본인 답 2026-05-13).
    # party 본격 본격 사냥 본격 species id set (★ MonsterDef.name / Boss.boss_id).
    # 같은 species 두 번째 사냥 → exp 0.
    first_killed_species: set[str] = field(default_factory=set)

    # ★ Phase 8 R4 — generic floor state (★ floor_two 본격 N층 enabler).
    # floor_states[N] = 본 N층 state (★ enter_next_floor 시 생성 본격).
    # first_entry_parties: 본 sim에서 최초 진입 보너스 발현한 floor set
    # (★ N in first_entry_parties → 본격 진입 시 보너스 X).
    # current_floor 본격 location.floor 본격 단일 source (★ R4 본격 본격 X 본격).
    floor_states: dict[int, FloorState] = field(default_factory=dict)
    first_entry_parties: set[int] = field(default_factory=set)

    # ★ Phase 9 — 마을 시간 mechanism (★ 19화 본문: 매월 1일 자정 미궁 열림 / 30일).
    # TIME_LIMIT_REACHED 본격 마을 turn loop 본격 (★ WAIT_IN_VILLAGE / ENTER_DUNGEON).
    # 본 commit 본격 sim_runner 본격 종료 condition 유지 — 후속 commit 본격 본격
    # 본격 마을 turn loop 본격 cascade 본격.
    month_number: int = 1  # ★ 1, 2, 3, ... (★ 1월부터 시작)
    day_in_month: int = 1  # ★ 1~30 (★ DAYS_PER_MONTH cap)


# ─── Stage 2: MonsterDef + SubArea + Floor1Definition (★ 2026-05-07) ───


@dataclass(frozen=True, slots=True)
class EssenceDrop:
    """몬스터 정수 드롭 정의.

    1차 자료 본질:
    - 드롭률 0.01% (★ 일반 9등급)
    - 등급 ↑ → 드롭률 소폭 ↑
    - 3등급+ 색 풀 5-6 (★ 색깔별 액티브)
    """

    essence_name: str  # "고블린 정수"
    drop_rate: float  # 0.0001 ~ 0.05
    color_pool: tuple[EssenceColor, ...] = ()  # 9등급 보통 1색


@dataclass(frozen=True, slots=True)
class MonsterDef:
    """몬스터 정의 (★ 1층 9등급).

    본문 본질:
    - 빛 없으면 활성화 X (★ 11화 명시)
    - 영역별 등장 (★ 노움 = 남쪽, 27화)
    """

    name: str  # "고블린" / "노움" / "슬라임" 등
    grade: MonsterGrade
    area: MonsterArea
    drops: tuple[EssenceDrop, ...] = ()
    behavior: str = ""  # 본문 본질
    requires_light: bool = True  # ★ 빛 있어야 활성화 (1층 본질)


@dataclass(frozen=True, slots=True)
class SubArea:
    """1층 sub_area (★ 본문 본질).

    예:
    - 수정동굴 진입점 (포탈 근처)
    - 북쪽 통로 (고블린 영역)
    - 남쪽 노움 영역
    - 비석 공동 (★ 374화 — 30m 공동, 의도적 균열 진입)
    - 동쪽 / 서쪽 통로
    """

    name: str
    description: str
    accessible_from: tuple[str, ...] = ()  # 인접 sub_area 이름
    monster_names: tuple[str, ...] = ()  # 등장 몬스터 (MonsterDef.name)
    is_dark: bool = True
    has_landmark: bool = False  # 비석 / 포탈 / 입구
    landmark_type: str | None = None  # "비석" / "포탈" / "입구"


@dataclass(frozen=True, slots=True)
class RiftSubAreaDef:
    """균열 내부 sub_area (챕터) 정의 (★ Phase 8 A1 — namu 본문 정합).

    별도 dataclass 이유: 1층 SubArea (수정동굴 영역)와 분리. 균열 챕터는
    BOSS / MID_BOSS / 진입 / 일반의 4 유형 + 단방향/양방향 연결 + 필드
    효과 + 히든 피스 등 균열 한정 정보를 보유.

    예 (핏빛성채):
      RiftSubAreaDef(
          id="bc_ch1",
          name="외곽 검문소",
          chamber_type=RiftChamberType.ENTRANCE,
          connections=("bc_ch2",),
          monsters=("데드맨", "병사 데드맨", "지휘관 데드맨"),
      )
    """

    id: str  # 균열 내부 고유 id (예: "bc_ch1")
    name: str  # 한국어 이름 (예: "외곽 검문소")
    chamber_type: RiftChamberType
    description: str = ""
    connections: tuple[str, ...] = ()  # 인접 sub_area id (양방향 가정)
    monsters: tuple[str, ...] = ()  # 등장 몬스터 이름
    mid_boss_name: str | None = None  # 중간 보스 이름 (★ 시체골렘 등)
    mid_boss_grade: int | None = None
    field_effect: str | None = None  # ★ 저체온증 등 (빙하굴 ch3)
    hidden_pieces: tuple[str, ...] = ()  # 챕터별 히든 피스


@dataclass(frozen=True, slots=True)
class BossWeakness:
    """보스 약점 정의 (★ Phase 8 A1 — namu 명시 spot 정보).

    예 (폭군 타룬바스):
      BossWeakness(element="전격", note="namu 명시 — 전격 속성 약점")
    """

    element: str  # 속성명 (★ 전격/화/냉기 등)
    note: str = ""


@dataclass(frozen=True, slots=True)
class VariantTrigger:
    """변종 균열 spawn trigger (★ Phase 8 A2 — 본인 가설 + namu '매우 드물게').

    본 commit: 단순 base_probability (★ namu '매우 드물게' ≈ 2%).
    후속 본격 trigger condition (defeated_bosses / floor_clears) 본격.

    None = 변종 X (★ namu 명시 X 본격 — 녹색 탄광 / 강철의 묘).
    """

    base_probability: float = 0.02  # ★ namu '매우 드물게'


@dataclass(frozen=True, slots=True)
class RiftDef:
    """균열 정의 — 작품 본질 (★ Phase 8 A1 본격 확장, 2026-05-13).

    1층 4종 (★ 핏빛성채/빙하굴/녹색탄광/강철의 묘):
    - 일반 8등급 몬스터 + 33% 수호자 정수 드롭
    - 수호자 처치 → 포탈 → 탈출 (★ 34화)
    - 1-5층 매번 리셋

    Phase 8 A1 핵심 변경:
    - boss_monster_name 단일 필드 → normal/variant 분리
    - sub_areas (RiftSubAreaDef 튜플) 추가 — namu 본격 챕터 구조
    - party_capacity 추가 — 5명 한도 (본인 결정)
    - intentional_offering_source_floor / area 추가 — 2층 망자의 땅 등
    - essence_color 추가 — 보상 정수 색 (red/blue/green/yellow)
    - boss_weakness 추가 — namu spot 정보 (★ 폭군 타룬바스 전격 등)
    """

    rift_id: str  # "bloody_castle" 등
    name: str  # "핏빛성채" 등

    # 일반 수호자 (★ 6.2 schema 분리)
    normal_boss_name: str  # ★ "저주받은 기사 블라터" 등
    normal_boss_grade: int  # ★ 일반 grade (★ namu X 시 후속 진단)

    # 챕터 구조 (★ namu 본격 정합)
    sub_areas: tuple[RiftSubAreaDef, ...]
    entrance_id: str  # 진입 chamber id (★ "bc_ch1" 등)
    boss_chamber_id: str  # 보스 chamber id (★ "bc_ch5" 등)

    # 진입 / 공물
    intentional_offering_source_floor: int  # ★ 2층 본격
    intentional_offering_source_area: str  # ★ "망자의 땅" 등
    intentional_offering_grade: int  # ★ 1층 균열 = 8

    # 보상 정수 색 (★ 6.4 spec)
    essence_color: str  # "red" / "blue" / "green" / "yellow"

    floor: int = 1

    # 변종 수호자 (★ 6.2 schema 분리, namu X 시 None)
    variant_possible: bool = False
    variant_boss_name: str | None = None
    variant_boss_grade: int | None = None
    # 변종 trigger (★ Phase 8 A2 — None = 변종 spawn X)
    variant_trigger: VariantTrigger | None = None

    # 보스 약점 (★ namu spot 정보, 옵션)
    boss_weakness: BossWeakness | None = None

    # 진입 방식 + 파티 한도
    entry_methods: tuple[RiftEntryMethod, ...] = ()
    party_capacity: int = 5  # ★ 본인 결정 (namu 본격 후속 진단)

    # 드롭률
    boss_drop_rate: float = 0.33

    # 환경
    description: str = ""

    # ★ Phase 9 rift-cooldown — A-1 spec 본격 실작동 (★ 27화 본문 정합).
    # 27화: "최소 3주기 세 달" / "대부분 5~6주기 사이 랜덤" / "맥시멈 8주기".
    # 1 주기 = 1 month (★ Phase 9 month_number — 19화 30일 정합).
    cooldown_min_periods: int = 3
    cooldown_max_periods: int = 8
    cooldown_typical_range: tuple[int, int] = (5, 6)


@dataclass(frozen=True, slots=True)
class LightSource:
    """빛 자원 정의 (★ Stage 4, 1층 본질).

    1차 자료:
    - 1층 어둠 기본 (가시거리 10m)
    - 빛 활성 시 몬스터 등장 (★ 11화)

    duration_hours=None = 단발 (조명탄).
    cooldown_hours=None = 회복 X (소비 / 재사용).
    requires_race=None = 모든 종족 사용 가능.
    """

    name: str
    light_type: LightSourceType
    duration_hours: float | None
    cooldown_hours: float | None
    radius_meters: float
    cost_stones: int
    is_consumable: bool
    requires_race: str | None = None


@dataclass(frozen=True, slots=True)
class BountyEntry:
    """현상금 진짜 동적 (★ Stage 7).

    게임 진행 중 동적 생성/삭제:
    - 약탈자가 메시지 스톤으로 현상금 발령
    - 표적 처치 시 issuer가 보상 지불
    """

    target_name: str
    amount_stones: int
    issuer_name: str
    issuer_faction: str | None = None
    kill_condition: BountyKillCondition = BountyKillCondition.DEAD_OR_ALIVE
    reason: str = ""
    issued_at_hours: int = 0  # 미궁 진입 후 N시간차


@dataclass(frozen=True, slots=True)
class MessageStoneSpec:
    """메시지 스톤 마도구 정의 (★ 10화 본문).

    1차 자료 + 본문:
    - 반경 300m 통신
    - 미리 공명시켜 둔 스톤끼리만 대화 가능
    - 약탈자 집단의 정보 전달 핵심 도구
    """

    range_meters: int = 300  # ★ 10화 본문
    requires_pre_resonance: bool = True  # ★ 미리 공명


@dataclass(frozen=True, slots=True)
class RaiderFaction:
    """약탈자 집단 정의 (★ 본문 발견).

    예: '수정 연합' (★ 10화 — 1층 주 무대).
    """

    name: str
    primary_floors: tuple[int, ...] = ()  # 1층 등
    description: str = ""


@dataclass(frozen=True, slots=True)
class BountyConfig:
    """층 PvP / 현상금 시스템 (★ 1층).

    1차 자료:
    - 메시지 스톤 300m
    - 약탈자 집단 활동 (수정 연합 등)
    - 표준 1만 / 강화 2만 스톤 (★ 11화 본문)
    """

    message_stone: MessageStoneSpec = field(default_factory=MessageStoneSpec)
    known_factions: tuple[RaiderFaction, ...] = ()
    standard_bounty_stones: int = 10000  # ★ 11화 표준
    escalated_bounty_stones: int = 20000  # ★ 11화 강화


@dataclass(frozen=True, slots=True)
class FloorDefinition:
    """본 floor 풀 정의 — N층 generic (★ Phase 8 R2).

    1차 자료 (1층 본격):
    - 168시간 한도 (★ 1주)
    - 가시거리 10m (★ 빛 없으면)
    - 어둠 기본 (★ 빛 없으면 몬스터 활성화 X)
    - 1-5층 매번 리셋

    Phase 8 R2:
    - Floor1Definition → FloorDefinition rename (★ N층 enabler)
    - portal_to_next / portal_to_prev: 본 층 ↔ 인접 층 진입 sub_area whitelist
    - Floor1Definition은 backward-compat alias 본격 본격
    """

    name: str = "수정동굴"
    floor_number: int = 1
    base_time_hours: int = 168
    base_visibility_meters: int = 10
    is_dark_default: bool = True

    sub_areas: tuple[SubArea, ...] = ()
    monsters: tuple[MonsterDef, ...] = ()
    rifts: tuple[RiftDef, ...] = ()
    light_sources: tuple[LightSource, ...] = ()
    bounty_config: BountyConfig | None = None

    # ★ Phase 8 R2 — 인접 층 진입 sub_area whitelist (★ N층 enabler).
    # 1층: portal_to_next = 4 portal 통로 (C commit), portal_to_prev = empty.
    # 후속 2층: portal_to_prev = {2층 도착 지점 ...} (★ R3+R4 본격 정합).
    portal_to_next: frozenset[str] = frozenset()
    portal_to_prev: frozenset[str] = frozenset()


# ★ Phase 8 R2 — backward-compat alias. 본 commit 본격 caller 본격 다수
# (`get_floor1_definition() -> Floor1Definition` 등) 본격 본격 본격.
Floor1Definition = FloorDefinition
