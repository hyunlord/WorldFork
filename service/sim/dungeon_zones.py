"""Phase D step 7 — 1층 sub_zone hybrid table + adjacency graph.

본문 정합:
- ep_0004: 1층 수정동굴, 암흑지대, 동서남북 지구
- wiki 010: 동쪽 칼날늑대 / 서쪽 노움 / 남쪽 구울 / 북쪽 고블린
- wiki 010: 1층 포탈 동서남북 방향마다 4개, 최중심부 암흑지대
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["north", "south", "east", "west"]
Lighting = Literal["bright", "normal", "dark", "very_dark"]


@dataclass(frozen=True)
class ZoneInfo:
    name: str
    lighting: Lighting
    grade: int
    description_hint: str


FLOOR_1_ZONES: dict[str, ZoneInfo] = {
    "1층 입구": ZoneInfo(
        "1층 입구", "bright", 1,
        "수정의 빛이 입구를 환하게 비춘다. 포탈 안정화 구역",
    ),
    "1층 수정 동굴": ZoneInfo(
        "1층 수정 동굴", "bright", 1,
        "벽과 천장의 수정이 은은한 빛을 낸다",
    ),
    "1층 초입부": ZoneInfo(
        "1층 초입부", "bright", 1,
        "포탈에서 멀지 않은 곳. 수정 빛이 아직 닿는다",
    ),
    "1층 중심부": ZoneInfo(
        "1층 중심부", "normal", 2,
        "수정의 빛이 약해진 통로. 네 방향의 지구가 합류하는 교차점",
    ),
    "1층 동쪽 지구": ZoneInfo(
        "1층 동쪽 지구", "normal", 2,
        "칼날늑대의 영역. 어둠 속에서 발소리가 들린다",
    ),
    "1층 서쪽 지구": ZoneInfo(
        "1층 서쪽 지구", "normal", 2,
        "노움의 영역. 울퉁불퉁한 바위 지형이 이어진다",
    ),
    "1층 남쪽 지구": ZoneInfo(
        "1층 남쪽 지구", "normal", 2,
        "구울의 영역. 차갑고 축축한 공기가 감돈다",
    ),
    "1층 북쪽 지구": ZoneInfo(
        "1층 북쪽 지구", "normal", 2,
        "고블린의 영역. 멀리서 떠드는 소리가 들린다",
    ),
    "1층 암흑지대": ZoneInfo(
        "1층 암흑지대", "very_dark", 3,
        "빛이 닿지 않는 최외곽부. 횃불 없이는 한 발도 움직일 수 없다",
    ),
}

# 4방향 인접 관계 — 본문 정합 (wiki 010: 포탈 동서남북 4개, 중심부 교차점)
FLOOR_1_ADJACENCY: dict[str, dict[Direction, str]] = {
    "1층 입구": {
        "north": "1층 초입부",
        "south": "1층 입구",
        "east": "1층 동쪽 지구",
        "west": "1층 서쪽 지구",
    },
    "1층 초입부": {
        "north": "1층 중심부",
        "south": "1층 입구",
        "east": "1층 동쪽 지구",
        "west": "1층 서쪽 지구",
    },
    "1층 수정 동굴": {
        "north": "1층 중심부",
        "south": "1층 초입부",
        "east": "1층 동쪽 지구",
        "west": "1층 서쪽 지구",
    },
    "1층 중심부": {
        "north": "1층 북쪽 지구",
        "south": "1층 남쪽 지구",
        "east": "1층 동쪽 지구",
        "west": "1층 서쪽 지구",
    },
    "1층 동쪽 지구": {
        "north": "1층 암흑지대",
        "south": "1층 입구",
        "east": "1층 암흑지대",
        "west": "1층 중심부",
    },
    "1층 서쪽 지구": {
        "north": "1층 암흑지대",
        "south": "1층 입구",
        "east": "1층 중심부",
        "west": "1층 암흑지대",
    },
    "1층 남쪽 지구": {
        "north": "1층 중심부",
        "south": "1층 암흑지대",
        "east": "1층 동쪽 지구",
        "west": "1층 서쪽 지구",
    },
    "1층 북쪽 지구": {
        "north": "1층 암흑지대",
        "south": "1층 중심부",
        "east": "1층 동쪽 지구",
        "west": "1층 서쪽 지구",
    },
    "1층 암흑지대": {
        "north": "1층 암흑지대",
        "south": "1층 중심부",
        "east": "1층 암흑지대",
        "west": "1층 암흑지대",
    },
}


def get_zone_info(zone_name: str, floor: int) -> ZoneInfo | None:
    if floor != 1:
        return None
    if zone_name in FLOOR_1_ZONES:
        return FLOOR_1_ZONES[zone_name]
    for key, info in FLOOR_1_ZONES.items():
        if zone_name in key or key in zone_name:
            return info
    return None


def get_adjacent_zone(zone_name: str, direction: Direction, floor: int) -> str | None:
    if floor != 1:
        return None
    adj = FLOOR_1_ADJACENCY.get(zone_name)
    if adj is not None:
        return adj.get(direction)
    for key, adj_map in FLOOR_1_ADJACENCY.items():
        if zone_name in key or key in zone_name:
            return adj_map.get(direction)
    return None
