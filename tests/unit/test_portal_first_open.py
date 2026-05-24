"""Phase D step 6d-followup — 최초 포탈 개방 EXP +2 (ep_0022)."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from service.persistence.sqlite_store import SessionRow, SqliteStore
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_exit_rift
from service.sim.session_manager import SessionManager, SessionState


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def _ctx(portal_first_opened: bool = False) -> ActionContext:
    return ActionContext(
        current_hp=80,
        max_hp=100,
        inventory=[],
        location="균열 내부 (균열 내부)",
        portal_first_opened=portal_first_opened,
    )


# ── handle_exit_rift ──


def test_first_exit_grants_xp_2() -> None:
    result = run(handle_exit_rift(_ctx(portal_first_opened=False)))
    assert result.xp_gain == 2


def test_first_exit_sets_portal_flag() -> None:
    result = run(handle_exit_rift(_ctx(portal_first_opened=False)))
    assert result.portal_first_opened_set is True


def test_first_exit_narrative_contains_portal_message() -> None:
    result = run(handle_exit_rift(_ctx(portal_first_opened=False)))
    assert "최초로 포탈을 개방했습니다" in result.narrative
    assert "EXP +2" in result.narrative


def test_second_exit_no_xp() -> None:
    result = run(handle_exit_rift(_ctx(portal_first_opened=True)))
    assert result.xp_gain == 0


def test_second_exit_no_portal_flag() -> None:
    result = run(handle_exit_rift(_ctx(portal_first_opened=True)))
    assert result.portal_first_opened_set is False


def test_second_exit_no_portal_message() -> None:
    result = run(handle_exit_rift(_ctx(portal_first_opened=True)))
    assert "최초로 포탈" not in result.narrative


# ── SessionState / SessionRow defaults ──


def test_session_state_portal_default_false() -> None:
    state = SessionState(
        session_id="x",
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층",
        encounters=[],
        turn_count=0,
        created_at=0.0,
        last_active=0.0,
    )
    assert state.portal_first_opened is False


def test_session_row_portal_default_false() -> None:
    row = SessionRow(
        session_id="x",
        created_at=0.0,
        last_active=0.0,
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층",
        turn_count=0,
    )
    assert row.portal_first_opened is False


# ── save/load roundtrip ──


def test_save_load_portal_flag() -> None:
    async def run_async() -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = SessionManager(SqliteStore(Path(f.name)))
        state = await mgr.create_session()
        assert state.portal_first_opened is False

        state.portal_first_opened = True
        await mgr.save_state(state)

        mgr._cache.clear()
        mgr._last_seen.clear()

        r = await mgr.get_session(state.session_id)
        assert r is not None
        assert r.portal_first_opened is True

    asyncio.run(run_async())
