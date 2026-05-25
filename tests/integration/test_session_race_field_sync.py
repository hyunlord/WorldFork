"""race field — SessionState / SessionRow / schema.sql / Response 정합 검증 (phase-e-1)."""

from __future__ import annotations

from dataclasses import fields as dc_fields


def test_race_field_in_state_and_row() -> None:
    """race field가 SessionState + SessionRow 양쪽에 존재."""
    from service.persistence.sqlite_store import SessionRow
    from service.sim.session_manager import SessionState

    state_fields = {f.name for f in dc_fields(SessionState)}
    row_fields = {f.name for f in dc_fields(SessionRow)}

    assert "race" in state_fields, "SessionState에 race field 없음"
    assert "race" in row_fields, "SessionRow에 race field 없음"


def test_race_default_consistent() -> None:
    """SessionState + SessionRow default 모두 'barbarian'."""
    from service.persistence.sqlite_store import SessionRow
    from service.sim.session_manager import SessionState

    state_default = next(
        f.default for f in dc_fields(SessionState) if f.name == "race"
    )
    row_default = next(
        f.default for f in dc_fields(SessionRow) if f.name == "race"
    )
    assert state_default == "barbarian"
    assert row_default == "barbarian"
    assert state_default == row_default


def test_session_state_response_race_field() -> None:
    """SessionStateResponse에 race field 존재."""
    from service.api.v2_session_router import SessionStateResponse
    assert "race" in SessionStateResponse.model_fields


def test_schema_sql_race_column() -> None:
    """schema.sql에 race column 정의."""
    from pathlib import Path
    schema = Path("service/persistence/schema.sql").read_text(encoding="utf-8")
    assert "race" in schema
    assert "barbarian" in schema
