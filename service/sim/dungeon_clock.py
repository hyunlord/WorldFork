"""Phase D 168h — dungeon cycle constants + warning / force-return logic.

본문 정합:
- wiki 010 (미궁 설정) 층별 제한 시간
- ep_0013: "정해진 시간이 되면 미궁은 해당 층에 있던 탐험가들을 도시로 뱉어낸다."
- ep_0036: "층계가 닫히려면 1시간도 안 남은 셈이군."
- ep_0003: "폐쇄까지 10분 남았습니다." / "폐쇄까지 1분 남았습니다."
"""

from __future__ import annotations

from dataclasses import dataclass

# 층별 활동 제한 시간 (hours) — wiki 010 정합
FLOOR_CYCLE_HOURS: dict[int, float] = {
    1: 168.0,       # 7일
    2: 240.0,       # 10일
    3: 15.0 * 24,   # 15일
    4: 23.0 * 24,
    5: 30.0 * 24,
    6: 60.0 * 24,
    7: 75.0 * 24,
}

# 경고 threshold — 남은 시간 (hours)
_WARN_1H = 1.0
_WARN_10MIN = 10.0 / 60.0
_WARN_1MIN = 1.0 / 60.0

# 귀환 시 시간 전진 (hours) — ep_0016 "다음날 정오" 단순 처리
RETURN_TIME_ADVANCE_HOURS = 24.0


@dataclass(frozen=True)
class WarningInfo:
    kind: str       # "1h" | "10min" | "1min"
    message: str


def hours_remaining(floor: int, hours_in_dungeon: float) -> float | None:
    """해당 층의 남은 시간(hours). 층 정보 없으면 None."""
    cycle = FLOOR_CYCLE_HOURS.get(floor)
    if cycle is None:
        return None
    return cycle - hours_in_dungeon


def should_force_return(floor: int, hours_in_dungeon: float) -> bool:
    """강제 귀환 시점 도달 여부."""
    remaining = hours_remaining(floor, hours_in_dungeon)
    if remaining is None:
        return False
    return remaining <= 0.0


def check_warning(
    floor: int,
    prev_hours: float,
    new_hours: float,
) -> WarningInfo | None:
    """이번 턴에 경고 threshold를 넘었으면 WarningInfo 반환, 아니면 None.

    강제 귀환 대상(new_hours >= cycle)은 별도 처리이므로 여기서는 제외.
    """
    cycle = FLOOR_CYCLE_HOURS.get(floor)
    if cycle is None:
        return None

    remaining_prev = cycle - prev_hours
    remaining_new = cycle - new_hours

    if remaining_new <= 0:
        return None  # 강제 귀환 — 별도 처리

    # 가장 급한 threshold 우선
    if remaining_prev > _WARN_1MIN >= remaining_new:
        return WarningInfo(
            kind="1min",
            message="「층계 폐쇄까지 1분 남았습니다.」",
        )
    if remaining_prev > _WARN_10MIN >= remaining_new:
        return WarningInfo(
            kind="10min",
            message="「층계 폐쇄까지 10분 남았습니다.」",
        )
    if remaining_prev > _WARN_1H >= remaining_new:
        return WarningInfo(
            kind="1h",
            message="'층계가 닫히려면 1시간도 안 남은 셈이군.'",
        )
    return None
