"""Phase D — 자연어 인터프리터 unit tests.

★ sync 함수 직접 mock + FastAPI TestClient 본 router 호출.
★ async test infra (pytest-asyncio) 미설치 — 외부 패키지 0건 streak.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.llm.client import JSONLLMResponse
from service.api.schemas.freeform_action import (
    FreeformActionRequest,
    FreeformActionResponse,
    IntentMatch,
    StateDelta,
)
from service.api.v2_freeform_router import router as freeform_router
from service.sim.freeform_handler import freeform_action
from service.sim.intent_classifier import classify_intent


def _json_response(parsed: dict[str, Any]) -> JSONLLMResponse:
    return JSONLLMResponse(
        parsed=parsed,
        text="",
        model="mock",
        cost_usd=0.0,
        latency_ms=42,
        input_tokens=10,
        output_tokens=20,
    )


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(freeform_router)
    return app


# ---------------------------------------------------------------------------
# Schema 검증
# ---------------------------------------------------------------------------


class TestFreeformActionRequest:
    def test_minimal(self) -> None:
        req = FreeformActionRequest(user_input="고블린 공격")
        assert req.user_input == "고블린 공격"
        assert req.rationale is None

    def test_with_rationale(self) -> None:
        req = FreeformActionRequest(
            user_input="앞으로 간다", rationale="포탈 확인"
        )
        assert req.rationale == "포탈 확인"

    def test_empty_input_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FreeformActionRequest(user_input="")

    def test_max_length(self) -> None:
        FreeformActionRequest(user_input="a" * 500)
        with pytest.raises(ValidationError):
            FreeformActionRequest(user_input="a" * 501)


class TestStateDelta:
    def test_defaults(self) -> None:
        d = StateDelta()
        assert d.hp_change == 0
        assert d.inventory_add == []
        assert d.time_advance == 1

    def test_time_advance_range(self) -> None:
        StateDelta(time_advance=24)
        with pytest.raises(ValidationError):
            StateDelta(time_advance=25)


class TestFreeformActionResponse:
    def test_intent_path(self) -> None:
        resp = FreeformActionResponse(
            resolved_path="intent",
            matched_action="attack",
            confidence=0.92,
            narrative="비요른은 공격을 시도합니다." + " " * 10,
            state_delta=StateDelta(time_advance=1),
        )
        assert resp.resolved_path == "intent"
        assert resp.matched_action == "attack"

    def test_fallback_path(self) -> None:
        resp = FreeformActionResponse(
            resolved_path="fallback",
            confidence=0.31,
            narrative="비요른은 분수를 들여다본다." * 2,
            state_delta=StateDelta(),
            fallback_reason="자유 행동",
        )
        assert resp.resolved_path == "fallback"
        assert resp.matched_action is None


# ---------------------------------------------------------------------------
# classify_intent — 9B mocked
# ---------------------------------------------------------------------------


class TestClassifyIntent:
    @patch("service.sim.intent_classifier.get_qwen35_9b_q3")
    def test_match_known_action(self, mock_factory: MagicMock) -> None:
        client = MagicMock()
        client.generate_json.return_value = _json_response(
            {
                "matched_action": "attack",
                "confidence": 0.92,
                "reason": "공격 명확",
            }
        )
        mock_factory.return_value = client

        result = classify_intent("고블린을 공격한다")
        assert result.matched_action == "attack"
        assert result.confidence == 0.92
        assert result.reason == "공격 명확"

    @patch("service.sim.intent_classifier.get_qwen35_9b_q3")
    def test_invalid_action_coerced_to_none(
        self, mock_factory: MagicMock
    ) -> None:
        """LLM 본 invalid value 본 → matched_action=None coerce."""
        client = MagicMock()
        client.generate_json.return_value = _json_response(
            {
                "matched_action": "invalid_action_xyz",
                "confidence": 0.77,
                "reason": "test",
            }
        )
        mock_factory.return_value = client

        result = classify_intent("ambiguous")
        assert result.matched_action is None

    @patch("service.sim.intent_classifier.get_qwen35_9b_q3")
    def test_null_matched_action(self, mock_factory: MagicMock) -> None:
        client = MagicMock()
        client.generate_json.return_value = _json_response(
            {
                "matched_action": None,
                "confidence": 0.18,
                "reason": "자유 행동",
            }
        )
        mock_factory.return_value = client

        result = classify_intent("분수에 손을 담그고 잠시 생각에 잠긴다")
        assert result.matched_action is None
        assert result.confidence == 0.18


# ---------------------------------------------------------------------------
# freeform_action — 27B mocked
# ---------------------------------------------------------------------------


class TestFreeformHandler:
    @patch("service.sim.freeform_handler.get_qwen36_27b_q3")
    def test_narrative_and_delta(self, mock_factory: MagicMock) -> None:
        client = MagicMock()
        client.generate_json.return_value = _json_response(
            {
                "narrative": "비요른은 분수에 손을 담그며 잠시 생각에 잠긴다." * 2,
                "state_delta": {
                    "hp_change": 0,
                    "inventory_add": ["젖은 천"],
                    "inventory_remove": [],
                    "location": None,
                    "time_advance": 1,
                    "affinity_changes": {},
                },
            }
        )
        mock_factory.return_value = client

        narrative, delta = freeform_action(
            "분수에 손을 담근다", rationale="잠시 휴식"
        )
        assert "분수" in narrative
        assert delta.inventory_add == ["젖은 천"]
        assert delta.time_advance == 1


# ---------------------------------------------------------------------------
# Router endpoint — FastAPI TestClient + mocked classify/handler
# ---------------------------------------------------------------------------


class TestFreeformRouter:
    @patch("service.api.v2_freeform_router.classify_intent")
    def test_intent_path_high_confidence(
        self, mock_classify: MagicMock
    ) -> None:
        mock_classify.return_value = IntentMatch(
            matched_action="attack",
            confidence=0.92,
            reason="공격 명확",
        )
        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={
                "user_input": "고블린을 공격",
                "encounters": [{"name": "고블린", "hostile": True}],
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["resolved_path"] == "intent"
        assert body["matched_action"] == "attack"
        assert body["confidence"] == 0.92
        assert body["state_delta"]["time_advance"] == 1

    @patch("service.api.v2_freeform_router.freeform_action")
    @patch("service.api.v2_freeform_router.classify_intent")
    def test_fallback_path_low_confidence(
        self,
        mock_classify: MagicMock,
        mock_handler: MagicMock,
    ) -> None:
        mock_classify.return_value = IntentMatch(
            matched_action=None,
            confidence=0.18,
            reason="자유 행동",
        )
        mock_handler.return_value = (
            "비요른은 분수에 손을 담그며 생각에 잠긴다." * 2,
            StateDelta(inventory_add=["젖은 천"], time_advance=1),
        )
        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={
                "user_input": "분수에 손을 담그고 생각에 잠긴다",
                "rationale": "잠시 쉬는 중",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["resolved_path"] == "fallback"
        assert body["matched_action"] is None
        assert body["confidence"] == 0.18
        assert body["fallback_reason"] == "자유 행동"
        assert "분수" in body["narrative"]
        assert body["state_delta"]["inventory_add"] == ["젖은 천"]

    @patch("service.api.v2_freeform_router.freeform_action")
    @patch("service.api.v2_freeform_router.classify_intent")
    def test_matched_action_but_low_confidence_fallback(
        self,
        mock_classify: MagicMock,
        mock_handler: MagicMock,
    ) -> None:
        """matched_action 있어도 confidence < threshold 면 fallback."""
        mock_classify.return_value = IntentMatch(
            matched_action="attack",
            confidence=0.42,
            reason="모호",
        )
        mock_handler.return_value = (
            "비요른은 적을 살피며 자세를 가다듬는다." * 2,
            StateDelta(time_advance=1),
        )
        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={"user_input": "적과 거리를 좁힌다"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["resolved_path"] == "fallback"

    @patch("service.api.v2_freeform_router.classify_intent")
    def test_classifier_error_502(self, mock_classify: MagicMock) -> None:
        mock_classify.side_effect = RuntimeError("backend gone")
        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={"user_input": "x"},
        )
        assert r.status_code == 502
        assert "intent classifier failed" in r.json()["detail"]

    def test_empty_input_422(self) -> None:
        client = TestClient(_app())
        r = client.post(
            "/api/v2/freeform_action",
            json={"user_input": ""},
        )
        assert r.status_code == 422
