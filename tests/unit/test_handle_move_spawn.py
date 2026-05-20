"""Phase D step 6c — _post_apply_spawn integration: city no spawn, dungeon spawn."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from service.canon.context import (
    clear_canon_facts,
    clear_spawn_table,
    set_canon_facts,
    set_spawn_table,
)
from service.canon.schema import CanonFacts, Location, Race
from service.canon.spawn import SpawnTable
from service.sim.session_manager import SessionState


def _session(
    location: str = "1층",
    turn_count: int = 10,
    last_spawn_turn: int = -10,
    encounters: list[dict[str, object]] | None = None,
) -> SessionState:
    return SessionState(
        session_id="test-sid",
        current_hp=100,
        max_hp=100,
        inventory=[],
        location=location,
        encounters=list(encounters or []),
        turn_count=turn_count,
        created_at=0.0,
        last_active=0.0,
        last_spawn_turn=last_spawn_turn,
    )


def _minimal_spawn_table() -> SpawnTable:
    facts = CanonFacts(
        races=[Race(name="고블린", description="지하 동굴에 서식한다")],
    )
    return SpawnTable(facts)


def _city_facts() -> CanonFacts:
    return CanonFacts(
        locations=[Location(name="라스카니아 광장", location_type="city")],
    )


def _dungeon_facts() -> CanonFacts:
    return CanonFacts(
        locations=[Location(name="마탑", location_type="dungeon")],
    )


# ─── _post_apply_spawn 직접 테스트 ───

@pytest.fixture(autouse=True)
def _cleanup_context():  # type: ignore[misc]
    yield
    clear_spawn_table()
    clear_canon_facts()


def test_post_apply_spawn_city_no_spawn() -> None:
    from service.api.v2_freeform_router import _post_apply_spawn

    set_spawn_table(_minimal_spawn_table())
    set_canon_facts(_city_facts())
    state = _session(location="라스카니아 광장", turn_count=10, last_spawn_turn=-10)

    _post_apply_spawn(state)

    assert state.encounters == []  # city → spawn X


def test_post_apply_spawn_dungeon_spawn_possible() -> None:
    from service.api.v2_freeform_router import _post_apply_spawn

    set_spawn_table(_minimal_spawn_table())
    set_canon_facts(_dungeon_facts())
    state = _session(location="마탑", turn_count=10, last_spawn_turn=-10)

    with patch("service.api.v2_freeform_router.trigger_spawn") as mock_trigger:
        mock_trigger.return_value = [{"name": "고블린", "hp": 25, "max_hp": 25,
                                      "attack": 6, "defense": 2, "hostile": True}]
        _post_apply_spawn(state)

    assert len(state.encounters) == 1
    assert state.last_spawn_turn == 10


def test_post_apply_spawn_already_encounters_no_op() -> None:
    from service.api.v2_freeform_router import _post_apply_spawn

    set_spawn_table(_minimal_spawn_table())
    existing = [{"name": "오크", "hp": 30}]
    state = _session(encounters=existing)

    with patch("service.api.v2_freeform_router.trigger_spawn") as mock_trigger:
        _post_apply_spawn(state)
        mock_trigger.assert_not_called()

    assert state.encounters == existing


def test_post_apply_spawn_no_table_no_crash() -> None:
    from service.api.v2_freeform_router import _post_apply_spawn

    clear_spawn_table()
    state = _session(location="마탑")
    _post_apply_spawn(state)  # 예외 없이 통과
    assert state.encounters == []


def test_post_apply_spawn_cooldown_blocks() -> None:
    from service.api.v2_freeform_router import _post_apply_spawn

    set_spawn_table(_minimal_spawn_table())
    set_canon_facts(_dungeon_facts())
    state = _session(location="마탑", turn_count=1, last_spawn_turn=0)

    with patch("service.api.v2_freeform_router.trigger_spawn") as mock_trigger:
        mock_trigger.return_value = []
        _post_apply_spawn(state)

    assert state.encounters == []
    assert state.last_spawn_turn == 0  # 변경 없음
