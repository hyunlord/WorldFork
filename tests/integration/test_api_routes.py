"""API 라우트 통합 테스트 (★ Tier 2 D7)."""

import pytest
from fastapi.testclient import TestClient

from service.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


class TestHealthRoute:
    def test_health_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestGameRoutes:
    def test_start_game(self, client: TestClient) -> None:
        response = client.post("/game/start", json={})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "plan" in data
        assert data["initial_state"]["turn"] == 0

    def test_state_not_found(self, client: TestClient) -> None:
        response = client.get("/game/state/nonexistent")
        assert response.status_code == 404

    def test_turn_session_not_found(self, client: TestClient) -> None:
        response = client.post(
            "/game/turn",
            json={"session_id": "nonexistent", "user_action": "주변을 살핍니다"},
        )
        assert response.status_code == 404

    def test_start_then_state(self, client: TestClient) -> None:
        # Start
        start_resp = client.post("/game/start", json={})
        assert start_resp.status_code == 200
        session_id = start_resp.json()["session_id"]

        # Get state
        state_resp = client.get(f"/game/state/{session_id}")
        assert state_resp.status_code == 200
        assert state_resp.json()["turn"] == 0


class TestStaticFiles:
    """정적 파일 라우트 (★ Tier 2 D8)."""

    def test_root_serves_index(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "WorldFork" in response.text
        assert "한국어" in response.text

    def test_static_css(self, client: TestClient) -> None:
        response = client.get("/static/style.css")
        assert response.status_code == 200
        # CSS content-type 확인
        assert "css" in response.headers.get("content-type", "").lower()

    def test_static_js(self, client: TestClient) -> None:
        response = client.get("/static/app.js")
        assert response.status_code == 200
