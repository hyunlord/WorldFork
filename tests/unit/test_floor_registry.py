"""Phase 8 R2 — FLOOR_REGISTRY + FloorDefinition rename 본격 unit 본격.

검증 본질:
- FLOOR_REGISTRY 본격 1층 등록
- get_current_floor_definition(location): default / fallback
- FloorDefinition 본격 모든 field (★ R2 신규 portal_to_next / portal_to_prev)
- Floor1Definition backward-compat alias
- 기존 get_floor1_definition() 본격 같은 instance
"""

from __future__ import annotations

from service.game.floors.floor1 import FLOOR1_DEFINITION, get_floor1_definition
from service.game.floors.registry import (
    FLOOR_REGISTRY,
    get_current_floor_definition,
)
from service.game.state_v2 import (
    Floor1Definition,
    FloorDefinition,
    Location,
    Realm,
)

# ─── 1. FLOOR_REGISTRY 본격 ───


def test_floor_registry_has_floor_1() -> None:
    assert 1 in FLOOR_REGISTRY
    assert FLOOR_REGISTRY[1] is FLOOR1_DEFINITION


# ─── 2. get_current_floor_definition ───


def test_get_current_floor_definition_floor_1() -> None:
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")
    floor_def = get_current_floor_definition(loc)
    assert floor_def is FLOOR1_DEFINITION


def test_get_current_floor_definition_floor_none_fallback() -> None:
    """Location.floor=None → default 1 (★ backward compat)."""
    loc = Location(realm=Realm.DUNGEON, floor=None, sub_area="진입점")
    floor_def = get_current_floor_definition(loc)
    assert floor_def is FLOOR1_DEFINITION


def test_get_current_floor_definition_unknown_floor_fallback() -> None:
    """미등록 floor → default 1 fallback (★ R3+R4 본격 본격 location.floor 보장 전).

    본 fallback은 backward-compat 본격 — 2층 enabler 본격 후속 commit 본격
    KeyError raise 본격 본격 본격 본격.
    """
    loc = Location(realm=Realm.DUNGEON, floor=99, sub_area="X")
    floor_def = get_current_floor_definition(loc)
    assert floor_def is FLOOR1_DEFINITION


# ─── 4. FloorDefinition 본격 fields ───


def test_floor_1_definition_basic_fields() -> None:
    fd = FLOOR1_DEFINITION
    assert fd.floor_number == 1
    assert fd.name == "수정동굴"
    assert fd.base_time_hours == 168
    assert fd.base_visibility_meters == 10
    assert fd.is_dark_default is True


def test_floor_1_definition_collections() -> None:
    fd = FLOOR1_DEFINITION
    # ★ Phase 8 C — 6 기본 + 4 portal = 10
    assert len(fd.sub_areas) == 10
    assert len(fd.rifts) == 4
    assert len(fd.monsters) == 8  # ★ F2 위치스램프 추가


def test_floor_1_definition_portal_to_next_4() -> None:
    """★ Phase 8 R2 — portal_to_next: 4 포탈 통로 (★ C commit)."""
    fd = FLOOR1_DEFINITION
    assert fd.portal_to_next == frozenset({
        "동쪽 포탈 통로",
        "서쪽 포탈 통로",
        "남쪽 포탈 통로",
        "북쪽 포탈 통로",
    })


def test_floor_1_definition_portal_to_prev_empty() -> None:
    """★ Phase 8 R2 — 1층은 최하단 → portal_to_prev empty."""
    fd = FLOOR1_DEFINITION
    assert fd.portal_to_prev == frozenset()


def test_floor_definition_default_portals_empty() -> None:
    """기본 instance (★ 본격 N층 본격 본격 fixture 본격) 본격 portal default empty."""
    fd = FloorDefinition()
    assert fd.portal_to_next == frozenset()
    assert fd.portal_to_prev == frozenset()


# ─── 5. Backward-compat alias ───


def test_floor1_definition_is_alias() -> None:
    """Floor1Definition = FloorDefinition (★ alias, 본격 caller 본격)."""
    assert Floor1Definition is FloorDefinition


def test_get_floor1_definition_returns_registry_floor_1() -> None:
    """기존 get_floor1_definition() 본격 같은 instance 본격 (★ R2 backward compat)."""
    assert get_floor1_definition() is FLOOR_REGISTRY[1]
    assert get_floor1_definition() is FLOOR1_DEFINITION
