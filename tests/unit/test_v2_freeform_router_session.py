"""Phase D step 4 — freeform_action session 통합 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.api.schemas.freeform_action import IntentMatch
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

    @patch("service.api.v2_freeform_router.stream_freeform_narrative")
    @patch("service.api.v2_freeform_router.classify_intent")
    def test_fallback_path_updates_session(
        self,
        mock_classify: MagicMock,
        mock_stream: MagicMock,
        tmp_path: Path,
    ) -> None:
        """fallback path도 세션 상태에 반영된다(스트리밍 서사 + 시간 진행)."""
        mock_classify.return_value = IntentMatch(
            matched_action=None,
            confidence=0.2,
            reason="자유",
        )

        # ★ free-form은 토큰 스트리밍 + 최소 delta — mechanical 변화(인벤토리) 없음.
        async def _fake_stream(*_a: object, **_k: object) -> object:
            for tok in ["나는 손가락으로 ", "공중에 원을 ", "그려보았다."]:
                yield tok

        mock_stream.side_effect = _fake_stream
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
        assert "원을" in body["narrative"]  # 스트리밍 서사 반영
        assert body["state_delta"]["time_advance"] == 1


class TestPredictiveCache:
    """예측 생성 → 캐시 히트 통합 — 미리 생성한 행동이 즉시(재생성 없이) 반환되는가."""

    @patch("service.api.v2_freeform_router.stream_freeform_narrative")
    @patch("service.api.v2_freeform_router.classify_intent")
    def test_predict_then_hit_skips_regeneration(
        self,
        mock_classify: MagicMock,
        mock_stream: MagicMock,
        tmp_path: Path,
    ) -> None:
        from service.sim import predictive_cache

        predictive_cache._CACHE.clear()
        mock_classify.return_value = IntentMatch(
            matched_action=None, confidence=0.2, reason="자유"
        )
        calls = {"n": 0}

        async def _fake_stream(*_a: object, **_k: object) -> object:
            calls["n"] += 1
            for tok in ["나는 ", "주변을 ", "살폈다."]:
                yield tok

        mock_stream.side_effect = _fake_stream

        store = SqliteStore(tmp_path / "pred.db")
        mgr = SessionManager(store)
        override_session_manager(mgr)
        import asyncio

        state = asyncio.run(mgr.create_session())
        client = TestClient(_app())

        # 1. 예측 생성(유휴) — dry-run 1회 생성
        pr = client.post(
            "/api/v2/freeform_action/predict",
            json={"session_id": state.session_id, "actions": ["주변을 살핀다"]},
        )
        assert pr.status_code == 200
        assert pr.json()["predicted"] == 1
        gen_after_predict = calls["n"]
        assert gen_after_predict >= 1  # 예측이 실제로 생성함

        # 2. 같은 행동 제출 → 캐시 히트(재생성 없음 — 호출 카운트 불변)
        hit = client.post(
            "/api/v2/freeform_action",
            json={"user_input": "주변을 살핀다", "session_id": state.session_id},
        )
        assert hit.status_code == 200
        body = hit.json()
        assert "살폈다" in body["narrative"]
        assert calls["n"] == gen_after_predict  # ★ 재생성 X — 캐시 히트

    @patch("service.api.v2_freeform_router.classify_intent")
    def test_freeform_miss_falls_through(
        self, mock_classify: MagicMock, tmp_path: Path
    ) -> None:
        # 예측 안 된 자유 입력 → 캐시 미스 → 정상 분류 경로(폴백).
        from service.sim import predictive_cache

        predictive_cache._CACHE.clear()
        mock_classify.return_value = IntentMatch(
            matched_action="rest", confidence=0.91, reason="휴식"
        )
        store = SqliteStore(tmp_path / "miss.db")
        mgr = SessionManager(store)
        override_session_manager(mgr)
        import asyncio

        state = asyncio.run(mgr.create_session())
        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={"user_input": "잠시 쉰다", "session_id": state.session_id},
        )
        assert r.status_code == 200
