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
    Location,
    Race,
    Realm,
    Skill,
    SkillType,
    WorldState,
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


def test_character_general_stats_default() -> None:
    """일반 세부 스탯 30+ 기본값 (★ 2차 보강)."""
    c = Character(name="X", race=Race.HUMAN)
    assert c.strength == 10
    assert c.agility == 10
    assert c.flexibility == 10
    assert c.bone_strength == 10
    assert c.fighting_spirit == 10
    assert c.height == 170  # ★ 인간 기본
    assert c.weight == 70
    assert c.magic_resistance == 10


def test_character_special_stats_default() -> None:
    """특이 스탯 5 기본값 (★ 본인 짚은 본질)."""
    c = Character(name="X", race=Race.HUMAN)
    assert c.obsession == 0
    assert c.sixth_sense == 0
    assert c.support_rating == 0
    assert c.perception_interference == 0


def test_character_special_stats_settable() -> None:
    """특이 스탯 게임 진행 중 변경 가능 (★ mutable)."""
    c = Character(name="에르웬", race=Race.FAERIE)
    c.obsession = 80  # ★ 얀데레 발현
    c.sixth_sense = 35
    c.support_rating = 50
    assert c.obsession == 80
    assert c.sixth_sense == 35
    assert c.support_rating == 50


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


# ─── Realm / Location / WorldState (★ Stage 1, 2026-05-07) ───


def test_realm_enum() -> None:
    assert Realm.DUNGEON.value == "미궁"
    assert Realm.RIFT.value == "균열"
    assert Realm.HIDDEN_FIELD.value == "히든 필드"
    assert Realm.UNDERGROUND.value == "지하"
    assert Realm.CITY.value == "도시"
    assert Realm.WILDERNESS.value == "야외"


def test_location_default_dark() -> None:
    """1층 어둠 기본 가시거리 10m (★ 1차 자료)."""
    loc = Location(realm=Realm.DUNGEON, floor=1)
    assert loc.visibility_meters == 10
    assert not loc.has_light


def test_location_with_light() -> None:
    loc = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="수정동굴 북쪽",
        visibility_meters=50,
        has_light=True,
    )
    assert loc.has_light
    assert loc.sub_area == "수정동굴 북쪽"


def test_location_rift() -> None:
    loc = Location(
        realm=Realm.RIFT,
        floor=1,
        rift_id="bloody_castle",
    )
    assert loc.realm == Realm.RIFT
    assert loc.rift_id == "bloody_castle"


def test_world_state_default() -> None:
    ws = WorldState()
    assert ws.current_round == 1
    assert ws.hours_in_dungeon == 0
    assert ws.is_dark_zone  # ★ 1층 기본
    assert not ws.is_dimension_collapse


def test_world_state_with_party() -> None:
    ws = WorldState(
        current_round=5,
        hours_in_dungeon=72,
        party_members=["비요른", "에르웬"],
        party_share_ratios={"비요른": 0.9, "에르웬": 0.1},
    )
    assert "비요른" in ws.party_members
    assert ws.party_share_ratios["비요른"] == 0.9


def test_world_state_dimension_collapse() -> None:
    ws = WorldState(is_dimension_collapse=True)
    assert ws.is_dimension_collapse


def test_world_state_active_rifts() -> None:
    ws = WorldState(active_rifts=["bloody_castle", "glacier_cave"])
    assert len(ws.active_rifts) == 2


# ─── Stage 2: MonsterDef + SubArea + Floor1Definition (★ 2026-05-07) ───


def test_essence_drop_basic() -> None:
    from service.game.state_v2 import EssenceDrop

    d = EssenceDrop(
        essence_name="고블린 정수",
        drop_rate=0.0001,
        color_pool=(EssenceColor.GREEN,),
    )
    assert d.drop_rate == 0.0001
    assert EssenceColor.GREEN in d.color_pool


def test_monster_def_basic() -> None:
    from service.game.state_v2 import (
        EssenceDrop,
        MonsterArea,
        MonsterDef,
        MonsterGrade,
    )

    m = MonsterDef(
        name="고블린",
        grade=MonsterGrade.GRADE_9,
        area=MonsterArea.GENERAL,
        drops=(
            EssenceDrop(
                essence_name="고블린 정수",
                drop_rate=0.0001,
                color_pool=(EssenceColor.GREEN,),
            ),
        ),
        behavior="조각칼 / 그르륵",
    )
    assert m.grade == MonsterGrade.GRADE_9
    assert m.requires_light  # default True


def test_sub_area_dark_default() -> None:
    from service.game.state_v2 import SubArea

    sa = SubArea(name="북쪽 통로", description="...")
    assert sa.is_dark
    assert not sa.has_landmark


def test_sub_area_with_landmark() -> None:
    from service.game.state_v2 import SubArea

    sa = SubArea(
        name="비석 공동",
        description="30m 공동",
        has_landmark=True,
        landmark_type="비석",
    )
    assert sa.landmark_type == "비석"


def test_floor1_definition_basic() -> None:
    from service.game.state_v2 import Floor1Definition

    f = Floor1Definition()
    assert f.name == "수정동굴"
    assert f.base_time_hours == 168
    assert f.base_visibility_meters == 10
    assert f.is_dark_default


# ─── Stage 3: RiftDef + Floor1Definition.rifts (★ 2026-05-07) ───


def test_rift_entry_method_enum() -> None:
    from service.game.state_v2 import RiftEntryMethod

    assert RiftEntryMethod.RANDOM_NATURAL.value == "무작위 자연"
    assert RiftEntryMethod.INTENTIONAL_OFFERING.value == "의도적 공물"


def test_rift_def_basic() -> None:
    from service.game.state_v2 import RiftDef, RiftEntryMethod

    r = RiftDef(
        rift_id="test",
        name="테스트 균열",
        entry_methods=(RiftEntryMethod.RANDOM_NATURAL,),
        boss_monster_name="테스트 보스",
    )
    assert r.boss_drop_rate == 0.33
    assert RiftEntryMethod.RANDOM_NATURAL in r.entry_methods


def test_rift_def_unknown_boss_empty() -> None:
    """boss_monster_name 빈 문자열 = 자료 X (★ 정직)."""
    from service.game.state_v2 import RiftDef

    r = RiftDef(rift_id="test", name="X")
    assert r.boss_monster_name == ""


def test_floor1_definition_rifts_default_empty() -> None:
    """Floor1Definition.rifts 기본 빈 tuple."""
    from service.game.state_v2 import Floor1Definition

    f = Floor1Definition()
    assert f.rifts == ()


# ─── Stage 4: LightSource (★ 2026-05-07) ───


def test_light_source_torch() -> None:
    from service.game.state_v2 import LightSource, LightSourceType

    ls = LightSource(
        name="횃불",
        light_type=LightSourceType.TORCH,
        duration_hours=72.0,
        cooldown_hours=None,
        radius_meters=10.0,
        cost_stones=10000,
        is_consumable=False,
    )
    assert ls.duration_hours == 72.0
    assert ls.cost_stones == 10000


def test_light_source_spirit_requires_faerie() -> None:
    from service.game.state_v2 import LightSource, LightSourceType

    ls = LightSource(
        name="정령 등불",
        light_type=LightSourceType.SPIRIT,
        duration_hours=10.0,
        cooldown_hours=2.0,
        radius_meters=10.0,
        cost_stones=0,
        is_consumable=False,
        requires_race="요정",
    )
    assert ls.requires_race == "요정"
    assert ls.cooldown_hours == 2.0


def test_light_source_flare_consumable() -> None:
    from service.game.state_v2 import LightSource, LightSourceType

    ls = LightSource(
        name="조명탄",
        light_type=LightSourceType.FLARE,
        duration_hours=None,
        cooldown_hours=None,
        radius_meters=50.0,
        cost_stones=0,
        is_consumable=True,
    )
    assert ls.duration_hours is None
    assert ls.is_consumable
    assert ls.radius_meters == 50.0


def test_floor1_definition_light_sources_default_empty() -> None:
    from service.game.state_v2 import Floor1Definition

    f = Floor1Definition()
    assert f.light_sources == ()
