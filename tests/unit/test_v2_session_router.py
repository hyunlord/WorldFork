"""Phase D step 4 — v2 session router 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from service.api.app import create_app
from service.persistence.sqlite_store import SqliteStore
from service.sim.session_manager import SessionManager, override_session_manager


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    store = SqliteStore(tmp_path / "test.db")
    mgr = SessionManager(store)
    override_session_manager(mgr)
    app = create_app()
    return TestClient(app)


class TestSessionStart:
    def test_default_start(self, client: TestClient) -> None:
        resp = client.post("/api/v2/session/start", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["current_hp"] == 100
        assert data["max_hp"] == 100
        assert data["location"] == "1층 입구"
        assert data["turn_count"] == 0

    def test_custom_start(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v2/session/start",
            json={"current_hp": 50, "max_hp": 80, "inventory": ["단검"], "location": "2층"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_hp"] == 50
        assert data["inventory"] == ["단검"]
        assert data["location"] == "2층"


class TestSessionState:
    def test_get_state(self, client: TestClient) -> None:
        start = client.post("/api/v2/session/start", json={}).json()
        sid = start["session_id"]
        resp = client.get(f"/api/v2/session/{sid}/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sid
        assert "created_at" in data
        assert "last_active" in data

    def test_missing_session_404(self, client: TestClient) -> None:
        resp = client.get("/api/v2/session/nonexistent/state")
        assert resp.status_code == 404


class TestSessionEnd:
    def test_end_session(self, client: TestClient) -> None:
        start = client.post("/api/v2/session/start", json={}).json()
        sid = start["session_id"]
        resp = client.post(f"/api/v2/session/{sid}/end")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ended"

        # 종료 후 조회 → 404
        resp2 = client.get(f"/api/v2/session/{sid}/state")
        assert resp2.status_code == 404

    def test_end_missing_session_404(self, client: TestClient) -> None:
        resp = client.post("/api/v2/session/no-such/end")
        assert resp.status_code == 404
