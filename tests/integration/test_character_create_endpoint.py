"""POST /api/v2/character/create endpoint 통합 테스트 (phase-e-2)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from service.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_character_create_bjorn_default(client: TestClient) -> None:
    """BJORN 기본 — race=barbarian, HP=120."""
    resp = client.post("/api/v2/character/create", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["race"] == "barbarian"
    assert data["hp"] == 120
    assert data["max_hp"] == 120
    assert data["scenario_mode"] == "bjorn"
    assert "session_id" in data
    assert "라스카니아" in data["starting_location"]


def test_character_create_bjorn_ignores_race(client: TestClient) -> None:
    """BJORN — race 지정해도 barbarian 고정."""
    resp = client.post("/api/v2/character/create", json={"scenario_mode": "bjorn", "race": "fairy"})
    assert resp.status_code == 200
    assert resp.json()["race"] == "barbarian"


def test_character_create_new_explorer_fairy(client: TestClient) -> None:
    """NEW_EXPLORER + 요정 — HP=80, 슬롯=2, 영혼력=20."""
    resp = client.post(
        "/api/v2/character/create",
        json={"scenario_mode": "new_explorer", "race": "fairy"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["race"] == "fairy"
    assert data["hp"] == 80
    assert data["max_hp"] == 80
    assert data["soul_power"] == 20
    assert data["max_essences"] == 2
    assert data["scenario_mode"] == "new_explorer"


def test_character_create_new_explorer_no_race_default_human(client: TestClient) -> None:
    """NEW_EXPLORER race 미지정 → human (HP=100)."""
    resp = client.post("/api/v2/character/create", json={"scenario_mode": "new_explorer"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["race"] == "human"
    assert data["hp"] == 100


def test_character_create_invalid_scenario(client: TestClient) -> None:
    """알 수 없는 scenario_mode → 400."""
    resp = client.post("/api/v2/character/create", json={"scenario_mode": "invalid_mode"})
    assert resp.status_code == 400


def test_character_create_race_traits_returned(client: TestClient) -> None:
    """race_traits 필드 비어있지 않음."""
    resp = client.post("/api/v2/character/create", json={})
    assert resp.status_code == 200
    assert len(resp.json()["race_traits"]) > 0


def test_session_start_backward_compat(client: TestClient) -> None:
    """POST /api/v2/session/start — 여전히 200 반환 (★ backward-compat)."""
    resp = client.post("/api/v2/session/start", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data


def test_scenario_mode_in_session_state(client: TestClient) -> None:
    """GET /{session_id}/state — scenario_mode 필드 포함."""
    create_resp = client.post("/api/v2/character/create", json={})
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    state_resp = client.get(f"/api/v2/session/{session_id}/state")
    assert state_resp.status_code == 200
    assert state_resp.json()["scenario_mode"] == "bjorn"
