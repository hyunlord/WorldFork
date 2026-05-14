"""Phase 8 village-schema-1 — Item.grade field + _defeat_boss wire 본격.

검증 본질:
- Item.grade: int | None default None
- Item(grade=0..9) 명시 본격
- frozen 본격 mutation X (★ FrozenInstanceError)
- 기존 Item 생성 본격 grade 없이 backward compat
- _defeat_boss 본격 mage stone Item.grade == boss.boss_grade (★ wire 검증)

본 commit village-schema-2 commit 본격 enabler:
- Character.stone field 본격 본격
- EXCHANGE_MAGE_STONES action handler 본격
- MAGE_STONE_EXCHANGE_RATE 본격 grade lookup
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS
from service.game.state_v2 import (
    Character,
    Item,
    ItemCategory,
    Race,
    WorldState,
)
from service.game.turn_handler_v2 import (
    _spawn_boss_encounter,
    execute_attack,
)

# ─── 1. Item.grade field 본격 ───


def test_default_grade_is_none() -> None:
    """기존 Item 생성 본격 grade default None (★ backward compat)."""
    item = Item(name="포션", category=ItemCategory.CONSUMABLE, weight=1)
    assert item.grade is None


def test_explicit_grade_9() -> None:
    """9등급 마석."""
    stone = Item(
        name="고블린의 마석",
        category=ItemCategory.MATERIAL,
        weight=1,
        grade=9,
    )
    assert stone.grade == 9


def test_grade_range_0_to_9() -> None:
    """0=계층군주 ~ 9=일반 (★ MonsterGrade enum 정합)."""
    for g in range(0, 10):
        stone = Item(
            name=f"grade_{g}_stone",
            category=ItemCategory.MATERIAL,
            weight=1,
            grade=g,
        )
        assert stone.grade == g


def test_grade_frozen_immutable() -> None:
    """frozen dataclass — grade 본격 mutation X (★ FrozenInstanceError)."""
    item = Item(
        name="마석", category=ItemCategory.MATERIAL, weight=1, grade=9
    )
    with pytest.raises(FrozenInstanceError):
        item.grade = 5  # type: ignore[misc]


# ─── 2. Backward compat — 기존 Item 생성 본격 ───


def test_create_without_grade_kwarg() -> None:
    """기존 caller 본격 grade kwarg 없이 본격 본격 (★ default None)."""
    item = Item(
        name="횃불",
        category=ItemCategory.CONSUMABLE,
        weight=1,
        description="빛 자원 — 어둠 환경",
    )
    assert item.grade is None
    assert item.description == "빛 자원 — 어둠 환경"


def test_other_fields_unaffected_by_grade() -> None:
    """grade 본격 본격 본격 본격 본격 본격 본격 X (★ field 독립)."""
    item = Item(
        name="블라터의 마석",
        category=ItemCategory.MATERIAL,
        weight=1,
        description="6등급 마석",
        grade=6,
        is_numbers=False,
    )
    assert item.name == "블라터의 마석"
    assert item.category == ItemCategory.MATERIAL
    assert item.weight == 1
    assert item.description == "6등급 마석"
    assert item.grade == 6
    assert item.is_numbers is False


# ─── 3. _defeat_boss wire (★ production caller) ───


def _strong_attacker() -> Character:
    return Character(
        name="투르윈",
        race=Race.BARBARIAN,
        hp=200,
        hp_max=200,
        physical=100,
        strength=600,
        is_player=True,
    )


def test_defeat_boss_normal_grade_6_stone() -> None:
    """저주받은 기사 블라터 (★ 6등급 normal boss) 처치 → Item.grade=6."""
    attacker = _strong_attacker()
    world = WorldState(active_rifts=["bloody_castle"])
    world.active_boss_encounter = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["bloody_castle"], is_variant=False
    )
    world.active_boss_encounter.hp = 1

    execute_attack(attacker, "보스", [attacker], world)

    stones = [
        it for it in attacker.inventory.items if "마석" in it.name
    ]
    assert len(stones) >= 1
    stone = stones[-1]
    assert stone.grade == 6  # ★ blater grade 6
    assert "블라터" in stone.name


def test_defeat_boss_variant_grade_5_stone() -> None:
    """캠보르미어 (★ 5등급 variant) 처치 → Item.grade=5."""
    attacker = _strong_attacker()
    world = WorldState(active_rifts=["bloody_castle"])
    world.active_boss_encounter = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["bloody_castle"], is_variant=True
    )
    world.active_boss_encounter.hp = 1

    execute_attack(attacker, "보스", [attacker], world)

    stones = [
        it for it in attacker.inventory.items if "마석" in it.name
    ]
    assert len(stones) >= 1
    stone = stones[-1]
    assert stone.grade == 5  # ★ variant grade 5
    assert "캠보르미어" in stone.name


def test_defeat_boss_stone_grade_matches_encounter_grade() -> None:
    """모든 rift 본격 — Item.grade == BossEncounter.boss_grade (★ wire 일관)."""
    for rift_id in FLOOR1_RIFT_DEFS:
        attacker = _strong_attacker()
        world = WorldState(active_rifts=[rift_id])
        boss = _spawn_boss_encounter(
            FLOOR1_RIFT_DEFS[rift_id], is_variant=False
        )
        world.active_boss_encounter = boss
        world.active_boss_encounter.hp = 1

        execute_attack(attacker, "보스", [attacker], world)

        stones = [
            it for it in attacker.inventory.items if "마석" in it.name
        ]
        assert stones, f"{rift_id} 본격 마석 X"
        assert stones[-1].grade == boss.boss_grade, (
            f"{rift_id}: grade mismatch — "
            f"item={stones[-1].grade} vs boss={boss.boss_grade}"
        )
