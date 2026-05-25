"""Phase E-3: create_session inventory 통합 테스트."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from service.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_character_create_bjorn_returns_shield(client: TestClient) -> None:
    """POST /api/v2/character/create BJORN → inventory 에 방패."""
    resp = client.post("/api/v2/character/create", json={"scenario_mode": "bjorn"})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    state_resp = client.get(f"/api/v2/session/{session_id}/state")
    assert state_resp.status_code == 200
    assert "방패" in state_resp.json()["inventory"]


def test_character_create_bjorn_inventory_explicit_override(client: TestClient) -> None:
    """명시적 inventory 전달 시 override 동작."""
    resp = client.post(
        "/api/v2/character/create",
        json={"scenario_mode": "bjorn", "inventory": ["도끼"]},
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    state_resp = client.get(f"/api/v2/session/{session_id}/state")
    assert state_resp.json()["inventory"] == ["도끼"]


def test_character_create_new_explorer_inventory_empty(client: TestClient) -> None:
    """NEW_EXPLORER 시작 inventory 비어 있음 (commit 4 전)."""
    resp = client.post(
        "/api/v2/character/create",
        json={"scenario_mode": "new_explorer"},
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    state_resp = client.get(f"/api/v2/session/{session_id}/state")
    assert state_resp.json()["inventory"] == []
