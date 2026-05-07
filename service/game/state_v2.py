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

    # 정수 (★ 종족별 슬롯, 인간 5개)
    essences: list[Essence] = field(default_factory=list)
    layer_lord_essence: Essence | None = None  # 계층군주 정수 1개 한정

    # 인벤토리/장비
    inventory: Inventory = field(default_factory=Inventory)
    equipment: Equipment = field(default_factory=Equipment)

    def is_alive(self) -> bool:
        return self.hp > 0

    def essence_slot_max(self) -> int:
        """종족별 정수 슬롯 (★ 1차 자료: 인간 5개).

        종족별 차이 = 추후 1차 자료 검증 후 정정.
        """
        return {
            Race.HUMAN: 5,
            Race.DWARF: 5,
            Race.BEASTKIN: 5,
            Race.FAERIE: 5,
            Race.BARBARIAN: 5,
            Race.DRAGONKIN: 5,
        }.get(self.race, 5)

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
    floor: int | None = None  # 1-10 (★ DUNGEON/RIFT/HIDDEN_FIELD)
    sub_area: str | None = None  # "수정동굴 북쪽" / "비석 공동" 등
    rift_id: str | None = None  # "bloody_castle" / "glacier_cave" 등
    # 사이드뷰 좌표는 Tier 4 시점에 추가 — 현재 사용 X면 추가 X

    # ★ 환경
    visibility_meters: int = 10  # 가시거리 (★ 1차 자료 — 어둠 기본 10)
    has_light: bool = False  # 빛 활성 (★ 횃불/정령/포탈)


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

    # ★ 환경 본질
    is_dark_zone: bool = True  # ★ 1층 기본 True (어둠)

    # ★ 파티 / 분배
    party_members: list[str] = field(default_factory=list)  # CharacterV2 name
    # "비요른": 0.9 등 (분배 비율)
    party_share_ratios: dict[str, float] = field(default_factory=dict)


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
class RiftDef:
    """균열 정의 — 작품 본질 (★ Stage 3, 2026-05-07).

    1층 4종 (★ 핏빛성채/빙하굴/녹색탄광/강철의 묘):
    - 일반 8등급 몬스터 + 33% 수호자 정수 드롭
    - 수호자 처치 → 포탈 → 탈출 (★ 34화)
    - 1-5층 매번 리셋

    boss_monster_name이 빈 문자열이면 '1차 자료에 명시 X' (정직).
    """

    rift_id: str  # "bloody_castle" 등
    name: str  # "핏빛성채" 등
    floor: int = 1

    # 진입
    entry_methods: tuple[RiftEntryMethod, ...] = ()
    intentional_offering_grade: int | None = None  # 1층 균열 = 8

    # 환경
    description: str = ""

    # 몬스터
    boss_monster_name: str = ""  # ★ 빈 문자열 = 자료 X (정직)
    boss_grade: int = 8  # 일반 1층 균열 = 8, 변종은 5
    boss_drop_rate: float = 0.33
    boss_is_variant: bool = False  # ★ 핏빛성채 뱀파이어 = 변종
    regular_monster_names: tuple[str, ...] = ()

    # 보상
    hidden_pieces: tuple[str, ...] = ()


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
class Floor1Definition:
    """1층 (수정동굴) 풀 정의 — 작품 본질.

    1차 자료:
    - 168시간 한도 (★ 1주)
    - 가시거리 10m (★ 빛 없으면)
    - 어둠 기본 (★ 빛 없으면 몬스터 활성화 X)
    - 1-5층 매번 리셋
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
