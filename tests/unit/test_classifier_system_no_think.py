"""INTENT_CLASSIFY_SYSTEM /no_think directive 정합 테스트."""

from __future__ import annotations

from service.sim.intent_classifier import INTENT_CLASSIFY_SYSTEM


def test_classifier_system_starts_no_think() -> None:
    """INTENT_CLASSIFY_SYSTEM 첫 줄에 /no_think directive."""
    assert INTENT_CLASSIFY_SYSTEM.startswith("/no_think")
