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


# ─── B commit 본격: model combination 비교 매트릭스 ───


@dataclass(frozen=True, slots=True)
class ModelCombination:
    """Player + GM 모델 조합 (★ 4회 비교 매트릭스)."""

    player_model: str
    gm_model: str
    label: str  # "9B+27B" / "27B+27B" 등

    def display_name(self) -> str:
        return f"Player={self.player_model}, GM={self.gm_model}"


@dataclass(frozen=True, slots=True)
class ModelComparisonResult:
    """단일 model combo 시뮬 결과 (★ 분석 + 비용/지연)."""

    combo: ModelCombination
    diversity_score: int
    survived_to_end: bool
    floor_exit_attempted: bool
    light_management_used: bool
    completed_turns: int
    total_turns: int

    # 비용/지연 본격
    total_player_cost_usd: float
    total_player_latency_s: float
    total_gm_cost_usd: float
    total_gm_latency_s: float
    total_runtime_s: float

    # action 분포 (★ top 5)
    top_actions: tuple[tuple[str, int, float], ...]


def build_model_comparison_result(
    combo: ModelCombination,
    analysis: SimAnalysis,
    runtime_s: float,
    gm_cost_usd: float = 0.0,
    gm_latency_s: float = 0.0,
) -> ModelComparisonResult:
    """SimAnalysis → ModelComparisonResult 변환 (★ tools caller)."""
    top = tuple(
        (f.action_type.value, f.count, f.percentage)
        for f in analysis.action_frequencies[:5]
    )

    return ModelComparisonResult(
        combo=combo,
        diversity_score=analysis.diversity_score,
        survived_to_end=analysis.survived_to_end,
        floor_exit_attempted=analysis.floor_exit_attempted,
        light_management_used=analysis.light_management_used,
        completed_turns=analysis.completed_turns,
        total_turns=analysis.total_turns,
        total_player_cost_usd=analysis.total_player_cost_usd,
        total_player_latency_s=analysis.total_latency_seconds,
        total_gm_cost_usd=gm_cost_usd,
        total_gm_latency_s=gm_latency_s,
        total_runtime_s=runtime_s,
        top_actions=top,
    )


def compare_model_combinations(
    results: list[ModelComparisonResult],
) -> str:
    """4회 비교 본격 출력 (★ matrix table)."""
    if not results:
        return "(★ 비교 결과 X)"

    lines = [
        "=" * 80,
        "9B vs 27B Player/GM 비교 매트릭스 (★ B commit 본격 입증)",
        "=" * 80,
        "",
        f"{'조합':<25} {'div':<6} {'생존':<5} {'균열':<5} "
        f"{'빛':<4} {'cost':<10} {'runtime':<10}",
        "-" * 80,
    ]

    for r in results:
        total_cost = r.total_player_cost_usd + r.total_gm_cost_usd
        lines.append(
            f"{r.combo.label:<25} "
            f"{r.diversity_score:>2}/13 "
            f"{'O' if r.survived_to_end else 'X':<5} "
            f"{'O' if r.floor_exit_attempted else 'X':<5} "
            f"{'O' if r.light_management_used else 'X':<4} "
            f"${total_cost:<8.4f} "
            f"{r.total_runtime_s:<9.1f}s"
        )

    lines.extend(["", "## 본격 비교 분석 (★ B commit)", ""])

    sorted_by_div = sorted(results, key=lambda r: -r.diversity_score)
    best = sorted_by_div[0]
    lines.append(
        f"**최고 diversity**: {best.combo.label} "
        f"({best.diversity_score}/13)"
    )

    sorted_by_runtime = sorted(results, key=lambda r: r.total_runtime_s)
    fastest = sorted_by_runtime[0]
    lines.append(
        f"**최저 runtime**: {fastest.combo.label} "
        f"({fastest.total_runtime_s:.1f}s)"
    )

    lines.extend(["", "## action 분포 본격 비교", ""])
    for r in results:
        lines.append(f"### {r.combo.label}")
        for name, count, pct in r.top_actions:
            lines.append(f"  - {name}: {count}회 ({pct:.1f}%)")
        lines.append("")

    return "\n".join(lines)
