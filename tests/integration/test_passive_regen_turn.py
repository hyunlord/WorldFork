"""passive HP 재생 turn cycle 연결 — apply_result 매 턴 회복 (★ case A e2e)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from service.persistence.sqlite_store import SqliteStore
from service.sim.action_context import ActionResult
from service.sim.session_manager import SessionManager


def _make_manager(tmp_path: Path) -> SessionManager:
    return SessionManager(SqliteStore(tmp_path / "regen.db"))


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def _absorb_regen_essence(mgr: SessionManager, sid: str, regen: int) -> None:
    """재생 정수 흡수 (regen_per_turn 부여)."""
    absorb = ActionResult(
        narrative="정수를 흡수했다.",
        essence_slot_add={"essence_name": "뱀파이어 정수", "regen_per_turn": regen},
    )
    run(mgr.apply_result(sid, absorb, "흡수", "absorb"))


def test_passive_regen_per_turn(tmp_path: Path) -> None:
    """★ case A — 재생 정수 흡수 후 매 턴 HP 재생."""
    mgr = _make_manager(tmp_path)
    state = run(mgr.create_session(current_hp=50, max_hp=100))
    _absorb_regen_essence(mgr, state.session_id, 2)
    # 액션 1턴 진행 (hp_change 없음) → 자연 재생 2
    act = ActionResult(narrative="복도를 탐색했다.", time_advance=1)
    updated = run(mgr.apply_result(state.session_id, act, "탐색", "explore"))
    assert updated.current_hp == 52


def test_regen_capped_at_max_hp(tmp_path: Path) -> None:
    """★ HP 재생은 max_hp 상한."""
    mgr = _make_manager(tmp_path)
    state = run(mgr.create_session(current_hp=99, max_hp=100))
    _absorb_regen_essence(mgr, state.session_id, 3)
    act = ActionResult(narrative="탐색.", time_advance=1)
    updated = run(mgr.apply_result(state.session_id, act, "탐색", "explore"))
    assert updated.current_hp == 100  # 99+3=102 아닌 상한 100


def test_no_regen_when_dead(tmp_path: Path) -> None:
    """★ 사망(HP 0) 시 재생 X — 부활 방지."""
    mgr = _make_manager(tmp_path)
    state = run(mgr.create_session(current_hp=10, max_hp=100))
    _absorb_regen_essence(mgr, state.session_id, 3)
    # 치명타로 사망
    fatal = ActionResult(narrative="치명상.", hp_change=-50)
    updated = run(mgr.apply_result(state.session_id, fatal, "전투", "intent"))
    assert updated.current_hp == 0  # 재생으로 살아나지 않음


def test_no_regen_without_essence(tmp_path: Path) -> None:
    """재생 정수 없으면 HP 불변 (회귀)."""
    mgr = _make_manager(tmp_path)
    state = run(mgr.create_session(current_hp=50, max_hp=100))
    act = ActionResult(narrative="탐색.", time_advance=1)
    updated = run(mgr.apply_result(state.session_id, act, "탐색", "explore"))
    assert updated.current_hp == 50


def test_regen_persists_across_reload(tmp_path: Path) -> None:
    """재생 정수가 SQLite 영속 후에도 재생 (regen_per_turn 직렬화)."""
    db = tmp_path / "persist.db"
    mgr1 = SessionManager(SqliteStore(db))
    state = run(mgr1.create_session(current_hp=40, max_hp=100))
    _absorb_regen_essence(mgr1, state.session_id, 2)
    # 새 매니저로 reload
    mgr2 = SessionManager(SqliteStore(db))
    act = ActionResult(narrative="탐색.", time_advance=1)
    updated = run(mgr2.apply_result(state.session_id, act, "탐색", "explore"))
    assert updated.current_hp == 42
