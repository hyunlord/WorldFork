"""SimResult 통계 분석 (★ 4차 commit).

본인 본질 (★ 5번 본격 분석 결정):
- HP 분포 / 정수 흡수율 / 시간 분포
- 빌드 패턴 (★ ActionType 빈도)
- 종족 매칭
- 작품 매칭 검증 (★ 168h 안 1층 탈출 가능?)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .types import PlayerActionType, SimResult


@dataclass(frozen=True, slots=True)
class ActionFrequency:
    """ActionType 빈도."""

    action_type: PlayerActionType
    count: int
    percentage: float                      # 0.0~100.0


@dataclass(frozen=True, slots=True)
class ActorStats:
    """캐릭터별 통계."""

    actor_name: str
    final_hp: int
    hp_changes: int                        # HP 변동 횟수
    essence_slots_used: int
    light_active_turns: int                # has_active_light = True 턴 수
    actions_taken: int


@dataclass(frozen=True, slots=True)
class SimAnalysis:
    """SimResult 분석 결과 — 본 commit 핵심."""

    sim_id: str
    config_summary: str

    end_reason: str
    completed_turns: int
    total_turns: int
    completion_rate: float

    final_hours_in_dungeon: int
    time_limit_reached: bool               # 168h 도달

    action_frequencies: tuple[ActionFrequency, ...]
    most_used_action: PlayerActionType | None
    diversity_score: int                   # 사용된 ActionType 개수 (★ 13 max)

    actors: tuple[ActorStats, ...]

    # 작품 매칭 검증
    survived_to_end: bool                  # player 영구사망 X
    floor_exit_attempted: bool             # ENTER_RIFT 또는 EXIT_RIFT 발생
    light_management_used: bool            # ACTIVATE_LIGHT 발생

    total_latency_seconds: float
    total_player_cost_usd: float


def analyze_sim_result(result: SimResult) -> SimAnalysis:
    """SimResult → SimAnalysis."""
    action_counter: Counter[PlayerActionType] = Counter(
        log.action.action_type for log in result.turn_logs
    )
    total_actions = sum(action_counter.values())

    frequencies: list[ActionFrequency] = []
    for at in PlayerActionType:
        cnt = action_counter.get(at, 0)
        if cnt > 0:
            pct = (cnt / total_actions * 100.0) if total_actions > 0 else 0.0
            frequencies.append(ActionFrequency(at, cnt, pct))
    frequencies.sort(key=lambda f: -f.count)

    most_used = frequencies[0].action_type if frequencies else None

    actor_stats: list[ActorStats] = []
    for actor_name in result.final_hp_by_actor:
        actor_logs = [
            log for log in result.turn_logs if log.actor_name == actor_name
        ]
        hp_changes = sum(
            1 for log in actor_logs if log.hp_before != log.hp_after
        )
        light_turns = sum(1 for log in actor_logs if log.has_active_light)

        actor_stats.append(
            ActorStats(
                actor_name=actor_name,
                final_hp=result.final_hp_by_actor[actor_name],
                hp_changes=hp_changes,
                essence_slots_used=result.essences_absorbed_by_actor.get(
                    actor_name, 0
                ),
                light_active_turns=light_turns,
                actions_taken=len(actor_logs),
            )
        )

    survived = result.end_reason != "permadeath"
    floor_exit = any(
        log.action.action_type
        in (PlayerActionType.ENTER_RIFT, PlayerActionType.EXIT_RIFT)
        for log in result.turn_logs
    )
    light_used = any(
        log.action.action_type == PlayerActionType.ACTIVATE_LIGHT
        for log in result.turn_logs
    )

    return SimAnalysis(
        sim_id=result.sim_id,
        config_summary=result.config_summary,
        end_reason=result.end_reason,
        completed_turns=result.completed_turns,
        total_turns=result.total_turns,
        completion_rate=(
            result.completed_turns / result.total_turns
            if result.total_turns > 0
            else 0.0
        ),
        final_hours_in_dungeon=result.final_hours_in_dungeon,
        time_limit_reached=(result.final_hours_in_dungeon >= 168),
        action_frequencies=tuple(frequencies),
        most_used_action=most_used,
        diversity_score=len(frequencies),
        actors=tuple(actor_stats),
        survived_to_end=survived,
        floor_exit_attempted=floor_exit,
        light_management_used=light_used,
        total_latency_seconds=result.total_latency_seconds,
        total_player_cost_usd=result.total_player_llm_cost,
    )


def format_analysis_text(analysis: SimAnalysis) -> str:
    """분석 결과 → 보기 좋은 텍스트."""
    lines = [
        f"=== SimAnalysis: {analysis.sim_id} ===",
        f"config: {analysis.config_summary}",
        "",
        "[종료]",
        f"  사유: {analysis.end_reason}",
        f"  완료: {analysis.completed_turns}/{analysis.total_turns} "
        f"({analysis.completion_rate * 100:.1f}%)",
        "",
        "[시간]",
        f"  미궁 시간: {analysis.final_hours_in_dungeon}h / 168h",
        f"  한도 도달: {'O' if analysis.time_limit_reached else 'X'}",
        "",
        f"[행동 빈도] (★ diversity={analysis.diversity_score}/13)",
    ]
    for f in analysis.action_frequencies[:5]:
        lines.append(
            f"  - {f.action_type.value}: {f.count}회 ({f.percentage:.1f}%)"
        )

    lines.extend(["", "[캐릭터별]"])
    for a in analysis.actors:
        lines.append(
            f"  - {a.actor_name}: HP {a.final_hp}, "
            f"정수 {a.essence_slots_used}슬롯, "
            f"빛 {a.light_active_turns}턴, 행동 {a.actions_taken}회"
        )

    lines.extend(
        [
            "",
            "[작품 매칭 검증]",
            f"  생존: {'O' if analysis.survived_to_end else 'X (영구사망)'}",
            f"  균열 시도: {'O' if analysis.floor_exit_attempted else 'X'}",
            f"  빛 관리: {'O' if analysis.light_management_used else 'X'}",
            "",
            "[비용]",
            f"  지연: {analysis.total_latency_seconds:.2f}s",
            f"  LLM cost: ${analysis.total_player_cost_usd:.4f}",
        ]
    )

    return "\n".join(lines)
