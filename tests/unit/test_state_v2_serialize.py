"""state_v2_serialize 단위 테스트 (★ Phase 7a)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import IntEnum

from service.game.state_v2 import (
    Character,
    EssenceColor,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.state_v2_serialize import (
    game_state_v2_to_dict,
    state_to_dict,
)

# ─── primitives ───


def test_state_to_dict_primitive_passthrough() -> None:
    assert state_to_dict(None) is None
    assert state_to_dict("hello") == "hello"
    assert state_to_dict(42) == 42
    assert state_to_dict(3.14) == 3.14
    assert state_to_dict(True) is True


# ─── Enum ───


def test_state_to_dict_strenum() -> None:
    """★ StrEnum 본격 .value 본격."""
    assert state_to_dict(Race.BARBARIAN) == "바바리안"
    assert state_to_dict(Realm.DUNGEON) == "미궁"
    assert state_to_dict(EssenceColor.RED) == "빨강"


def test_state_to_dict_intenum() -> None:
    """★ IntEnum 본격 .value 본격 int."""

    class Grade(IntEnum):
        LOW = 1
        HIGH = 9

    assert state_to_dict(Grade.LOW) == 1
    assert state_to_dict(Grade.HIGH) == 9


# ─── list / dict ───


def test_state_to_dict_list_of_enum() -> None:
    result = state_to_dict([Race.BARBARIAN, Race.FAERIE])
    assert result == ["바바리안", "요정"]


def test_state_to_dict_dict_with_enum() -> None:
    result = state_to_dict({"race": Race.BARBARIAN, "hp": 150})
    assert result == {"race": "바바리안", "hp": 150}


# ─── dataclass ───


def test_state_to_dict_character() -> None:
    """★ Character (★ frozen dataclass X — slots X 본격) 본격 본격."""
    c = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        physical=14,
        is_player=True,
    )
    result = state_to_dict(c)
    assert isinstance(result, dict)
    assert result["name"] == "비요른"
    assert result["race"] == "바바리안"
    assert result["hp"] == 150
    assert result["physical"] == 14
    assert result["is_player"] is True


def test_state_to_dict_location() -> None:
    """★ Location 본격 — Enum Realm 본격 변환 본격."""
    loc = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="진입점",
        rift_id=None,
        has_light=False,
    )
    result = state_to_dict(loc)
    assert isinstance(result, dict)
    assert result["realm"] == "미궁"
    assert result["floor"] == 1
    assert result["sub_area"] == "진입점"
    assert result["rift_id"] is None
    assert result["has_light"] is False


def test_state_to_dict_world_state() -> None:
    """★ WorldState 본격 — list field 본격."""
    w = WorldState(
        active_rifts=["bloody_castle"],
        party_members=["비요른", "에르웬"],
    )
    result = state_to_dict(w)
    assert isinstance(result, dict)
    assert result["active_rifts"] == ["bloody_castle"]
    assert result["party_members"] == ["비요른", "에르웬"]


# ─── nested ───


def test_state_to_dict_nested_dataclass() -> None:
    """★ nested dataclass 본격 본격."""

    @dataclass
    class Inner:
        color: EssenceColor
        amount: int

    @dataclass
    class Outer:
        name: str
        inner: Inner
        items: list[Inner]

    o = Outer(
        name="test",
        inner=Inner(color=EssenceColor.BLUE, amount=3),
        items=[Inner(color=EssenceColor.GREEN, amount=1)],
    )
    result = state_to_dict(o)
    assert isinstance(result, dict)
    assert result["name"] == "test"
    assert result["inner"] == {"color": "파랑", "amount": 3}
    assert result["items"] == [{"color": "초록", "amount": 1}]


def test_state_to_dict_json_serializable() -> None:
    """★ 본격 결과 본격 json.dumps 본격 본격."""
    c = Character(name="비요른", race=Race.BARBARIAN, hp=150, hp_max=150)
    result = state_to_dict(c)
    # 본격 json.dumps 본격 본격 본격
    serialized = json.dumps(result, ensure_ascii=False)
    assert isinstance(serialized, str)
    assert "비요른" in serialized


# ─── game_state_v2_to_dict ───


def test_game_state_v2_to_dict_structure() -> None:
    """★ (party + world + location) 본격 본격 dict 본격 본격."""
    party = {
        "비요른": Character(name="비요른", race=Race.BARBARIAN, hp=150, hp_max=150),
    }
    world = WorldState(party_members=["비요른"])
    location = Location(realm=Realm.DUNGEON, floor=1)

    result = game_state_v2_to_dict(party, world, location)
    assert "characters" in result
    assert "world" in result
    assert "location" in result
    # 본격 본격
    assert "비요른" in result["characters"]
    assert isinstance(result["characters"]["비요른"], dict)
    assert result["world"]["party_members"] == ["비요른"]
    assert result["location"]["realm"] == "미궁"


def test_game_state_v2_to_dict_json_roundtrip() -> None:
    """★ 본격 결과 본격 json.dumps 본격 본격 (★ 본격 frontend serialization)."""
    party = {
        "비요른": Character(name="비요른", race=Race.BARBARIAN, hp=150, hp_max=150),
        "에르웬": Character(name="에르웬", race=Race.FAERIE, hp=90, hp_max=90),
    }
    world = WorldState(
        party_members=["비요른", "에르웬"],
        active_rifts=["bloody_castle"],
    )
    location = Location(
        realm=Realm.RIFT,
        floor=1,
        sub_area="균열 내부",
        rift_id="bloody_castle",
    )

    result = game_state_v2_to_dict(party, world, location)
    serialized = json.dumps(result, ensure_ascii=False)
    parsed = json.loads(serialized)
    assert parsed["location"]["realm"] == "균열"
    assert parsed["location"]["rift_id"] == "bloody_castle"
    assert parsed["world"]["active_rifts"] == ["bloody_castle"]


# ─── Phase 7j: PlayerActionType 정합 ───


def test_player_action_type_count_15() -> None:
    """PlayerActionType 본격 15개 (★ Phase 7j 13 + Phase 8 C/R3 2개 추가).

    Phase 8 C / R3 추가:
    - ENTER_NEXT_FLOOR (★ generic, R3 rename from ENTER_FLOOR_TWO)
    - EXIT_TO_PREV_FLOOR (★ generic, R3 rename from EXIT_TO_FLOOR_ONE)
    """
    from service.sim.types import PlayerActionType

    assert len(list(PlayerActionType)) == 15
