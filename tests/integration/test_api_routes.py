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

    def test_start_initializes_v2_session_state(
        self, client: TestClient
    ) -> None:
        """★ Tier 2 D12: /start가 v2 schema 진짜 production track."""
        from service.api.game_routes import _sessions

        start_resp = client.post("/game/start", json={})
        session_id = start_resp.json()["session_id"]

        session = _sessions[session_id]
        assert "v2_chars" in session
        assert "v2_world" in session
        assert session["v2_world"].hours_in_dungeon == 0
        # 주인공 진짜 v2 character로 등록
        assert "용감한 모험가" in session["v2_chars"]


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


class TestEndSession:
    """세션 종료 라우트 (★ Tier 2 D10)."""

    def test_end_not_found(self, client: TestClient) -> None:
        response = client.post(
            "/game/end",
            json={"session_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_end_basic(self, client: TestClient) -> None:
        # Start
        start_resp = client.post("/game/start", json={})
        sid = start_resp.json()["session_id"]

        # End
        end_resp = client.post(
            "/game/end",
            json={
                "session_id": sid,
                "comment": "test",
            },
        )
        assert end_resp.status_code == 200
        data = end_resp.json()
        assert "saved_path" in data
        assert data["total_turns"] == 0

    def test_end_with_rating(self, client: TestClient) -> None:
        start_resp = client.post("/game/start", json={})
        sid = start_resp.json()["session_id"]

        end_resp = client.post(
            "/game/end",
            json={
                "session_id": sid,
                "fun_rating": {"score": 5, "comment": "재밌음"},
                "findings": [
                    {
                        "category": "truncation",
                        "description": "응답 잘림",
                        "severity": "major",
                    },
                ],
            },
        )
        assert end_resp.status_code == 200
        assert end_resp.json()["summary"]["fun_score"] == 5

    def test_fun_rating_validation(self, client: TestClient) -> None:
        start_resp = client.post("/game/start", json={})
        sid = start_resp.json()["session_id"]

        # Invalid rating (>5)
        response = client.post(
            "/game/end",
            json={
                "session_id": sid,
                "fun_rating": {"score": 6},
            },
        )
        assert response.status_code == 422

    def test_session_cleared_after_end(self, client: TestClient) -> None:
        start_resp = client.post("/game/start", json={})
        sid = start_resp.json()["session_id"]

        client.post("/game/end", json={"session_id": sid})

        # State 가져오려 시도
        state_resp = client.get(f"/game/state/{sid}")
        assert state_resp.status_code == 404


class TestCrossModelVerify:
    """Cross-Model 검증 (★ A1, game_llm ≠ verify_llm)."""

    def test_game_routes_imports_27b(self) -> None:
        """game_routes.py가 27B factory를 import."""
        import inspect

        from service.api import game_routes

        source = inspect.getsource(game_routes)
        assert "get_qwen36_27b_q3" in source

    def test_cross_model_distinct_names(self) -> None:
        """9B와 27B model_name이 진짜 다름."""
        from core.llm.local_client import get_qwen35_9b_q3, get_qwen36_27b_q3

        c9 = get_qwen35_9b_q3()
        c27 = get_qwen36_27b_q3()
        assert c9.model_name != c27.model_name
