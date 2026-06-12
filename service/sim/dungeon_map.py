"""V3 수직 슬라이스 — 미궁 1층(수정 동굴) 경량 타일맵 1겹.

좌표 격자 위 지형만 둔다(벽/바닥/계단/수정 광원). 충돌은 경계+벽뿐 — 내비메시/경로탐색
없음(YAGNI). 수정('*')은 벽이자 광원: is_lit가 수정 반경 안을 '밝음'으로 본다(원작
"벽의 수정이 광원"). 이동 보조(disposition_tick._advance)는 is_blocked를 받아 벽을 피한다.

손으로 짠 작은 맵(방+통로) — PCG는 슬라이스 제외(다음 단계). 좌표·이동·사거리는 V3
엔진(disposition_tick) 것을 재사용하고, 여기서는 '어디가 벽/바닥/광원인가'만 제공한다.
"""

from __future__ import annotations

from dataclasses import dataclass

# 수정 동굴 1층 — '#' 벽 / '.' 바닥 / '>' 계단(내려가는) / '*' 수정(벽 + 광원).
# 가로 통로(2·5·6행)는 좌우로 트여 파티/적이 가운데 장애물을 우회해 교전 가능.
_CRYSTAL_CAVE: tuple[str, ...] = (
    "####**######",
    "#.........>#",
    "#..........#",
    "#....##....#",
    "#....##....#",
    "#..........#",
    "#..........#",
    "######**####",
)
# 수정 광원 반경(맨해튼) — 이 밖은 어둠(blank로 렌더). 작을수록 동굴 어둠이 짙다.
_LIGHT_RADIUS = 6

# 벽으로 취급해 이동을 막는 글자(수정은 벽에 박혀 있어 통과 불가).
_WALL_CHARS = frozenset({"#", "*"})


@dataclass(frozen=True)
class DungeonMap:
    """타일맵 1겹 — 지형 조회만(엔티티는 모름). 좌표는 (x, y) 정수 격자."""

    grid: tuple[str, ...]
    light_radius: int = _LIGHT_RADIUS

    @property
    def width(self) -> int:
        """가로 타일 수."""
        return len(self.grid[0]) if self.grid else 0

    @property
    def height(self) -> int:
        """세로 타일 수."""
        return len(self.grid)

    def char(self, x: int, y: int) -> str:
        """(x, y) 글자 — 경계 밖은 벽('#')."""
        if not self.in_bounds(x, y):
            return "#"
        return self.grid[y][x]

    def in_bounds(self, x: int, y: int) -> bool:
        """격자 안인가."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, x: int, y: int) -> bool:
        """벽(또는 수정)이라 통과 불가인가."""
        return self.char(x, y) in _WALL_CHARS

    def is_blocked(self, pos: tuple[int, int]) -> bool:
        """이동 보조용 — 그 칸이 벽이면 True(경계 밖 포함)."""
        return self.is_wall(pos[0], pos[1])

    def crystals(self) -> list[tuple[int, int]]:
        """수정(광원) 좌표 목록."""
        return [
            (x, y)
            for y, row in enumerate(self.grid)
            for x, c in enumerate(row)
            if c == "*"
        ]

    def stair(self) -> tuple[int, int] | None:
        """내려가는 계단 좌표(없으면 None) — 정찰 목표로도 쓴다."""
        for y, row in enumerate(self.grid):
            x = row.find(">")
            if x >= 0:
                return (x, y)
        return None

    def is_lit(self, x: int, y: int) -> bool:
        """수정 광원 반경 안이라 밝은가 — 밖은 어둠(blank)."""
        return any(
            abs(x - cx) + abs(y - cy) <= self.light_radius for cx, cy in self.crystals()
        )


def crystal_cave() -> DungeonMap:
    """슬라이스 고정 맵 — 미궁 1층 수정 동굴."""
    return DungeonMap(_CRYSTAL_CAVE)
