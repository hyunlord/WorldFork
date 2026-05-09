"""regenerate_missing.py 본격 단위 검증 (★ Phase 2 A)."""

from __future__ import annotations

from tools.visual.regenerate_missing import MISSING_TARGETS


def test_missing_targets_count() -> None:
    """3개 누락 (★ 비요른_00, 에르웬_06, 07)."""
    assert len(MISSING_TARGETS) == 3


def test_missing_targets_includes_bjorn_00() -> None:
    """비요른_00 unknown 재생성 본격."""
    targets = [(t["character"], t["pose_idx"]) for t in MISSING_TARGETS]
    assert ("비요른", 0) in targets


def test_missing_targets_includes_erwen_67() -> None:
    """에르웬_06 + 07 timeout 누락 본격."""
    targets = [(t["character"], t["pose_idx"]) for t in MISSING_TARGETS]
    assert ("에르웬", 6) in targets
    assert ("에르웬", 7) in targets


def test_missing_targets_have_seeds() -> None:
    """모든 target seed int 본격."""
    for t in MISSING_TARGETS:
        assert "seed" in t
        assert isinstance(t["seed"], int)
