"""Phase D step 4 — freeform_action session 통합 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.api.schemas.freeform_action import IntentMatch, StateDelta
from service.api.v2_freeform_router import router as freeform_router
from service.persistence.sqlite_store import SqliteStore
from service.sim.session_manager import SessionManager, override_session_manager


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(freeform_router)
    return app


@pytest.fixture(autouse=True)
def isolate_session_manager(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "test.db")
    mgr = SessionManager(store)
    override_session_manager(mgr)


class TestFreeformSessionIntegration:
    @patch("service.api.v2_freeform_router.classify_intent")
    def test_no_session_id_stateless(self, mock_classify: MagicMock) -> None:
        """session_id 없으면 응답에 session_id=None, session_state=None."""
        mock_classify.return_value = IntentMatch(
            matched_action="rest",
            confidence=0.91,
            reason="휴식",
        )
        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={"user_input": "잠시 쉰다"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["session_id"] is None
        assert body["session_state"] is None

    @patch("service.api.v2_freeform_router.classify_intent")
    def test_with_session_id_returns_session_state(
        self, mock_classify: MagicMock, tmp_path: Path
    ) -> None:
        """session_id 제공 시 응답에 session_id + session_state 포함."""
        mock_classify.return_value = IntentMatch(
            matched_action="rest",
            confidence=0.92,
            reason="휴식",
        )
        store = SqliteStore(tmp_path / "test2.db")
        mgr = SessionManager(store)
        override_session_manager(mgr)

        import asyncio
        state = asyncio.run(mgr.create_session(current_hp=80, max_hp=100))

        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={
                "user_input": "잠시 쉰다",
                "session_id": state.session_id,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["session_id"] == state.session_id
        assert body["session_state"] is not None
        assert body["session_state"]["turn_count"] == 1

    @patch("service.api.v2_freeform_router.classify_intent")
    def test_session_hp_updated_after_attack(
        self, mock_classify: MagicMock, tmp_path: Path
    ) -> None:
        """ATTACK 후 세션 HP 감소 반영."""
        mock_classify.return_value = IntentMatch(
            matched_action="attack",
            confidence=0.95,
            reason="공격",
        )
        store = SqliteStore(tmp_path / "test3.db")
        mgr = SessionManager(store)
        override_session_manager(mgr)

        import asyncio
        state = asyncio.run(
            mgr.create_session(
                current_hp=100,
                max_hp=100,
            )
        )

        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={
                "user_input": "고블린 공격",
                "session_id": state.session_id,
                "encounters": [{"name": "고블린", "hostile": True}],
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["resolved_path"] == "intent"
        assert body["session_state"]["turn_count"] == 1

    @patch("service.api.v2_freeform_router.classify_intent")
    def test_unknown_session_id_auto_creates(
        self, mock_classify: MagicMock
    ) -> None:
        """존재하지 않는 session_id → 자동 신규 세션 생성."""
        mock_classify.return_value = IntentMatch(
            matched_action="wait",
            confidence=0.91,
            reason="대기",
        )
        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={
                "user_input": "잠시 기다린다",
                "session_id": "no-such-session-id",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["session_id"] is not None
        assert body["session_id"] != "no-such-session-id"

    @patch("service.api.v2_freeform_router.freeform_action")
    @patch("service.api.v2_freeform_router.classify_intent")
    def test_fallback_path_updates_session(
        self,
        mock_classify: MagicMock,
        mock_handler: MagicMock,
        tmp_path: Path,
    ) -> None:
        """fallback path도 세션 상태에 반영된다."""
        mock_classify.return_value = IntentMatch(
            matched_action=None,
            confidence=0.2,
            reason="자유",
        )
        mock_handler.return_value = (
            "비요른은 손가락으로 공중에 원을 그려본다." * 2,
            StateDelta(time_advance=1, inventory_add=["이상한 돌멩이"]),
        )
        store = SqliteStore(tmp_path / "test4.db")
        mgr = SessionManager(store)
        override_session_manager(mgr)

        import asyncio
        state = asyncio.run(mgr.create_session())

        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={
                "user_input": "손가락으로 공중에 원을 그린다",
                "session_id": state.session_id,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["resolved_path"] == "fallback"
        assert body["session_state"]["turn_count"] == 1
        assert "이상한 돌멩이" in body["session_state"]["inventory"]
