"""time_elapsed 누적 E2E — apply_result 다중 호출 후 DB roundtrip 검증."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from service.persistence.sqlite_store import SqliteStore
from service.sim.action_context import ActionResult
from service.sim.session_manager import SessionManager


@pytest.mark.asyncio
async def test_time_elapsed_accumulates_and_persists() -> None:
    """apply_result 3회(1h+2h+0h = 180min) + reload 후 time_elapsed 유지."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        store = SqliteStore(Path(f.name))
    mgr = SessionManager(store)

    state = await mgr.create_session()
    sid = state.session_id
    assert state.time_elapsed == 0

    for advance in [1, 2, 0]:
        r = ActionResult(narrative="행동", hp_change=0, time_advance=advance)
        state = await mgr.apply_result(sid, r, "이동", "intent")

    assert state.time_elapsed == 180

    # 별도 매니저로 DB reload
    mgr2 = SessionManager(store)
    reloaded = await mgr2.get_session(sid)
    assert reloaded is not None
    assert reloaded.time_elapsed == 180
