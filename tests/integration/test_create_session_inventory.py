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


def test_character_create_new_explorer_human_default(client: TestClient) -> None:
    """NEW_EXPLORER race 미지정 → HUMAN default → 검 (commit 4 정합)."""
    resp = client.post(
        "/api/v2/character/create",
        json={"scenario_mode": "new_explorer"},
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    state_resp = client.get(f"/api/v2/session/{session_id}/state")
    assert state_resp.json()["inventory"] == ["검"]


def test_character_create_new_explorer_beastkin_empty(client: TestClient) -> None:
    """NEW_EXPLORER 수인 → 빈 inventory (발톱 비무장 정합)."""
    resp = client.post(
        "/api/v2/character/create",
        json={"scenario_mode": "new_explorer", "race": "beastkin"},
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    state_resp = client.get(f"/api/v2/session/{session_id}/state")
    assert state_resp.json()["inventory"] == []
