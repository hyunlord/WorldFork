"""Audit C — 마석 → 스톤 환산 table.

본문 확정 (ep_0024):
- 9등급 = 20스톤 (돌빵 한 개)
- 8등급 = 100스톤 (고블린 다섯 마리와 동일)

7등급 이하는 본문 미명시 — 5배 비율 추정.
본문 정확 확인 시 table 직접 수정.
"""

from __future__ import annotations

# 등급별 마석 1개 → 스톤 환산 (★ 9·8등급만 본문 확정)
MAGE_STONE_EXCHANGE_RATE: dict[int, int] = {
    9: 20,
    8: 100,
    7: 500,
    6: 2_500,
    5: 12_500,
    4: 62_500,
    3: 312_500,
    2: 1_562_500,
    1: 7_812_500,
}


def compute_stone_for_mage_stone(grade: int, count: int = 1) -> int:
    """등급 마석 N개 → 스톤.

    grade 범위 밖이면 0 반환.
    """
    rate = MAGE_STONE_EXCHANGE_RATE.get(grade, 0)
    return rate * count
