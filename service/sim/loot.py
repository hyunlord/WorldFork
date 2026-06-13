"""V3 수직 슬라이스 Phase 3 — 처치 드롭(마석/정수) → 인벤·소지금.

WORLD_BIBLE §10 등급 경제 참조: 9등급 마석 ≈ 20스톤, 8등급 ≈ 100스톤(등급↑일수록 고가).
병행 경제를 새로 발명하지 않는다 — 등급→스톤 값만 둔다. 정수는 '획득·표시'까지(흡수 자격/
능력 부여/정수 표준가 거래 등 §8.2는 구현 안 함 — 다음 단계, YAGNI). 누적·표시만, §6 세이브 무관.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 등급 → 마석 환산 스톤(WORLD_BIBLE: 숫자 클수록 하위·저가). 미정의 등급은 9등급가.
_MANA_STONE_VALUE: dict[int, int] = {9: 20, 8: 100, 7: 300}


def mana_stone_value(grade: int) -> int:
    """마석 등급 → 소지금(스톤) 환산값."""
    return _MANA_STONE_VALUE.get(grade, _MANA_STONE_VALUE[9])


@dataclass
class Inventory:
    """슬라이스 인벤 — 소지금(스톤) + 마석(등급 목록) + 정수(이름 목록). 표시 전용 상태."""

    stones: int = 0
    mana_stones: list[int] = field(default_factory=list)  # 보유 마석 등급들
    essences: list[str] = field(default_factory=list)  # 수집 정수 이름들


def award_drop(inv: Inventory, *, grade: int, essence: str) -> list[str]:
    """처치 적의 드롭을 인벤에 반영 — 마석→소지금+인벤, 정수→인벤(수집만).

    return: 로그 문구(획득 알림). ★ 정수 흡수/거래는 슬라이스 범위 밖.
    """
    notes: list[str] = []
    value = mana_stone_value(grade)
    inv.stones += value
    inv.mana_stones.append(grade)
    notes.append(f"「{grade}등급 마석 획득 — +{value} 스톤」")
    if essence:
        inv.essences.append(essence)
        notes.append(f"「{essence} 획득(정수 — 수집)」")
    return notes
