"""audit-step7 fix — FLOOR_1_ADJACENCY 자기참조·방향 버그 수정 검증."""

from __future__ import annotations

from service.sim.dungeon_zones import get_adjacent_zone


def test_entrance_south_is_none() -> None:
    """1층 입구 남쪽 이동 불가 (자기참조 self-loop 제거)."""
    result = get_adjacent_zone("1층 입구", "south", 1)
    assert result is None


def test_entrance_north_is_choinipbu() -> None:
    """1층 입구 북쪽 → 1층 초입부."""
    assert get_adjacent_zone("1층 입구", "north", 1) == "1층 초입부"


def test_east_district_south_is_center() -> None:
    """1층 동쪽 지구 남쪽 → 1층 중심부 (1층 입구 아님)."""
    assert get_adjacent_zone("1층 동쪽 지구", "south", 1) == "1층 중심부"


def test_west_district_south_is_center() -> None:
    """1층 서쪽 지구 남쪽 → 1층 중심부 (1층 입구 아님)."""
    assert get_adjacent_zone("1층 서쪽 지구", "south", 1) == "1층 중심부"


def test_east_district_north_is_dark() -> None:
    """1층 동쪽 지구 북쪽 → 1층 암흑지대 (변경 없음)."""
    assert get_adjacent_zone("1층 동쪽 지구", "north", 1) == "1층 암흑지대"


def test_west_district_north_is_dark() -> None:
    """1층 서쪽 지구 북쪽 → 1층 암흑지대 (변경 없음)."""
    assert get_adjacent_zone("1층 서쪽 지구", "north", 1) == "1층 암흑지대"
