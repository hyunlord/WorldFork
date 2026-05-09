"""regenerate_monster.py 본격 단위 검증 (★ Phase 4 vision 검수 답)."""

from __future__ import annotations

from tools.visual.monsters import MONSTERS
from tools.visual.regenerate_monster import REGENERATE_TARGETS


def test_regenerate_targets_count() -> None:
    """검수 X 발견 1종 (★ 노움)."""
    assert len(REGENERATE_TARGETS) == 1


def test_regenerate_includes_gnome() -> None:
    names = [t["name"] for t in REGENERATE_TARGETS]
    assert "노움" in names


def test_gnome_prompt_is_hostile() -> None:
    """노움 적대 mood 본문 22화 정합."""
    data = MONSTERS["노움"]
    text = (
        data["physical"] + " " + data["weapon"] + " " + data["behavior"]
    ).lower()
    assert (
        "hostile" in text
        or "snarling" in text
        or "malicious" in text
        or "aggressive" in text
    )


def test_gnome_has_pickaxe_or_tool() -> None:
    """노움 광부 도구 본격."""
    data = MONSTERS["노움"]
    text = data["weapon"].lower()
    assert "pickaxe" in text or "tool" in text


def test_gnome_threatening_stance() -> None:
    """노움 공격 자세 본격."""
    data = MONSTERS["노움"]
    text = (data["weapon"] + " " + data["behavior"]).lower()
    assert (
        "threatening" in text
        or "attack" in text
        or "territorial" in text
    )
