"""state_v2.py 단위 테스트."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from service.game.state_v2 import (
    BeastkinTribe,
    Character,
    Equipment,
    Essence,
    EssenceColor,
    EssenceGrade,
    EssenceOrigin,
    EssenceType,
    Inventory,
    Item,
    ItemCategory,
    Race,
    Skill,
    SkillType,
)

# ─── Skill ───


def test_skill_active_with_cost() -> None:
    s = Skill(
        "긴급복원",
        SkillType.ACTIVE,
        "5분 전 장비 복원",
        soul_cost=20,
        cooldown_seconds=300,
    )
    assert s.name == "긴급복원"
    assert s.soul_cost == 20


def test_skill_passive_no_cost() -> None:
    s = Skill("육체보존", SkillType.PASSIVE, "재생력 大")
    assert s.soul_cost is None


def test_skill_frozen() -> None:
    s = Skill("X", SkillType.PASSIVE, "")
    with pytest.raises(FrozenInstanceError):
        s.name = "Y"  # type: ignore[misc]


# ─── Essence ───


def test_essence_basic() -> None:
    e = Essence(
        name="고블린 정수",
        grade=EssenceGrade.GRADE_9,
        color=EssenceColor.GREEN,
        essence_type=EssenceType.DPS_MELEE,
        origin=EssenceOrigin.MONSTER_DROP,
        monster_source="고블린",
        stat_bonuses={"근력": 7, "민첩": 5},
    )
    assert e.grade == EssenceGrade.GRADE_9
    assert not e.is_guardian
    assert e.stat_bonuses["근력"] == 7


def test_essence_guardian() -> None:
    e = Essence(
        name="라이칸스트로프 정수",
        grade=EssenceGrade.GRADE_5,
        color=EssenceColor.RAINBOW,
        essence_type=EssenceType.DPS_MELEE,
        origin=EssenceOrigin.GUARDIAN_DROP,
        monster_source="라이칸스트로프",
        is_guardian=True,
    )
    assert e.is_guardian
    assert e.color == EssenceColor.RAINBOW


def test_essence_layer_lord() -> None:
    e = Essence(
        name="어둠의 정수",
        grade=EssenceGrade.LAYER_LORD,
        color=EssenceColor.BLACK,
        essence_type=EssenceType.MAGE,
        origin=EssenceOrigin.LAYER_LORD_KILL,
        monster_source="어둠의 군주",
        is_layer_lord=True,
    )
    assert e.is_layer_lord


# ─── Item / Inventory ───


def test_item_basic() -> None:
    i = Item(
        "라이티늄 도끼",
        ItemCategory.WEAPON,
        weight=15,
        stat_bonuses={"근력": 8},
    )
    assert i.weight == 15


def test_item_numbers() -> None:
    i = Item(
        "No.1911 파벨라 회중시계",
        ItemCategory.NUMBERS,
        weight=1,
        is_numbers=True,
        numbers_id=1911,
    )
    assert i.is_numbers
    assert i.numbers_id == 1911


def test_inventory_add_within_weight() -> None:
    inv = Inventory(weight_max=50)
    item = Item("나이프", ItemCategory.WEAPON, weight=2)
    assert inv.add(item) is True
    assert inv.weight_total == 2


def test_inventory_overweight_rejected() -> None:
    inv = Inventory(weight_max=10)
    big = Item("강철거인 무기", ItemCategory.WEAPON, weight=20)
    assert inv.add(big) is False
    assert len(inv.items) == 0


def test_inventory_remove_by_name() -> None:
    inv = Inventory()
    inv.add(Item("나이프", ItemCategory.WEAPON, weight=1))
    inv.add(Item("배낭", ItemCategory.ACCESSORY, weight=3))
    removed = inv.remove("나이프")
    assert removed is not None
    assert removed.name == "나이프"
    assert len(inv.items) == 1


# ─── Equipment ───


def test_equipment_aggregate_bonuses() -> None:
    eq = Equipment(
        weapon=Item(
            "도끼", ItemCategory.WEAPON, weight=10, stat_bonuses={"근력": 8}
        ),
        armor=Item(
            "강철 갑옷",
            ItemCategory.ARMOR,
            weight=20,
            stat_bonuses={"내구력": 10, "근력": 2},
        ),
    )
    bonuses = eq.aggregated_bonuses()
    assert bonuses["근력"] == 10
    assert bonuses["내구력"] == 10


# ─── Character ───


def test_character_basic() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN, is_player=True)
    assert c.is_alive()
    assert c.essence_slot_max() == 5


def test_character_dead_at_zero_hp() -> None:
    c = Character(name="X", race=Race.HUMAN, hp=0)
    assert not c.is_alive()


def test_character_beastkin_with_tribe() -> None:
    c = Character(
        name="미샤",
        race=Race.BEASTKIN,
        sub_race=BeastkinTribe.RED_CAT,
    )
    assert c.sub_race == BeastkinTribe.RED_CAT


def test_essence_absorb_basic() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    e = Essence(
        name="고블린 정수",
        grade=EssenceGrade.GRADE_9,
        color=EssenceColor.GREEN,
        essence_type=EssenceType.DPS_MELEE,
        origin=EssenceOrigin.MONSTER_DROP,
        monster_source="고블린",
    )
    assert c.absorb_essence(e) is True
    assert c.essence_slots_used() == 1


def test_essence_absorb_slot_full() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    for i in range(5):
        e = Essence(
            name=f"정수_{i}",
            grade=EssenceGrade.GRADE_9,
            color=EssenceColor.GREEN,
            essence_type=EssenceType.DPS_MELEE,
            origin=EssenceOrigin.MONSTER_DROP,
            monster_source=f"몬스터_{i}",
        )
        assert c.absorb_essence(e) is True

    overflow = Essence(
        name="overflow",
        grade=EssenceGrade.GRADE_9,
        color=EssenceColor.GREEN,
        essence_type=EssenceType.DPS_MELEE,
        origin=EssenceOrigin.MONSTER_DROP,
        monster_source="X",
    )
    assert c.absorb_essence(overflow) is False
    assert c.essence_slots_used() == 5


def test_essence_absorb_duplicate_active() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    skill = Skill("덫 생성", SkillType.ACTIVE, "...")

    e1 = Essence(
        name="고블린 정수",
        grade=EssenceGrade.GRADE_9,
        color=EssenceColor.GREEN,
        essence_type=EssenceType.DPS_MELEE,
        origin=EssenceOrigin.MONSTER_DROP,
        monster_source="고블린",
        active_skills=(skill,),
    )
    e2 = Essence(
        name="홉 고블린 정수",
        grade=EssenceGrade.GRADE_8,
        color=EssenceColor.GREEN,
        essence_type=EssenceType.DPS_MELEE,
        origin=EssenceOrigin.MONSTER_DROP,
        monster_source="홉 고블린",
        active_skills=(skill,),
    )

    assert c.absorb_essence(e1) is True
    assert c.absorb_essence(e2) is False  # 중복 차단


def test_layer_lord_essence_slot() -> None:
    c = Character(name="이백호", race=Race.HUMAN)

    # 일반 정수 5개 채우고도 계층군주 가능
    for i in range(5):
        c.essences.append(
            Essence(
                name=f"정수_{i}",
                grade=EssenceGrade.GRADE_9,
                color=EssenceColor.GREEN,
                essence_type=EssenceType.DPS_MELEE,
                origin=EssenceOrigin.MONSTER_DROP,
                monster_source=f"몬스터_{i}",
            )
        )

    layer = Essence(
        name="어둠의 정수",
        grade=EssenceGrade.LAYER_LORD,
        color=EssenceColor.BLACK,
        essence_type=EssenceType.MAGE,
        origin=EssenceOrigin.LAYER_LORD_KILL,
        monster_source="어둠의 군주",
        is_layer_lord=True,
    )
    assert c.absorb_essence(layer) is True
    assert c.layer_lord_essence is layer


def test_layer_lord_only_one() -> None:
    c = Character(name="X", race=Race.HUMAN)
    layer1 = Essence(
        name="어둠의 정수",
        grade=EssenceGrade.LAYER_LORD,
        color=EssenceColor.BLACK,
        essence_type=EssenceType.MAGE,
        origin=EssenceOrigin.LAYER_LORD_KILL,
        monster_source="어둠의 군주",
        is_layer_lord=True,
    )
    layer2 = Essence(
        name="혼돈의 정수",
        grade=EssenceGrade.LAYER_LORD,
        color=EssenceColor.RED,
        essence_type=EssenceType.MAGE,
        origin=EssenceOrigin.LAYER_LORD_KILL,
        monster_source="혼돈의 군주",
        is_layer_lord=True,
    )
    assert c.absorb_essence(layer1) is True
    assert c.absorb_essence(layer2) is False  # 1캐릭 1개 한정
