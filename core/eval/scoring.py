"""Eval scoring (HARNESS_CORE 6장).

Day 5: 단순 평균 + 가중치.
이후:
  - Day 6: per-rule weight, severity별
  - Tier 1+: 신뢰 구간 (bootstrap)
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runner import EvalAttempt


@dataclass
class EvalScore:
    """카테고리별 / 종합 점수."""

    total: float                                   # 0-100
    mechanical_avg: float                          # 0-100
    judge_avg: float | None
    pass_count: int
    total_count: int
    by_category: dict[str, dict[str, float]] = field(default_factory=dict)


def score_results(attempts: list["EvalAttempt"]) -> EvalScore:
    """results → EvalScore.

    가중치:
      - Mechanical 50% + Judge 50% (judge 있을 때)
      - Judge 없으면 Mechanical 100%
    """
    if not attempts:
        return EvalScore(total=0, mechanical_avg=0, judge_avg=None, pass_count=0, total_count=0)

    pass_count = sum(1 for a in attempts if a.final_passed)
    total = len(attempts)

    mechanical_scores = [a.mechanical_score for a in attempts]
    mechanical_avg = sum(mechanical_scores) / total

    judge_scores = [a.judge_score for a in attempts if a.judge_score is not None]
    judge_avg = sum(judge_scores) / len(judge_scores) if judge_scores else None

    if judge_avg is not None:
        total_score = 0.5 * mechanical_avg + 0.5 * judge_avg
    else:
        total_score = mechanical_avg

    by_category: dict[str, dict[str, float]] = {}
    cats = {a.category for a in attempts}
    for cat in cats:
        cat_attempts = [a for a in attempts if a.category == cat]
        cat_pass = sum(1 for a in cat_attempts if a.final_passed)
        cat_mech = sum(a.mechanical_score for a in cat_attempts) / len(cat_attempts)
        cat_judge = [a.judge_score for a in cat_attempts if a.judge_score is not None]
        cat_judge_avg = sum(cat_judge) / len(cat_judge) if cat_judge else None

        by_category[cat] = {
            "count": float(len(cat_attempts)),
            "pass_count": float(cat_pass),
            "pass_rate": cat_pass / len(cat_attempts),
            "mechanical_avg": cat_mech,
            "judge_avg": cat_judge_avg if cat_judge_avg is not None else 0.0,
        }

    return EvalScore(
        total=total_score,
        mechanical_avg=mechanical_avg,
        judge_avg=judge_avg,
        pass_count=pass_count,
        total_count=total,
        by_category=by_category,
    )
