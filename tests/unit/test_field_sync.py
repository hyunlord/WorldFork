"""SessionState ↔ SessionRow ↔ SQLite ↔ save/load 4곳 동기화 자동 검증.

commit별 신규 필드 추가 시 silent regression 방지.
"""

from __future__ import annotations

import asyncio
import dataclasses
import sqlite3
import tempfile
from pathlib import Path

from service.persistence.sqlite_store import SessionRow, SqliteStore
from service.sim.session_manager import SessionManager, SessionState

# in-memory only — DB 비영속 허용 목록
_EXEMPT_FROM_ROW = {"encounters"}


def test_session_state_fields_in_session_row() -> None:
    """SessionState의 모든 field가 SessionRow에 존재."""
    state_fields = {f.name for f in dataclasses.fields(SessionState)}
    row_fields = {f.name for f in dataclasses.fields(SessionRow)}
    missing = state_fields - row_fields - _EXEMPT_FROM_ROW
    assert not missing, (
        f"SessionState fields missing in SessionRow: {missing}. "
        "Add to SessionRow + _migrate() ALTER TABLE."
    )


def test_session_row_columns_in_db() -> None:
    """SessionRow의 모든 field가 sessions table column에 존재."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        store = SqliteStore(Path(f.name))
    conn = sqlite3.connect(f.name)
    db_cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    conn.close()

    row_fields = {f.name for f in dataclasses.fields(SessionRow)}
    missing = row_fields - db_cols
    assert not missing, (
        f"SessionRow fields missing in DB schema: {missing}. "
        "Add ALTER TABLE in _migrate()."
    )
    _ = store  # init이 _migrate 수행했음을 명시


def test_session_row_defaults_match_session_state() -> None:
    """SessionRow scalar default이 SessionState scalar default과 정합."""
    missing_sentinel = dataclasses.MISSING

    mismatches: list[tuple[str, object, object]] = []
    ss_by_name = {f.name: f for f in dataclasses.fields(SessionState)}
    sr_by_name = {f.name: f for f in dataclasses.fields(SessionRow)}

    for name, ss_f in ss_by_name.items():
        if name not in sr_by_name:
            continue
        sr_f = sr_by_name[name]
        ss_d = ss_f.default
        sr_d = sr_f.default
        # factory defaults (list/dict) 제외 — scalar만 비교
        if ss_d is missing_sentinel or sr_d is missing_sentinel:
            continue
        if ss_d != sr_d:
            mismatches.append((name, ss_d, sr_d))

    assert not mismatches, (
        f"SessionRow defaults mismatch SessionState: {mismatches}"
    )


def test_save_load_roundtrip_all_fields() -> None:
    """save_session → load_session 후 모든 field 보존."""
    async def run() -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = SessionManager(SqliteStore(Path(f.name)))

        state = await mgr.create_session()
        sid = state.session_id

        state.current_hp = 77
        state.player_level = 9
        state.stone_balance = 9999
        state.hours_in_dungeon = 72.5
        state.rift_id = "bloody_castle"
        state.rift_sub_area = "boss_room"
        state.rift_is_variant = True
        state.floor_number = 3
        state.soul_power = 88
        state.last_spawn_turn = 42
        await mgr.save_state(state)

        # cache 비우고 SQLite reload
        mgr._cache.clear()
        mgr._last_seen.clear()

        r = await mgr.get_session(sid)
        assert r is not None
        assert r.current_hp == 77
        assert r.player_level == 9
        assert r.stone_balance == 9999
        assert r.hours_in_dungeon == 72.5
        assert r.rift_id == "bloody_castle"
        assert r.rift_sub_area == "boss_room"
        assert r.rift_is_variant is True
        assert r.floor_number == 3
        assert r.soul_power == 88
        assert r.last_spawn_turn == 42

    asyncio.run(run())
