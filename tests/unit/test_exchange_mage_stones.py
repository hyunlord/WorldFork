"""Phase 8 exchange — Character.stone + exchange_mage_stones unit 본격.

검증 본질:
- Character.stone field default 0 + mutation
- MAGE_STONE_EXCHANGE_RATE 본문 정합 (9=20, 8=100)
- exchange_mage_stones handler:
  * realm != CITY → fail
  * sub_area != exchange_office → fail
  * 마석 X → fail
  * single 9등급 → +20 스톤
  * batch mixed grades
  * non-stone Item (grade=None) 보존
  * side_effects markers
- PlayerActionType.EXCHANGE_MAGE_STONES enum 본격
- gm_agent exchange_office hint 본격
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Item,
    ItemCategory,
    Location,
    Race,
    Realm,
)
from service.game.turn_handler_v2 import (
    EXCHANGE_OFFICE_SUB_AREA,
    MAGE_STONE_EXCHANGE_RATE,
    exchange_mage_stones,
)
from service.sim.types import PlayerActionType

# ─── 1. Character.stone field ───


def test_character_stone_default_0() -> None:
    c = Character(name="투르윈", race=Race.BARBARIAN)
    assert c.stone == 0


def test_character_stone_mutation() -> None:
    c = Character(name="투르윈", race=Race.BARBARIAN)
    c.stone += 100
    assert c.stone == 100
    c.stone -= 30
    assert c.stone == 70


# ─── 2. MAGE_STONE_EXCHANGE_RATE 본문 정합 ───


def test_rate_9_grade_20() -> None:
    """본문 명시: 9등급 마석 = 20 스톤."""
    assert MAGE_STONE_EXCHANGE_RATE[9] == 20


def test_rate_8_grade_100() -> None:
    """본문 명시: 8등급 마석 = 100 스톤."""
    assert MAGE_STONE_EXCHANGE_RATE[8] == 100


def test_rate_higher_grade_higher_value() -> None:
    """등급 ↑ → 가치 ↑ (★ 0=계층군주 가장 비쌈)."""
    for g in range(0, 9):
        assert (
            MAGE_STONE_EXCHANGE_RATE[g]
            > MAGE_STONE_EXCHANGE_RATE[g + 1]
        )


def test_rate_table_covers_0_to_9() -> None:
    assert set(MAGE_STONE_EXCHANGE_RATE.keys()) == set(range(0, 10))


# ─── 3. exchange_mage_stones handler ───


def _make_actor() -> Character:
    return Character(name="투르윈", race=Race.BARBARIAN)


def _exchange_office_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area=EXCHANGE_OFFICE_SUB_AREA,
        city_id="rapdonia",
    )


def _make_stone(grade: int, name: str | None = None) -> Item:
    return Item(
        name=name or f"{grade}등급 마석",
        category=ItemCategory.MATERIAL,
        weight=1,
        grade=grade,
    )


def test_fails_outside_city() -> None:
    """realm != CITY → fail."""
    actor = _make_actor()
    actor.inventory.items.append(_make_stone(9))
    loc = Location(
        realm=Realm.DUNGEON, floor=1, sub_area="진입점"
    )
    result = exchange_mage_stones(actor, loc)
    assert result.success is False
    assert "마을" in result.message or "CITY" in result.message
    # mutation 없음
    assert actor.stone == 0
    assert len(actor.inventory.items) == 1


def test_fails_wrong_sub_area() -> None:
    """마을 본격 다른 sub_area → fail."""
    actor = _make_actor()
    actor.inventory.items.append(_make_stone(9))
    loc = Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="district_7_plaza",
        city_id="rapdonia",
    )
    result = exchange_mage_stones(actor, loc)
    assert result.success is False
    assert EXCHANGE_OFFICE_SUB_AREA in result.message
    assert actor.stone == 0


def test_fails_no_mage_stones() -> None:
    """exchange_office 본격 마석 X → fail."""
    actor = _make_actor()
    result = exchange_mage_stones(actor, _exchange_office_loc())
    assert result.success is False
    assert "마석 X" in result.message
    assert actor.stone == 0


def test_single_9_grade_20_stone() -> None:
    """9등급 1개 → +20 스톤 + 마석 inventory 제거."""
    actor = _make_actor()
    actor.inventory.items.append(_make_stone(9))
    result = exchange_mage_stones(actor, _exchange_office_loc())
    assert result.success is True
    assert actor.stone == 20
    assert len(actor.inventory.items) == 0


def test_single_8_grade_100_stone() -> None:
    actor = _make_actor()
    actor.inventory.items.append(_make_stone(8))
    result = exchange_mage_stones(actor, _exchange_office_loc())
    assert result.success is True
    assert actor.stone == 100


def test_batch_mixed_grades() -> None:
    """9등급 3 + 8등급 2 = 60 + 200 = 260 스톤."""
    actor = _make_actor()
    for _ in range(3):
        actor.inventory.items.append(_make_stone(9))
    for _ in range(2):
        actor.inventory.items.append(_make_stone(8))
    result = exchange_mage_stones(actor, _exchange_office_loc())
    assert result.success is True
    assert actor.stone == 260
    assert len(actor.inventory.items) == 0


def test_non_stone_items_preserved() -> None:
    """grade=None Item (★ 포션 등) 본격 보존."""
    actor = _make_actor()
    actor.inventory.items.append(_make_stone(9))
    actor.inventory.items.append(
        Item(name="포션", category=ItemCategory.CONSUMABLE, weight=1)
    )
    result = exchange_mage_stones(actor, _exchange_office_loc())
    assert result.success is True
    assert actor.stone == 20
    assert len(actor.inventory.items) == 1
    assert actor.inventory.items[0].name == "포션"
    assert actor.inventory.items[0].grade is None


def test_existing_stone_accumulates() -> None:
    """이미 보유한 stone 본격 누적."""
    actor = _make_actor()
    actor.stone = 1000
    actor.inventory.items.append(_make_stone(8))
    result = exchange_mage_stones(actor, _exchange_office_loc())
    assert result.success is True
    assert actor.stone == 1100  # 1000 + 100


def test_side_effects_emitted() -> None:
    actor = _make_actor()
    actor.inventory.items.append(_make_stone(8))
    result = exchange_mage_stones(actor, _exchange_office_loc())
    assert f"exchanged_stones={actor.name}:1" in result.side_effects
    assert f"stone_gained={actor.name}:+100" in result.side_effects


def test_batch_message_includes_count_and_total() -> None:
    actor = _make_actor()
    for _ in range(2):
        actor.inventory.items.append(_make_stone(8))
    result = exchange_mage_stones(actor, _exchange_office_loc())
    assert "2개 환전" in result.message
    assert "+200 스톤" in result.message


# ─── 4. PlayerActionType enum ───


def test_action_type_in_enum() -> None:
    assert PlayerActionType.EXCHANGE_MAGE_STONES.value == "exchange_mage_stones"


# ─── 5. gm_agent exchange_office hint (★ wire) ───


def test_gm_prompt_exchange_office_hint() -> None:
    from service.game.gm_agent import _format_city_context

    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "exchange_office",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "EXCHANGE_MAGE_STONES" in out
    assert "9등급=20" in out
    assert "8등급=100" in out


def test_gm_prompt_other_sub_area_no_hint() -> None:
    """district_7_plaza 본격 EXCHANGE hint X (★ exchange_office 본격만)."""
    from service.game.gm_agent import _format_city_context

    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "district_7_plaza",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "EXCHANGE_MAGE_STONES" not in out
