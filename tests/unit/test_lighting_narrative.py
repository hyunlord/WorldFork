"""audit-step7 fix — _lighting_narrative bright suffix 수정 검증."""

from __future__ import annotations

from service.sim.action_handlers import _lighting_narrative  # noqa: PLC2701


def test_bright_narrative_hwanhan() -> None:
    """bright zone → '환하게' 포함."""
    result = _lighting_narrative("1층 수정 동굴", 1)
    assert "환하게" in result
    assert "은은하게" not in result


def test_very_dark_narrative() -> None:
    """very_dark zone → '한 발 앞도 보이지 않는다' 포함."""
    result = _lighting_narrative("1층 암흑지대", 1)
    assert "한 발 앞도 보이지 않는다" in result


def test_dark_narrative() -> None:
    """dark zone → '어둠이 짙어졌다' 포함."""
    result = _lighting_narrative("1층 중심부", 1)
    assert "어둠이 짙어졌다" in result


def test_choinipbu_very_dark_narrative() -> None:
    """1층 초입부 (now very_dark) → very_dark narrative."""
    result = _lighting_narrative("1층 초입부", 1)
    assert "한 발 앞도 보이지 않는다" in result


def test_unknown_zone_returns_empty() -> None:
    """알 수 없는 zone → 빈 문자열."""
    result = _lighting_narrative("알 수 없는 장소", 1)
    assert result == ""
