"""audit-step168h fix — time_elapsed field 추가 + force return +1440min."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from service.persistence.sqlite_store import SessionRow, SqliteStore
from service.sim.session_manager import SessionState


def test_session_state_time_elapsed_default() -> None:
    state = SessionState(
        session_id="t1",
        current_hp=100, max_hp=100,
        inventory=[], location="마을",
        encounters=[], turn_count=0,
        created_at=0.0, last_active=0.0,
    )
    assert state.time_elapsed == 0


def test_session_row_time_elapsed_default() -> None:
    row = SessionRow(
        session_id="t1",
        created_at=0.0, last_active=0.0,
        current_hp=100, max_hp=100,
        inventory=[], location="마을",
        turn_count=0,
    )
    assert row.time_elapsed == 0


def test_force_return_advances_time_1440min() -> None:
    """force return 시 time_elapsed += 1440 (24h * 60)."""
    from service.api.v2_freeform_router import _force_return_to_city
    from service.sim.dungeon_clock import RETURN_TIME_ADVANCE_HOURS

    state = SessionState(
        session_id="t2",
        current_hp=100, max_hp=100,
        inventory=["방패"], location="1층 입구",
        encounters=[{"name": "고블린"}],
        turn_count=5,
        created_at=0.0, last_active=0.0,
        floor_number=1,
        hours_in_dungeon=168.0,
        status_effects=[{"type": "poison"}],
        time_elapsed=200,
        player_level=3,
        player_xp=30,
        absorbed_essences=[{"essence_name": "고블린"}],
        stone_balance=500,
    )

    _force_return_to_city(state)

    expected_advance = int(RETURN_TIME_ADVANCE_HOURS * 60)  # 1440
    assert state.time_elapsed == 200 + expected_advance


def test_force_return_resets_dungeon_state() -> None:
    """force return 시 dungeon state 초기화 확인."""
    from service.api.v2_freeform_router import _force_return_to_city

    state = SessionState(
        session_id="t3",
        current_hp=100, max_hp=100,
        inventory=["방패"], location="1층 입구",
        encounters=[{"name": "고블린"}],
        turn_count=5,
        created_at=0.0, last_active=0.0,
        floor_number=1,
        hours_in_dungeon=168.0,
        status_effects=[{"type": "poison"}],
        time_elapsed=0,
        player_level=3,
        player_xp=30,
    )

    _force_return_to_city(state)

    assert state.floor_number == 0
    assert state.location == "라프도니아 · 차원광장"
    assert state.encounters == []
    assert state.status_effects == []
    assert state.hours_in_dungeon == 0.0


def test_force_return_preserves_inventory_level_xp() -> None:
    """force return 시 inventory / level / xp / 정수 유지."""
    from service.api.v2_freeform_router import _force_return_to_city

    state = SessionState(
        session_id="t4",
        current_hp=100, max_hp=100,
        inventory=["방패", "마석"],
        location="1층 입구",
        encounters=[],
        turn_count=5,
        created_at=0.0, last_active=0.0,
        floor_number=1,
        hours_in_dungeon=168.0,
        status_effects=[],
        time_elapsed=0,
        player_level=3,
        player_xp=30,
        absorbed_essences=[{"essence_name": "고블린"}],
        stone_balance=500,
    )

    _force_return_to_city(state)

    assert state.inventory == ["방패", "마석"]
    assert state.player_level == 3
    assert state.player_xp == 30
    assert state.absorbed_essences == [{"essence_name": "고블린"}]
    assert state.stone_balance == 500


def test_time_elapsed_persists_through_db_roundtrip() -> None:
    """time_elapsed가 SQLite save/load roundtrip 후 유지."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        store = SqliteStore(Path(f.name))

    row = SessionRow(
        session_id="rt1",
        created_at=0.0, last_active=0.0,
        current_hp=100, max_hp=100,
        inventory=[], location="마을",
        turn_count=0,
        time_elapsed=1640,
    )
    store.save_session(row)
    loaded = store.load_session("rt1")
    assert loaded is not None
    assert loaded.time_elapsed == 1640


@pytest.mark.asyncio
async def test_session_manager_time_elapsed_roundtrip() -> None:
    """SessionManager create → force_return → save → load 전체 cycle."""
    from service.api.v2_freeform_router import _force_return_to_city
    from service.sim.session_manager import SessionManager

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        store = SqliteStore(Path(f.name))
    mgr = SessionManager(store)

    state = await mgr.create_session()
    assert state.time_elapsed == 0

    state.floor_number = 1
    state.hours_in_dungeon = 168.0
    _force_return_to_city(state)
    assert state.time_elapsed == 1440

    await mgr.save_state(state)
    reloaded = await mgr.get_session(state.session_id)
    assert reloaded is not None
    assert reloaded.time_elapsed == 1440
