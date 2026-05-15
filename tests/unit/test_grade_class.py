"""Phase 9.9-b grade-class — Character.grade + class_type + 길드 wire 본격 unit.

검증 본질:
- ClassType enum value (★ warrior/mage/priest/paladin)
- Character.grade default 1
- Character.class_type default 'warrior'
- 28화 본문 정합 (★ 6등급 마법사 아루아 레이븐)
- _create_recruit_character 본격 grade=1 / class=warrior wire
- gm_agent prompt 본격 등급 + 직업 표시
- sim_runner ctx 본격 serialize

본문 정합:
- 28화: '6등급 마법사 아루아 레이븐' (★ grade = 정수 등급)
- 5화: 신관/마법사 = 중층 이상 (★ 신참 길드 본격 본격 X)
- 73화: 5등급 정수 2개 = 상위 탐험가
"""

from __future__ import annotations

import random
from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    ClassType,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import _create_recruit_character
from service.sim.sim_runner import _refresh_context

# ─── 1. ClassType enum ───


def test_classtype_warrior() -> None:
    assert ClassType.WARRIOR.value == "warrior"


def test_classtype_mage_28hwa() -> None:
    """28화 본문 정합 — 6등급 마법사 아루아 레이븐."""
    assert ClassType.MAGE.value == "mage"


def test_classtype_priest_5hwa() -> None:
    """5화 본문 정합 — 신관/마법사 중층 이상."""
    assert ClassType.PRIEST.value == "priest"


def test_classtype_paladin() -> None:
    assert ClassType.PALADIN.value == "paladin"


# ─── 2. Character defaults ───


def test_character_default_grade_1() -> None:
    c = Character(name="Test", race=Race.HUMAN)
    assert c.grade == 1


def test_character_default_class_warrior() -> None:
    c = Character(name="Test", race=Race.HUMAN)
    assert c.class_type == "warrior"


def test_character_explicit_grade_class_28hwa() -> None:
    """28화 본문 정합 — 6등급 마법사."""
    c = Character(
        name="아루아 레이븐",
        race=Race.HUMAN,
        grade=6,
        class_type=ClassType.MAGE.value,
    )
    assert c.grade == 6
    assert c.class_type == "mage"


# ─── 3. _create_recruit_character wire ───


def test_recruit_grade_1_5hwa() -> None:
    """5화 본문 정합 — 신참 길드 = warrior, grade=1."""
    rng = random.Random(42)
    c = _create_recruit_character("인간", 1, 0, rng)
    assert c.grade == 1


def test_recruit_class_warrior() -> None:
    rng = random.Random(42)
    c = _create_recruit_character("인간", 1, 0, rng)
    assert c.class_type == ClassType.WARRIOR.value


# ─── 4. gm_agent prompt rendering ───


def _base_ctx() -> dict[str, Any]:
    return {
        "work_name": "1층 시뮬",
        "work_genre": "판타지",
        "world_setting": "라스카니아",
        "world_tone": "차분",
        "world_rules": ["1층 어둠"],
        "main_character_name": "비요른",
        "main_character_role": "주인공",
        "supporting_characters": [],
        "current_location": "1층",
        "current_turn": 0,
    }


def _ctx_with_char(grade: int, cls: str) -> dict[str, Any]:
    ctx = _base_ctx()
    ctx["v2_characters"] = {
        "비요른": {
            "race": "바바리안",
            "hp": 100,
            "hp_max": 100,
            "level": 1,
            "experience": 0,
            "physical": 14,
            "strength": 16,
            "grade": grade,
            "class_type": cls,
        },
    }
    return ctx


def test_prompt_shows_grade_class_default() -> None:
    prompt = _gm_system_prompt(_ctx_with_char(1, "warrior"))
    assert "1등급 warrior" in prompt


def test_prompt_shows_grade_6_mage_28hwa() -> None:
    """28화 본문 정합 — '6등급 mage' prompt 본격 표시."""
    prompt = _gm_system_prompt(_ctx_with_char(6, "mage"))
    assert "6등급 mage" in prompt


def test_prompt_missing_keys_default_to_1_warrior() -> None:
    """ctx 본격 grade/class_type key 본격 X → default 1 warrior."""
    ctx = _base_ctx()
    ctx["v2_characters"] = {
        "비요른": {
            "race": "바바리안",
            "hp": 100,
            "hp_max": 100,
            "level": 1,
            "experience": 0,
            "physical": 14,
            "strength": 16,
        },
    }
    prompt = _gm_system_prompt(ctx)
    assert "1등급 warrior" in prompt


# ─── 5. sim_runner ctx serialize ───


def _make_party_world() -> tuple[
    dict[str, Character], WorldState, Location
]:
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=100,
            hp_max=100,
            grade=2,
            class_type="warrior",
        ),
    }
    world = WorldState(party_members=["비요른"])
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")
    return party, world, loc


def test_refresh_context_serializes_grade_class() -> None:
    party, world, loc = _make_party_world()
    ctx = _refresh_context(party, world, loc, _base_ctx(), [])
    assert ctx["v2_characters"]["비요른"]["grade"] == 2
    assert ctx["v2_characters"]["비요른"]["class_type"] == "warrior"


def test_refresh_context_default_grade_class() -> None:
    """Character default 본격 grade=1 / warrior serialize."""
    party = {
        "에르웬": Character(
            name="에르웬",
            race=Race.FAERIE,
            hp=90,
            hp_max=90,
        ),
    }
    world = WorldState(party_members=["에르웬"])
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")
    ctx = _refresh_context(party, world, loc, _base_ctx(), [])
    assert ctx["v2_characters"]["에르웬"]["grade"] == 1
    assert ctx["v2_characters"]["에르웬"]["class_type"] == "warrior"
