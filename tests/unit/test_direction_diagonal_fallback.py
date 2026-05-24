"""audit-step7 fix — 대각선 방향 → 4방향 fallback 검증."""

from __future__ import annotations

from service.sim.action_handlers import _KOR_TO_4WAY  # noqa: PLC2701


def test_northeast_maps_to_north() -> None:
    assert _KOR_TO_4WAY["북동"] == "north"


def test_northwest_maps_to_north() -> None:
    assert _KOR_TO_4WAY["북서"] == "north"


def test_southeast_maps_to_south() -> None:
    assert _KOR_TO_4WAY["남동"] == "south"


def test_southwest_maps_to_south() -> None:
    assert _KOR_TO_4WAY["남서"] == "south"


def test_cardinal_directions_preserved() -> None:
    """기존 기본 4방향 변경 없음."""
    assert _KOR_TO_4WAY["북"] == "north"
    assert _KOR_TO_4WAY["남"] == "south"
    assert _KOR_TO_4WAY["동"] == "east"
    assert _KOR_TO_4WAY["서"] == "west"
