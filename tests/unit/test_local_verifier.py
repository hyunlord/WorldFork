"""Tier 1 W1 D2: Local verifier 옵션 (assert_compatible) 테스트."""

import pytest

from core.verify.cross_model import CrossModelEnforcer, CrossModelError


class TestStrictMode:
    """Mode 1: Cross-Model strict (자료 권장)."""

    def test_different_family_ok(self) -> None:
        CrossModelEnforcer.assert_compatible(
            "qwen35-9b-q3", "claude_code", mode="strict"
        )

    def test_same_family_rejected(self) -> None:
        with pytest.raises(CrossModelError, match="same family"):
            CrossModelEnforcer.assert_compatible(
                "qwen35-9b-q3", "qwen36-27b-q2", mode="strict"
            )

    def test_identical_rejected(self) -> None:
        with pytest.raises(CrossModelError, match="Self-rationalization"):
            CrossModelEnforcer.assert_compatible(
                "qwen35-9b-q3", "qwen35-9b-q3", mode="strict"
            )

    def test_openai_vs_qwen_ok(self) -> None:
        CrossModelEnforcer.assert_compatible(
            "qwen35-9b-q3", "codex", mode="strict"
        )

    def test_claude_vs_gemini_ok(self) -> None:
        CrossModelEnforcer.assert_compatible(
            "claude_code", "gemini", mode="strict"
        )


class TestSameFamilyMode:
    """Mode 2: Local-only (★ 본인 인사이트 — 같은 family OK)."""

    def test_same_family_ok(self) -> None:
        CrossModelEnforcer.assert_compatible(
            "qwen35-9b-q3", "qwen36-27b-q2", mode="same_family"
        )

    def test_identical_still_rejected(self) -> None:
        with pytest.raises(CrossModelError, match="Self-rationalization"):
            CrossModelEnforcer.assert_compatible(
                "qwen35-9b-q3", "qwen35-9b-q3", mode="same_family"
            )

    def test_different_family_also_ok(self) -> None:
        CrossModelEnforcer.assert_compatible(
            "qwen35-9b-q3", "claude_code", mode="same_family"
        )

    def test_27b_q3_vs_27b_q2_ok(self) -> None:
        CrossModelEnforcer.assert_compatible(
            "qwen36-27b-q3", "qwen36-27b-q2", mode="same_family"
        )
