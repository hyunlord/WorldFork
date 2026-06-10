"""흥정 메커니즘 — 가격 협상 코드 로직(★ combat.py 정합: 게임 로직은 코드, LLM은 묘사).

다듬기 마지막(비전투 흥정 6축 저점 시스템 2·구체성 2 해소). 전투 패턴 적용:
- 시스템 「」 수치: 「제시가 50 → 협상 35 스톤」 판정을 코드로 계산해 fact에 명시.
- 성공률은 player_level + 난수(rand_func 주입 — 결정적 테스트, combat.py 동일 패턴).

흥정 결과 fact를 GM에 주입 → GM이 구체 서사로 묘사(노움 표정/몸짓). 가격/성공은 코드가 결정.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

# 흥정 할인 폭(성공 시): 기본 가격의 20~40%. 레벨이 높을수록 협상 유리.
_MIN_DISCOUNT = 0.20
_MAX_DISCOUNT = 0.40
# 흥정 성공 확률 기본 + 레벨 보정(레벨당 +3%, 상한 0.85).
_BASE_SUCCESS = 0.45
_LEVEL_BONUS = 0.03
_MAX_SUCCESS = 0.85


@dataclass(frozen=True)
class BarterResult:
    """흥정 판정 결과 — 코드 계산값(GM은 이를 묘사만)."""

    base_price: int
    final_price: int
    success: bool
    discount_pct: int  # 성공 시 할인율(%), 실패 시 0


def compute_barter(
    base_price: int,
    player_level: int = 1,
    rand_func: Callable[[], float] = random.random,
) -> BarterResult:
    """흥정 판정 — 성공률(레벨 보정) + 할인 폭 계산. 실패면 제시가 그대로."""
    success_chance = min(_MAX_SUCCESS, _BASE_SUCCESS + (player_level - 1) * _LEVEL_BONUS)
    if rand_func() >= success_chance:
        return BarterResult(base_price, base_price, success=False, discount_pct=0)
    # 성공: 할인 폭을 난수로 결정(20~40%)
    span = _MAX_DISCOUNT - _MIN_DISCOUNT
    discount = _MIN_DISCOUNT + rand_func() * span
    final = max(1, int(round(base_price * (1.0 - discount))))
    return BarterResult(base_price, final, success=True, discount_pct=int(round(discount * 100)))


def format_barter_fact(result: BarterResult, item: str) -> str:
    """흥정 결과 → 「」 시스템 판정 fact(전투 「명중 — 피해 N」 패턴 정합)."""
    if result.success:
        return (
            f"나는 {item}의 값을 흥정했다. "
            f"「협상 성공 — 제시 {result.base_price} → {result.final_price} 스톤 "
            f"({result.discount_pct}% 절감)」"
        )
    return (
        f"나는 {item}의 값을 흥정했으나 통하지 않았다. "
        f"「협상 실패 — {result.base_price} 스톤 그대로」"
    )
