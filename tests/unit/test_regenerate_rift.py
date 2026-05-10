"""regenerate_rift.py 본격 단위 검증 (★ Phase 5 vision 검수 답)."""

from __future__ import annotations

from tools.visual.regenerate_rift import REGENERATE_TARGETS
from tools.visual.rifts import RIFTS


def test_regenerate_targets_count() -> None:
    """검수 X 발견 1장 (★ 핏빛성채)."""
    assert len(REGENERATE_TARGETS) == 1


def test_regenerate_includes_blood_fortress() -> None:
    names = [t["name"] for t in REGENERATE_TARGETS]
    assert "핏빛성채" in names


def test_blood_fortress_prompt_mentions_necronomicon() -> None:
    """핏빛성채 prompt Necronomicon 명시 (★ Phase 4 검수 X 답)."""
    data = RIFTS["핏빛성채"]
    text = data["details"].lower()
    assert "necronomicon" in text


def test_blood_fortress_prompt_mentions_weeping() -> None:
    """여신의 눈물 weeping 명시 (★ Phase 4 검수 X 답)."""
    data = RIFTS["핏빛성채"]
    text = data["details"].lower()
    assert "weeping" in text or "tears" in text


def test_blood_fortress_prompt_mentions_grimoire_visible() -> None:
    """그리모어 시각 본격 명시."""
    data = RIFTS["핏빛성채"]
    text = data["details"].lower()
    assert "visible" in text or "altar" in text
