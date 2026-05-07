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

    다음 commit:
    - 2차: 일반 세부 스탯 30+ + 특이 5
    - 3차: 위치 (Location)
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
