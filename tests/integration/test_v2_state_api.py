"""Tier 2 state API 통합 테스트 (★ Phase 7a, FastAPI TestClient).

backend 가동 X 본격 in-process 본격.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from service.api.app import create_app
from service.api.v2_state_router import get_holder


@pytest.fixture
def client() -> TestClient:
    """create_app + TestClient + holder reset 본격 (★ 격리)."""
    app = create_app()
    # ★ 본 test 본격 격리 — singleton holder reset 본격
    get_holder().reset()
    return TestClient(app)


class TestGetCurrentState:
    def test_default_state(self, client: TestClient) -> None:
        """default 본격 비요른 + 에르웬, 1층 진입점 DUNGEON 본격."""
        response = client.get("/api/v2/state")
        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert "turn" in data
        assert data["turn"] == 0

    def test_state_structure(self, client: TestClient) -> None:
        response = client.get("/api/v2/state")
        data = response.json()
        state = data["state"]
        # ★ 본격 3 본격
        assert "characters" in state
        assert "world" in state
        assert "location" in state

    def test_characters_default(self, client: TestClient) -> None:
        response = client.get("/api/v2/state")
        chars = response.json()["state"]["characters"]
        assert "비요른" in chars
        assert "에르웬" in chars
        assert chars["비요른"]["race"] == "바바리안"
        assert chars["비요른"]["hp"] == 150
        assert chars["비요른"]["is_player"] is True
        assert chars["에르웬"]["race"] == "요정"

    def test_location_default(self, client: TestClient) -> None:
        response = client.get("/api/v2/state")
        loc = response.json()["state"]["location"]
        assert loc["realm"] == "미궁"
        assert loc["floor"] == 1
        assert loc["sub_area"] == "진입점"
        assert loc["has_light"] is False
        assert loc["rift_id"] is None

    def test_world_default(self, client: TestClient) -> None:
        response = client.get("/api/v2/state")
        world = response.json()["state"]["world"]
        assert world["active_rifts"] == []
        assert world["party_members"] == ["비요른", "에르웬"]
        assert world["hours_in_dungeon"] == 0


class TestRecentActions:
    def test_default_empty(self, client: TestClient) -> None:
        response = client.get("/api/v2/state/recent_actions")
        assert response.status_code == 200
        data = response.json()
        assert data["actions"] == []
        assert data["count"] == 0
        assert data["total"] == 0

    def test_n_param_default_10(self, client: TestClient) -> None:
        response = client.get("/api/v2/state/recent_actions?n=10")
        assert response.status_code == 200

    def test_n_too_low(self, client: TestClient) -> None:
        response = client.get("/api/v2/state/recent_actions?n=0")
        assert response.status_code == 400

    def test_n_too_high(self, client: TestClient) -> None:
        response = client.get("/api/v2/state/recent_actions?n=101")
        assert response.status_code == 400

    def test_returns_slice(self, client: TestClient) -> None:
        """★ holder.recent_actions 본격 본격 → 본격 slice 본격."""
        h = get_holder()
        h.recent_actions = [
            {"turn": i, "action": "ATTACK"} for i in range(15)
        ]
        response = client.get("/api/v2/state/recent_actions?n=5")
        data = response.json()
        assert data["count"] == 5
        assert data["total"] == 15
        # 본격 마지막 5
        assert data["actions"][-1]["turn"] == 14


class TestResetState:
    def test_reset_status(self, client: TestClient) -> None:
        response = client.post("/api/v2/state/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reset"
        assert data["turn"] == 0

    def test_reset_clears_recent_actions(self, client: TestClient) -> None:
        h = get_holder()
        h.recent_actions = [{"turn": 1, "action": "FOO"}]
        h.turn = 5

        client.post("/api/v2/state/reset")
        response = client.get("/api/v2/state/recent_actions")
        assert response.json()["total"] == 0
        # ★ turn 본격 0 본격
        state_response = client.get("/api/v2/state")
        assert state_response.json()["turn"] == 0


class TestAppMount:
    def test_state_route_registered(self, client: TestClient) -> None:
        """★ app.include_router 본격 본격 검증."""
        response = client.get("/api/v2/state")
        assert response.status_code == 200

    def test_existing_routes_remain(
        self, client: TestClient
    ) -> None:
        """★ 기존 /health 본격 본격 본격 (★ 새 router 본격 X)."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
