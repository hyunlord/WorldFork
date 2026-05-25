"""Phase E-4: NEW_EXPLORER 종족별 inventory 통합 테스트."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from service.api.app import create_app
from service.canon.races import Race
from service.canon.scenario import ScenarioMode
from service.persistence.sqlite_store import SqliteStore
from service.sim.session_manager import SessionManager


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _mgr(tmp_path: Path) -> SessionManager:
    return SessionManager(SqliteStore(tmp_path / "test.db"))


def test_new_explorer_barbarian_has_axe(tmp_path: Path) -> None:
    """NEW_EXPLORER 바바리안 → 도끼 (ep_0002 성인식 정합)."""
    mgr = _mgr(tmp_path)
    state = asyncio.run(mgr.create_session(
        race=Race.BARBARIAN,
        scenario_mode=ScenarioMode.NEW_EXPLORER,
    ))
    assert state.inventory == ["도끼"]


def test_new_explorer_human_has_sword(tmp_path: Path) -> None:
    """NEW_EXPLORER 인간 → 검 (wiki 오러 도검류 정합)."""
    mgr = _mgr(tmp_path)
    state = asyncio.run(mgr.create_session(
        race=Race.HUMAN,
        scenario_mode=ScenarioMode.NEW_EXPLORER,
    ))
    assert state.inventory == ["검"]


def test_new_explorer_dwarf_has_hammer(tmp_path: Path) -> None:
    """NEW_EXPLORER 드워프 → 망치 (wiki 망치 맹세 정합)."""
    mgr = _mgr(tmp_path)
    state = asyncio.run(mgr.create_session(
        race=Race.DWARF,
        scenario_mode=ScenarioMode.NEW_EXPLORER,
    ))
    assert state.inventory == ["망치"]


def test_new_explorer_beastkin_empty(tmp_path: Path) -> None:
    """NEW_EXPLORER 수인 → 빈 inventory (발톱 비무장 traits 정합)."""
    mgr = _mgr(tmp_path)
    state = asyncio.run(mgr.create_session(
        race=Race.BEASTKIN,
        scenario_mode=ScenarioMode.NEW_EXPLORER,
    ))
    assert state.inventory == []


def test_new_explorer_fairy_has_dagger(tmp_path: Path) -> None:
    """NEW_EXPLORER 요정 → 단검 (정령술 정합)."""
    mgr = _mgr(tmp_path)
    state = asyncio.run(mgr.create_session(
        race=Race.FAIRY,
        scenario_mode=ScenarioMode.NEW_EXPLORER,
    ))
    assert state.inventory == ["단검"]


def test_bjorn_still_uses_shield(tmp_path: Path) -> None:
    """BJORN → 방패 유지 (commit 3 backward-compat)."""
    mgr = _mgr(tmp_path)
    state = asyncio.run(mgr.create_session(scenario_mode=ScenarioMode.BJORN))
    assert state.inventory == ["방패"]
    assert "도끼" not in state.inventory


def test_new_explorer_barbarian_shield_not_default(tmp_path: Path) -> None:
    """NEW_EXPLORER 바바리안 — 방패 X (방패는 BJORN 전용)."""
    mgr = _mgr(tmp_path)
    state = asyncio.run(mgr.create_session(
        race=Race.BARBARIAN,
        scenario_mode=ScenarioMode.NEW_EXPLORER,
    ))
    assert "방패" not in state.inventory


def test_character_endpoint_new_explorer_inventory(client: TestClient) -> None:
    """POST /api/v2/character/create NEW_EXPLORER → 종족별 inventory."""
    for race_str, expected in [
        ("barbarian", ["도끼"]),
        ("human", ["검"]),
        ("dwarf", ["망치"]),
        ("beastkin", []),
        ("fairy", ["단검"]),
    ]:
        resp = client.post(
            "/api/v2/character/create",
            json={"scenario_mode": "new_explorer", "race": race_str},
        )
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        state_resp = client.get(f"/api/v2/session/{session_id}/state")
        assert state_resp.status_code == 200
        assert state_resp.json()["inventory"] == expected, (
            f"race={race_str}: expected {expected}, got {state_resp.json()['inventory']}"
        )
