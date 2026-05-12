"""Tier 2 action API 통합 테스트 (★ Phase 7j, FastAPI TestClient).

POST /api/v2/action — 13 PlayerActionType 본격 execute + state mutation.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from service.api.app import create_app
from service.api.v2_state_router import get_holder


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    get_holder().reset()
    return TestClient(app)


class TestActionUnknown:
    def test_unknown_action_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/v2/action", json={"action_type": "UNKNOWN_FOO"}
        )
        assert response.status_code == 400
        assert "Unknown action_type" in response.json()["detail"]


class TestActionBasic:
    def test_explore_success(self, client: TestClient) -> None:
        """★ EXPLORE 본격 안전 본격 (★ 시간 0.5h)."""
        response = client.post(
            "/api/v2/action", json={"action_type": "explore"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "탐색" in data["message"] or "주변" in data["message"]
        assert data["turn"] == 1

    def test_state_returned(self, client: TestClient) -> None:
        response = client.post(
            "/api/v2/action", json={"action_type": "explore"}
        )
        data = response.json()
        assert "state" in data
        assert "characters" in data["state"]
        assert "world" in data["state"]
        assert "location" in data["state"]

    def test_turn_increments(self, client: TestClient) -> None:
        before = client.get("/api/v2/state").json()["turn"]
        client.post("/api/v2/action", json={"action_type": "explore"})
        client.post("/api/v2/action", json={"action_type": "explore"})
        after = client.get("/api/v2/state").json()["turn"]
        assert after == before + 2


class TestActionActor:
    def test_default_actor_first_party(self, client: TestClient) -> None:
        """★ actor None 본격 시 첫 party member (★ 비요른)."""
        client.post(
            "/api/v2/action", json={"action_type": "explore"}
        )
        actions = client.get(
            "/api/v2/state/recent_actions?n=1"
        ).json()["actions"]
        assert actions[-1]["actor"] == "비요른"

    def test_explicit_actor(self, client: TestClient) -> None:
        response = client.post(
            "/api/v2/action",
            json={"action_type": "explore", "actor": "에르웬"},
        )
        assert response.status_code == 200
        actions = client.get(
            "/api/v2/state/recent_actions?n=1"
        ).json()["actions"]
        assert actions[-1]["actor"] == "에르웬"


class TestActionTargets:
    def test_enter_rift_inactive_fails_gracefully(
        self, client: TestClient
    ) -> None:
        """★ active_rifts empty 본격 ENTER_RIFT → success=False, 200 OK."""
        response = client.post(
            "/api/v2/action",
            json={"action_type": "enter_rift", "target": "핏빛성채"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "비활성" in data["message"] or "X" in data["message"]

    def test_attack_no_target_fails(self, client: TestClient) -> None:
        response = client.post(
            "/api/v2/action", json={"action_type": "attack"}
        )
        # ★ target X 본격 → success=False (★ _execute_action 본격)
        data = response.json()
        assert data["success"] is False


class TestActionRecentActions:
    def test_recent_actions_logged(self, client: TestClient) -> None:
        client.post("/api/v2/action", json={"action_type": "explore"})
        client.post(
            "/api/v2/action",
            json={"action_type": "enter_rift", "target": "핏빛성채"},
        )
        actions = client.get(
            "/api/v2/state/recent_actions?n=5"
        ).json()["actions"]
        assert len(actions) == 2
        assert actions[0]["action_type"] == "explore"
        assert actions[1]["action_type"] == "enter_rift"
        assert actions[1]["target"] == "핏빛성채"
        # ★ failed 본격 본격 본격 본격
        assert actions[1]["success"] is False


