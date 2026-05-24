"""audit-step7 fix — FLOOR_1_ZONES lighting 수정 검증."""

from __future__ import annotations

from service.sim.dungeon_zones import get_zone_info


def test_choinipbu_lighting_is_very_dark() -> None:
    """1층 초입부 lighting → very_dark (bright 아님)."""
    info = get_zone_info("1층 초입부", 1)
    assert info is not None
    assert info.lighting == "very_dark"


def test_center_lighting_is_dark() -> None:
    """1층 중심부 lighting → dark (normal 아님)."""
    info = get_zone_info("1층 중심부", 1)
    assert info is not None
    assert info.lighting == "dark"


def test_crystal_cave_lighting_is_bright() -> None:
    """1층 수정 동굴 lighting → bright (변경 없음)."""
    info = get_zone_info("1층 수정 동굴", 1)
    assert info is not None
    assert info.lighting == "bright"


def test_crystal_cave_hint_hwanhan() -> None:
    """1층 수정 동굴 description_hint — '은은한' 제거, '환한' 포함."""
    info = get_zone_info("1층 수정 동굴", 1)
    assert info is not None
    assert "환한" in info.description_hint
    assert "은은한" not in info.description_hint


def test_choinipbu_hint_dark() -> None:
    """1층 초입부 description_hint — 어둠 묘사 포함."""
    info = get_zone_info("1층 초입부", 1)
    assert info is not None
    assert "어두운" in info.description_hint


def test_center_hint_monument() -> None:
    """1층 중심부 description_hint — 기념비 언급 포함."""
    info = get_zone_info("1층 중심부", 1)
    assert info is not None
    assert "기념비" in info.description_hint
