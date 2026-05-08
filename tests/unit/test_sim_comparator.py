"""다중 시뮬 비교 테스트 (★ 4차 commit)."""

from __future__ import annotations

from service.sim.analyzer import analyze_sim_result
from service.sim.comparator import compare_sims, format_comparison_text
from service.sim.types import (
    PlayerAction,
    PlayerActionType,
    SimResult,
    TurnLog,
)


def _mk_log(turn: int, actor: str, at: PlayerActionType) -> TurnLog:
    return TurnLog(
        turn_number=turn,
        actor_name=actor,
        action=PlayerAction(action_type=at, actor_name=actor),
        success=True,
        message="",
    )


def _mk_result(
    sim_id: str,
    end_reason: str,
    hours: int,
    has_light_action: bool = False,
) -> SimResult:
    logs = [_mk_log(1, "X", PlayerActionType.WAIT)]
    if has_light_action:
        logs.append(_mk_log(2, "X", PlayerActionType.ACTIVATE_LIGHT))

    return SimResult(
        sim_id=sim_id,
        config_summary="",
        total_turns=50,
        completed_turns=50,
        end_reason=end_reason,
        turn_logs=logs,
        final_hp_by_actor={"X": 100},
        final_hours_in_dungeon=hours,
    )


def test_compare_empty() -> None:
    comp = compare_sims([])
    assert comp.sim_count == 0
    assert comp.avg_completed_turns == 0.0
    assert comp.survival_rate == 0.0


def test_compare_single() -> None:
    a = analyze_sim_result(_mk_result("t1", "max_turns", 50))
    comp = compare_sims([a])

    assert comp.sim_count == 1
    assert comp.survival_rate == 1.0
    assert comp.avg_completed_turns == 50


def test_compare_multiple_survival_rate() -> None:
    analyses = [
        analyze_sim_result(_mk_result("t1", "max_turns", 50)),
        analyze_sim_result(_mk_result("t2", "permadeath", 20)),
        analyze_sim_result(_mk_result("t3", "max_turns", 50)),
        analyze_sim_result(_mk_result("t4", "permadeath", 30)),
    ]
    comp = compare_sims(analyses)

    assert comp.sim_count == 4
    assert comp.survival_rate == 0.5  # 2 / 4


def test_compare_time_limit_rate() -> None:
    analyses = [
        analyze_sim_result(_mk_result("t1", "time_limit_168h", 168)),
        analyze_sim_result(_mk_result("t2", "max_turns", 50)),
    ]
    comp = compare_sims(analyses)

    assert comp.time_limit_rate == 0.5


def test_compare_light_usage_rate() -> None:
    analyses = [
        analyze_sim_result(
            _mk_result("t1", "max_turns", 50, has_light_action=True)
        ),
        analyze_sim_result(
            _mk_result("t2", "max_turns", 50, has_light_action=False)
        ),
        analyze_sim_result(
            _mk_result("t3", "max_turns", 50, has_light_action=True)
        ),
    ]
    comp = compare_sims(analyses)

    assert abs(comp.light_usage_rate - 2 / 3) < 0.01


def test_compare_end_reason_distribution() -> None:
    analyses = [
        analyze_sim_result(_mk_result("t1", "max_turns", 50)),
        analyze_sim_result(_mk_result("t2", "max_turns", 50)),
        analyze_sim_result(_mk_result("t3", "permadeath", 20)),
    ]
    comp = compare_sims(analyses)

    assert comp.end_reason_distribution["max_turns"] == 2
    assert comp.end_reason_distribution["permadeath"] == 1


def test_format_comparison_text() -> None:
    analyses = [
        analyze_sim_result(_mk_result("t1", "max_turns", 50)),
    ]
    comp = compare_sims(analyses)
    text = format_comparison_text(comp)

    assert "1 sims" in text
    assert "max_turns" in text
    assert "%" in text
