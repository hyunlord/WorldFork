"""SimAnalyzer 단위 테스트 (★ 4차 commit)."""

from __future__ import annotations

from service.sim.analyzer import (
    analyze_sim_result,
    format_analysis_text,
)
from service.sim.types import (
    PlayerAction,
    PlayerActionType,
    SimResult,
    TurnLog,
)


def _mk_log(
    turn: int,
    actor: str,
    action_type: PlayerActionType,
    target: str | None = None,
    hp_before: int = 100,
    hp_after: int = 100,
    has_light: bool = False,
    hours: int = 0,
) -> TurnLog:
    return TurnLog(
        turn_number=turn,
        actor_name=actor,
        action=PlayerAction(
            action_type=action_type, actor_name=actor, target=target
        ),
        success=True,
        message="",
        hp_before=hp_before,
        hp_after=hp_after,
        has_active_light=has_light,
        hours_in_dungeon=hours,
    )


def test_analyze_empty_result() -> None:
    result = SimResult(
        sim_id="empty",
        config_summary="test",
        total_turns=50,
        completed_turns=0,
    )
    a = analyze_sim_result(result)

    assert a.sim_id == "empty"
    assert a.completion_rate == 0.0
    assert a.diversity_score == 0
    assert a.most_used_action is None


def test_analyze_action_frequencies() -> None:
    logs = [
        _mk_log(1, "X", PlayerActionType.WAIT),
        _mk_log(2, "X", PlayerActionType.WAIT),
        _mk_log(3, "X", PlayerActionType.MOVE, target="북쪽 통로"),
        _mk_log(4, "X", PlayerActionType.WAIT),
    ]
    result = SimResult(
        sim_id="t",
        config_summary="",
        total_turns=4,
        completed_turns=4,
        turn_logs=logs,
        final_hp_by_actor={"X": 100},
    )
    a = analyze_sim_result(result)

    assert a.diversity_score == 2
    assert a.most_used_action == PlayerActionType.WAIT

    wait_freq = next(
        f
        for f in a.action_frequencies
        if f.action_type == PlayerActionType.WAIT
    )
    assert wait_freq.count == 3
    assert wait_freq.percentage == 75.0


def test_analyze_completion_rate() -> None:
    result = SimResult(
        sim_id="t",
        config_summary="",
        total_turns=50,
        completed_turns=25,
    )
    a = analyze_sim_result(result)
    assert a.completion_rate == 0.5


def test_analyze_time_limit_reached() -> None:
    result = SimResult(
        sim_id="t",
        config_summary="",
        total_turns=200,
        completed_turns=200,
        final_hours_in_dungeon=168,
    )
    a = analyze_sim_result(result)
    assert a.time_limit_reached

    result2 = SimResult(
        sim_id="t2",
        config_summary="",
        total_turns=50,
        completed_turns=50,
        final_hours_in_dungeon=50,
    )
    a2 = analyze_sim_result(result2)
    assert not a2.time_limit_reached


def test_analyze_actor_stats() -> None:
    logs = [
        _mk_log(
            1,
            "비요른",
            PlayerActionType.WAIT,
            hp_before=100,
            hp_after=100,
            has_light=True,
        ),
        _mk_log(
            2,
            "비요른",
            PlayerActionType.ATTACK,
            hp_before=100,
            hp_after=80,
            has_light=True,
        ),
        _mk_log(
            3,
            "에르웬",
            PlayerActionType.EXPLORE,
            hp_before=90,
            hp_after=90,
        ),
    ]
    result = SimResult(
        sim_id="t",
        config_summary="",
        total_turns=3,
        completed_turns=3,
        turn_logs=logs,
        final_hp_by_actor={"비요른": 80, "에르웬": 90},
        essences_absorbed_by_actor={"비요른": 1, "에르웬": 0},
    )
    a = analyze_sim_result(result)

    bjorn = next(s for s in a.actors if s.actor_name == "비요른")
    assert bjorn.final_hp == 80
    assert bjorn.hp_changes == 1
    assert bjorn.light_active_turns == 2
    assert bjorn.actions_taken == 2

    erwen = next(s for s in a.actors if s.actor_name == "에르웬")
    assert erwen.actions_taken == 1
    assert erwen.light_active_turns == 0


def test_analyze_survived_to_end() -> None:
    result_alive = SimResult(
        sim_id="t1",
        config_summary="",
        total_turns=50,
        completed_turns=50,
        end_reason="max_turns",
    )
    assert analyze_sim_result(result_alive).survived_to_end

    result_dead = SimResult(
        sim_id="t2",
        config_summary="",
        total_turns=50,
        completed_turns=20,
        end_reason="permadeath",
    )
    assert not analyze_sim_result(result_dead).survived_to_end


def test_analyze_floor_exit_attempted() -> None:
    logs = [
        _mk_log(
            1, "X", PlayerActionType.OFFER_TO_STONE, target="green_mine"
        ),
        _mk_log(2, "X", PlayerActionType.ENTER_RIFT, target="green_mine"),
    ]
    result = SimResult(
        sim_id="t",
        config_summary="",
        total_turns=2,
        completed_turns=2,
        turn_logs=logs,
    )
    a = analyze_sim_result(result)
    assert a.floor_exit_attempted


def test_analyze_light_management_used() -> None:
    logs = [
        _mk_log(1, "X", PlayerActionType.ACTIVATE_LIGHT, target="횃불"),
    ]
    result = SimResult(
        sim_id="t",
        config_summary="",
        total_turns=1,
        completed_turns=1,
        turn_logs=logs,
    )
    a = analyze_sim_result(result)
    assert a.light_management_used


def test_format_analysis_text() -> None:
    result = SimResult(
        sim_id="test",
        config_summary="config",
        total_turns=50,
        completed_turns=50,
        end_reason="max_turns",
        turn_logs=[_mk_log(1, "X", PlayerActionType.WAIT)],
        final_hp_by_actor={"X": 100},
    )
    a = analyze_sim_result(result)
    text = format_analysis_text(a)

    assert "test" in text
    assert "max_turns" in text
    assert "diversity" in text
