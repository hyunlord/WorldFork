"""Phase D step 5 — intent classifier entity extraction (mock-based)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from service.api.schemas.freeform_action import ExtractedEntities, IntentMatch
from service.sim.intent_classifier import classify_intent
from service.sim.types import PlayerActionType


def _mock_response(
    matched_action: str | None,
    confidence: float,
    reason: str,
    actor: str | None = None,
    location: str | None = None,
    item: str | None = None,
) -> MagicMock:
    import json as _json
    mock_resp = MagicMock()
    mock_resp.parsed = {
        "matched_action": matched_action,
        "confidence": confidence,
        "reason": reason,
        "entities": {"actor": actor, "location": location, "item": item},
    }
    mock_resp.text = _json.dumps(mock_resp.parsed)
    return mock_resp


@pytest.fixture()
def mock_client() -> MagicMock:
    client = MagicMock()
    with patch("service.sim.intent_classifier.get_qwen35_9b_q3", return_value=client):
        yield client


def test_entities_all_populated(mock_client: MagicMock) -> None:
    mock_client.generate_json.return_value = _mock_response(
        matched_action=PlayerActionType.DIALOGUE.value,
        confidence=0.9,
        reason="대화 의도",
        actor="투르윈",
        location="1층 입구",
        item=None,
    )
    result = classify_intent("투르윈에게 1층 입구에서 말을 건다")
    assert isinstance(result, IntentMatch)
    assert result.entities.actor == "투르윈"
    assert result.entities.location == "1층 입구"
    assert result.entities.item is None


def test_entities_all_null(mock_client: MagicMock) -> None:
    mock_client.generate_json.return_value = _mock_response(
        matched_action=None,
        confidence=0.3,
        reason="자유 행동",
        actor=None,
        location=None,
        item=None,
    )
    result = classify_intent("뭔가 특이한 행동을 한다")
    assert result.matched_action is None
    assert result.confidence == pytest.approx(0.3)
    assert result.entities == ExtractedEntities(actor=None, location=None, item=None)


def test_entities_item_populated(mock_client: MagicMock) -> None:
    mock_client.generate_json.return_value = _mock_response(
        matched_action=PlayerActionType.USE_ITEM.value,
        confidence=0.95,
        reason="아이템 사용",
        actor=None,
        location=None,
        item="회복 포션",
    )
    result = classify_intent("회복 포션을 사용한다")
    assert result.entities.item == "회복 포션"
    assert result.matched_action == PlayerActionType.USE_ITEM.value


def test_invalid_matched_action_falls_back_to_none(mock_client: MagicMock) -> None:
    mock_client.generate_json.return_value = _mock_response(
        matched_action="invalid_action_xyz",
        confidence=0.9,
        reason="잘못된 action",
    )
    result = classify_intent("알 수 없는 행동")
    assert result.matched_action is None


def test_empty_string_entities_normalized_to_none(mock_client: MagicMock) -> None:
    mock_client.generate_json.return_value = _mock_response(
        matched_action=PlayerActionType.MOVE.value,
        confidence=0.85,
        reason="이동",
        actor="",
        location="",
        item="",
    )
    result = classify_intent("이동한다")
    assert result.entities.actor is None
    assert result.entities.location is None
    assert result.entities.item is None
