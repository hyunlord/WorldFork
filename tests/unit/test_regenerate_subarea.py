"""regenerate_subarea.py 본격 단위 검증 (★ Phase 3 vision 검수 답)."""

from __future__ import annotations

from tools.visual.regenerate_subarea import REGENERATE_TARGETS
from tools.visual.sub_areas import SUB_AREAS


def test_regenerate_targets_count() -> None:
    """검수 X 발견 2장."""
    assert len(REGENERATE_TARGETS) == 2


def test_regenerate_includes_southern_passage() -> None:
    names = [t["name"] for t in REGENERATE_TARGETS]
    assert "남쪽_통로" in names


def test_regenerate_includes_portal_zone() -> None:
    names = [t["name"] for t in REGENERATE_TARGETS]
    assert "포탈_영역" in names


def test_southern_passage_prompt_mentions_dark() -> None:
    """남쪽_통로 prompt 어둠 본격 명시 (★ 검수 X 답)."""
    data = SUB_AREAS["남쪽_통로"]
    text = (data["atmosphere"] + " " + data["details"]).lower()
    assert (
        "dark" in text
        or "underground" in text
        or "no daylight" in text
    )


def test_southern_passage_prompt_mentions_gnome() -> None:
    """남쪽_통로 prompt 노움 명시."""
    data = SUB_AREAS["남쪽_통로"]
    text = (data["atmosphere"] + " " + data["details"]).lower()
    assert "gnome" in text


def test_portal_zone_prompt_mentions_four() -> None:
    """포탈_영역 prompt 4 본격 명시 (★ 검수 X 답)."""
    data = SUB_AREAS["포탈_영역"]
    text = (data["atmosphere"] + " " + data["details"]).lower()
    assert "four" in text


def test_portal_zone_prompt_mentions_steel() -> None:
    """포탈_영역 4번째 강철 본격 명시."""
    data = SUB_AREAS["포탈_영역"]
    text = data["details"].lower()
    assert "steel" in text or "grey" in text
