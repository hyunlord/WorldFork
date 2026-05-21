"""Fix 2 검증 — evict_stale() + ACTIVE_TIMEOUT."""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from service.persistence.sqlite_store import SqliteStore
from service.sim.session_manager import ACTIVE_TIMEOUT, SessionManager


def _make_mgr(tmp_path: str) -> SessionManager:
    return SessionManager(SqliteStore(Path(tmp_path)))


def test_active_timeout_constant() -> None:
    assert ACTIVE_TIMEOUT == timedelta(hours=1)


def test_evict_stale_removes_stale_entry() -> None:
    async def run() -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = _make_mgr(f.name)
        s1 = await mgr.create_session()
        s2 = await mgr.create_session()
        sid1 = s1.session_id
        sid2 = s2.session_id

        mgr._last_seen[sid1] = datetime.utcnow() - timedelta(hours=2)

        evicted = await mgr.evict_stale()
        assert evicted == 1
        assert sid1 not in mgr._cache
        assert sid2 in mgr._cache

    asyncio.run(run())


def test_evict_stale_sqlite_survives() -> None:
    """evict 후 SQLite에는 남아 있어 reload 가능."""
    async def run() -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = _make_mgr(f.name)
        state = await mgr.create_session()
        sid = state.session_id

        mgr._last_seen[sid] = datetime.utcnow() - timedelta(hours=2)
        await mgr.evict_stale()
        assert sid not in mgr._cache

        reloaded = await mgr.get_session(sid)
        assert reloaded is not None
        assert reloaded.session_id == sid

    asyncio.run(run())


def test_evict_stale_zero_when_all_fresh() -> None:
    async def run() -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = _make_mgr(f.name)
        await mgr.create_session()
        await mgr.create_session()

        count = await mgr.evict_stale()
        assert count == 0

    asyncio.run(run())


def test_end_session_clears_last_seen() -> None:
    async def run() -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = _make_mgr(f.name)
        state = await mgr.create_session()
        sid = state.session_id
        assert sid in mgr._last_seen

        await mgr.end_session(sid)
        assert sid not in mgr._last_seen
        assert sid not in mgr._cache

    asyncio.run(run())
