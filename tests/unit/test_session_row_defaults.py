"""Fix 1 검증 — SessionRow.last_spawn_turn default -10 (SessionState 정합)."""

from service.persistence.sqlite_store import SessionRow
from service.sim.session_manager import SessionState


def test_session_row_last_spawn_turn_default() -> None:
    row = SessionRow(
        session_id="x", created_at=0.0, last_active=0.0,
        current_hp=100, max_hp=100, inventory=[], location="1층", turn_count=0,
    )
    assert row.last_spawn_turn == -10


def test_session_state_row_last_spawn_turn_match() -> None:
    import dataclasses
    ss_defaults = {f.name: f.default for f in dataclasses.fields(SessionState)}
    sr_defaults = {f.name: f.default for f in dataclasses.fields(SessionRow)}
    assert ss_defaults["last_spawn_turn"] == sr_defaults["last_spawn_turn"] == -10
