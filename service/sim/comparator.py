"""다중 시뮬 비교 (★ 4차 commit).

본인 본질:
- 9B vs 27B 비교 (★ 후속 commit 본격)
- N회 평균 통계
- 빌드 패턴 비교
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .analyzer import SimAnalysis


@dataclass(frozen=True, slots=True)
class SimComparison:
    """다중 시뮬 비교 결과."""

    sim_count: int

    # 평균
    avg_completed_turns: float
    avg_hours_in_dungeon: float
    avg_diversity_score: float
    avg_latency_seconds: float

    # 비율
    survival_rate: float                   # 영구사망 X 비율
    light_usage_rate: float                # ACTIVATE_LIGHT 사용 비율
    rift_attempt_rate: float               # 균열 시도 비율
    time_limit_rate: float                 # 168h 도달 비율

    # 종합
    end_reason_distribution: dict[str, int] = field(default_factory=dict)


def compare_sims(analyses: list[SimAnalysis]) -> SimComparison:
    """여러 SimAnalysis → 비교 결과."""
    n = len(analyses)
    if n == 0:
        return SimComparison(
            sim_count=0,
            avg_completed_turns=0.0,
            avg_hours_in_dungeon=0.0,
            avg_diversity_score=0.0,
            avg_latency_seconds=0.0,
            survival_rate=0.0,
            light_usage_rate=0.0,
            rift_attempt_rate=0.0,
            time_limit_rate=0.0,
            end_reason_distribution={},
        )

    avg_turns = sum(a.completed_turns for a in analyses) / n
    avg_hours = sum(a.final_hours_in_dungeon for a in analyses) / n
    avg_diversity = sum(a.diversity_score for a in analyses) / n
    avg_latency = sum(a.total_latency_seconds for a in analyses) / n

    survival = sum(1 for a in analyses if a.survived_to_end) / n
    light = sum(1 for a in analyses if a.light_management_used) / n
    rift = sum(1 for a in analyses if a.floor_exit_attempted) / n
    time_limit = sum(1 for a in analyses if a.time_limit_reached) / n

    reasons: dict[str, int] = {}
    for a in analyses:
        reasons[a.end_reason] = reasons.get(a.end_reason, 0) + 1

    return SimComparison(
        sim_count=n,
        avg_completed_turns=avg_turns,
        avg_hours_in_dungeon=avg_hours,
        avg_diversity_score=avg_diversity,
        avg_latency_seconds=avg_latency,
        survival_rate=survival,
        light_usage_rate=light,
        rift_attempt_rate=rift,
        time_limit_rate=time_limit,
        end_reason_distribution=reasons,
    )


def format_comparison_text(comp: SimComparison) -> str:
    """SimComparison → 보기 좋은 텍스트."""
    lines = [
        f"=== SimComparison ({comp.sim_count} sims) ===",
        "",
        "[평균]",
        f"  완료 턴: {comp.avg_completed_turns:.1f}",
        f"  미궁 시간: {comp.avg_hours_in_dungeon:.1f}h",
        f"  다양성: {comp.avg_diversity_score:.1f} / 13",
        f"  지연: {comp.avg_latency_seconds:.2f}s",
        "",
        "[비율]",
        f"  생존: {comp.survival_rate * 100:.1f}%",
        f"  빛 사용: {comp.light_usage_rate * 100:.1f}%",
        f"  균열 시도: {comp.rift_attempt_rate * 100:.1f}%",
        f"  168h 도달: {comp.time_limit_rate * 100:.1f}%",
        "",
        "[종료 사유]",
    ]
    for reason, count in sorted(
        comp.end_reason_distribution.items(),
        key=lambda x: -x[1],
    ):
        pct = count / comp.sim_count * 100 if comp.sim_count > 0 else 0
        lines.append(f"  - {reason}: {count} ({pct:.1f}%)")

    return "\n".join(lines)
