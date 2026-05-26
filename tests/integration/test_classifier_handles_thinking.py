"""classifier 경로에서 thinking 포함 응답 정상 parse 통합 테스트."""

from __future__ import annotations

import json

from service.sim.llm_helpers import strip_thinking_tags


def test_classifier_strips_thinking_on_response() -> None:
    """thinking 포함 응답 → strip → JSON parse 성공.

    /no_think 누락 시 fallback strip 정합.
    """
    mock_response = '<think>고민중...</think>{"matched_action": "attack", "confidence": 0.9}'
    cleaned = strip_thinking_tags(mock_response)
    parsed = json.loads(cleaned)
    assert parsed["matched_action"] == "attack"
    assert parsed["confidence"] == 0.9


def test_classifier_strips_multiline_thinking() -> None:
    """다중 줄 thinking + JSON parse 성공."""
    mock_response = (
        "<think>\n분류 고민 중\n여러 줄\n</think>\n"
        '{"matched_action": "explore", "confidence": 0.85}'
    )
    cleaned = strip_thinking_tags(mock_response)
    parsed = json.loads(cleaned)
    assert parsed["matched_action"] == "explore"


def test_no_thinking_json_unchanged() -> None:
    """thinking X — JSON 그대로 parse."""
    raw = '{"matched_action": null, "confidence": 0.3}'
    cleaned = strip_thinking_tags(raw)
    assert cleaned == raw
    parsed = json.loads(cleaned)
    assert parsed["matched_action"] is None
