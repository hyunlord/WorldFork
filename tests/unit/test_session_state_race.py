"""SessionState + SessionRow race field 검증 (phase-e-1)."""

from __future__ import annotations

from dataclasses import fields as dc_fields


def test_session_state_race_default_barbarian() -> None:
    """SessionState.race default == 'barbarian' (★ backward-compat)."""
    from service.sim.session_manager import SessionState
    state = SessionState(
        session_id="test-id",
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층 입구",
        encounters=[],
        turn_count=0,
        created_at=0.0,
        last_active=0.0,
    )
    assert state.race == "barbarian"


def test_session_state_race_field_exists() -> None:
    """SessionState에 race field 존재."""
    from service.sim.session_manager import SessionState
    field_names = {f.name for f in dc_fields(SessionState)}
    assert "race" in field_names


def test_session_row_race_default() -> None:
    """SessionRow.race default == 'barbarian'."""
    from service.persistence.sqlite_store import SessionRow
    row = SessionRow(
        session_id="test",
        created_at=0.0,
        last_active=0.0,
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층 입구",
        turn_count=0,
    )
    assert row.race == "barbarian"


def test_session_row_race_field_exists() -> None:
    """SessionRow에 race field 존재."""
    from service.persistence.sqlite_store import SessionRow
    field_names = {f.name for f in dc_fields(SessionRow)}
    assert "race" in field_names


def test_session_state_race_can_be_set() -> None:
    """SessionState.race 다른 종족으로 설정 가능."""
    from service.sim.session_manager import SessionState
    state = SessionState(
        session_id="test-id",
        current_hp=80,
        max_hp=80,
        inventory=[],
        location="1층 입구",
        encounters=[],
        turn_count=0,
        created_at=0.0,
        last_active=0.0,
        race="fairy",
    )
    assert state.race == "fairy"
