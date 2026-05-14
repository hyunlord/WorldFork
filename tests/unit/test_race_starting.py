"""Phase 8 race-starting — 종족별 시작 자금/아이템 본격 unit.

검증 본질 (★ docs/village_spec.md §7.5 정합):
- RACE_STARTING_STONE: 바바리안=0 (★ 3화 본문 정합)
- 다른 종족 default 0 (★ 본문 X — placeholder)
- _make_barbarian_starting_items: 식량 Item (★ 3화 본문)
- _race_starting_items: race 본격 분기
- plan_character_to_v2 production caller 본격:
  * 바바리안 plan → stone=0 + 식량 inventory
  * 인간 plan → stone=0 + empty inventory (★ default)

본 commit 본문 정직 정공법:
- 바바리안만 본문 분기 (★ 3화 명시)
- 다른 종족 default (★ 추측 X — 후속 본문 발견 시 분기 추가)
"""

from __future__ import annotations

from service.game.init_from_plan import (
    RACE_STARTING_STONE,
    _make_barbarian_starting_items,
    _race_starting_items,
    plan_character_to_v2,
)
from service.game.state_v2 import ItemCategory, Race
from service.pipeline.types import CharacterPlan

# ─── 1. RACE_STARTING_STONE 본격 ───


def test_barbarian_stone_0_from_3hwa() -> None:
    """3화 본문: 부족장 식량만, 화폐 X (★ 바바리안 신참 stone=0)."""
    assert RACE_STARTING_STONE[Race.BARBARIAN] == 0


def test_only_barbarian_explicit() -> None:
    """본 commit 본격 본문 명시 종족만 분기 — 다른 종족 default (★ 본인 #19)."""
    assert set(RACE_STARTING_STONE.keys()) == {Race.BARBARIAN}


def test_other_races_default_to_0_via_get() -> None:
    """본문 X 종족 → .get(race, 0) → 0 (★ placeholder)."""
    for race in Race:
        if race == Race.BARBARIAN:
            continue
        # 본격 다른 종족 본격 default 0 본격
        assert RACE_STARTING_STONE.get(race, 0) == 0


# ─── 2. _make_barbarian_starting_items 본격 ───


def test_barbarian_items_has_weekly_food() -> None:
    """3화 본문: 부족장 일주일 식량."""
    items = _make_barbarian_starting_items()
    food = next((i for i in items if "식량" in i.name), None)
    assert food is not None
    assert food.category == ItemCategory.CONSUMABLE


def test_barbarian_items_no_mage_stones() -> None:
    """시작 아이템 본격 마석 X (★ 시작 시 보스 처치 X)."""
    items = _make_barbarian_starting_items()
    for item in items:
        assert item.grade is None, f"{item.name} 본격 grade={item.grade}"


def test_barbarian_food_description_cites_3hwa() -> None:
    """description 본격 본문 출처 명시 (★ 정직 정공법)."""
    items = _make_barbarian_starting_items()
    food = items[0]
    assert "3화" in food.description or "부족장" in food.description


# ─── 3. _race_starting_items 본격 분기 ───


def test_barbarian_starts_with_items() -> None:
    items = _race_starting_items(Race.BARBARIAN)
    assert len(items) > 0


def test_human_starts_empty() -> None:
    """본문 X 종족 default empty (★ placeholder)."""
    items = _race_starting_items(Race.HUMAN)
    assert items == []


def test_other_races_start_empty() -> None:
    """본문 X 종족 모두 default empty."""
    for race in [Race.BEASTKIN, Race.DWARF, Race.FAERIE, Race.DRAGONKIN]:
        items = _race_starting_items(race)
        assert items == [], f"{race.value} 본격 본문 X → empty 본격"


# ─── 4. plan_character_to_v2 production caller 본격 ───


def _make_plan(name: str, role: str = "주인공") -> CharacterPlan:
    return CharacterPlan(name=name, role=role, description="...")


def test_barbarian_plan_starts_with_0_stone() -> None:
    """본 commit production caller — 바바리안 plan → character.stone = 0."""
    plan = _make_plan("투르윈", role="주인공 바바리안")
    char = plan_character_to_v2(plan)
    assert char.race == Race.BARBARIAN
    assert char.stone == 0


def test_barbarian_plan_starts_with_food() -> None:
    """바바리안 plan → inventory에 부족장 식량 Item 본격."""
    plan = _make_plan("투르윈", role="주인공 바바리안")
    char = plan_character_to_v2(plan)
    assert char.race == Race.BARBARIAN
    assert len(char.inventory.items) == 1
    assert "식량" in char.inventory.items[0].name


def test_other_race_plan_starts_empty() -> None:
    """본문 X 종족 plan → stone=0 + empty inventory (★ default)."""
    # 인간 본격 (★ role 본격 detect 본격 본격 HUMAN default)
    plan = _make_plan("이한수", role="주인공")
    char = plan_character_to_v2(plan)
    assert char.stone == 0
    assert char.inventory.items == []


def test_faerie_plan_starts_empty() -> None:
    """요정 plan → stone=0 + empty (★ 본문 X)."""
    plan = _make_plan("에르웬", role="동료 요정")
    char = plan_character_to_v2(plan)
    assert char.race == Race.FAERIE
    assert char.stone == 0
    assert char.inventory.items == []
