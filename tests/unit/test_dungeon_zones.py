"""Phase D step 7 — dungeon_zones 단위 테스트."""

from __future__ import annotations

import pytest

from service.sim.dungeon_zones import (
    FLOOR_1_ADJACENCY,
    FLOOR_1_ZONES,
    get_adjacent_zone,
    get_zone_info,
)


def test_floor1_zones_count() -> None:
    assert len(FLOOR_1_ZONES) == 9


def test_floor1_adjacency_coverage() -> None:
    for zone in FLOOR_1_ZONES:
        assert zone in FLOOR_1_ADJACENCY, f"{zone} 누락"


def test_adjacency_targets_valid() -> None:
    for zone, adj_map in FLOOR_1_ADJACENCY.items():
        for direction, target in adj_map.items():
            assert target in FLOOR_1_ZONES, (
                f"{zone} → {direction} → {target} 는 FLOOR_1_ZONES에 없음"
            )


def test_get_zone_info_exact() -> None:
    info = get_zone_info("1층 암흑지대", 1)
    assert info is not None
    assert info.lighting == "very_dark"
    assert info.grade == 3


def test_get_zone_info_bright() -> None:
    info = get_zone_info("1층 수정 동굴", 1)
    assert info is not None
    assert info.lighting == "bright"


def test_get_zone_info_substring() -> None:
    info = get_zone_info("1층 수정", 1)
    assert info is not None
    assert "수정" in info.name


def test_get_zone_info_floor2_returns_none() -> None:
    assert get_zone_info("1층 입구", 2) is None


def test_get_adjacent_zone_center_north() -> None:
    result = get_adjacent_zone("1층 중심부", "north", 1)
    assert result == "1층 북쪽 지구"


def test_get_adjacent_zone_center_south() -> None:
    result = get_adjacent_zone("1층 중심부", "south", 1)
    assert result == "1층 남쪽 지구"


def test_get_adjacent_zone_center_east() -> None:
    result = get_adjacent_zone("1층 중심부", "east", 1)
    assert result == "1층 동쪽 지구"


def test_get_adjacent_zone_center_west() -> None:
    result = get_adjacent_zone("1층 중심부", "west", 1)
    assert result == "1층 서쪽 지구"


def test_get_adjacent_zone_dark_loops_to_dark() -> None:
    result = get_adjacent_zone("1층 암흑지대", "north", 1)
    assert result == "1층 암흑지대"


def test_get_adjacent_zone_substring_match() -> None:
    result = get_adjacent_zone("1층 중심", "north", 1)
    assert result == "1층 북쪽 지구"


def test_get_adjacent_zone_floor2_returns_none() -> None:
    assert get_adjacent_zone("1층 중심부", "north", 2) is None


@pytest.mark.parametrize("zone,lighting", [
    ("1층 입구", "bright"),
    ("1층 수정 동굴", "bright"),
    ("1층 초입부", "very_dark"),
    ("1층 중심부", "dark"),
    ("1층 동쪽 지구", "normal"),
    ("1층 암흑지대", "very_dark"),
])
def test_zone_lighting(zone: str, lighting: str) -> None:
    info = get_zone_info(zone, 1)
    assert info is not None
    assert info.lighting == lighting
