"""일반 turn time_elapsed 누적 단위 테스트 — audit-step168h-followup."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from service.persistence.sqlite_store import SqliteStore
from service.sim.action_context import ActionResult
from service.sim.session_manager import SessionManager


def _make_manager() -> SessionManager:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = SqliteStore(Path(tmp.name))
    return SessionManager(store)


def _result(time_advance: int = 0) -> ActionResult:
    return ActionResult(narrative="테스트", hp_change=0, time_advance=time_advance)


@pytest.mark.asyncio
async def test_apply_result_adds_60_for_1h() -> None:
    """1h action → time_elapsed +60."""
    mgr = _make_manager()
    state = await mgr.create_session()
    assert state.time_elapsed == 0

    updated = await mgr.apply_result(state.session_id, _result(1), "이동", "intent")
    assert updated.time_elapsed == 60


@pytest.mark.asyncio
async def test_apply_result_adds_0_for_zero_advance() -> None:
    """time_advance=0 → time_elapsed 변화 없음."""
    mgr = _make_manager()
    state = await mgr.create_session()

    updated = await mgr.apply_result(state.session_id, _result(0), "대기", "intent")
    assert updated.time_elapsed == 0


@pytest.mark.asyncio
async def test_apply_result_2h_adds_120() -> None:
    """2h action → time_elapsed +120."""
    mgr = _make_manager()
    state = await mgr.create_session()

    updated = await mgr.apply_result(state.session_id, _result(2), "수색", "intent")
    assert updated.time_elapsed == 120


@pytest.mark.asyncio
async def test_apply_result_3h_adds_180() -> None:
    """3h action → time_elapsed +180."""
    mgr = _make_manager()
    state = await mgr.create_session()

    updated = await mgr.apply_result(state.session_id, _result(3), "탐색", "intent")
    assert updated.time_elapsed == 180


@pytest.mark.asyncio
async def test_force_return_only_1440_not_action_time() -> None:
    """force_return turn: apply_result +60 후 _force_return_to_city(undo_min=60) → total=1440."""
    from service.api.v2_freeform_router import _force_return_to_city

    mgr = _make_manager()
    state = await mgr.create_session()

    state = await mgr.apply_result(state.session_id, _result(1), "던전 탐색", "intent")
    assert state.time_elapsed == 60

    _force_return_to_city(state, undo_min=60)
    assert state.time_elapsed == 1440


@pytest.mark.asyncio
async def test_multiple_turns_accumulate() -> None:
    """3턴 × 1h = 180min."""
    mgr = _make_manager()
    state = await mgr.create_session()

    for i in range(3):
        state = await mgr.apply_result(state.session_id, _result(1), f"행동{i}", "intent")

    assert state.time_elapsed == 180
