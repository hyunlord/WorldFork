"""AI Playtester schema 단위 테스트 (★ 1차 commit)."""

from __future__ import annotations

from service.sim.types import (
    PlayerAction,
    PlayerActionType,
    SimConfig,
    SimResult,
    TurnLog,
)


def test_player_action_type_enum_values() -> None:
    """PlayerActionType enum 본질 (★ 1층 자료 본문 매핑)."""
    assert PlayerActionType.ACTIVATE_LIGHT.value == "activate_light"
    assert PlayerActionType.ABSORB_ESSENCE.value == "absorb_essence"
    assert PlayerActionType.OFFER_TO_STONE.value == "offer_to_stone"
    assert PlayerActionType.ENTER_RIFT.value == "enter_rift"


def test_player_action_basic() -> None:
    a = PlayerAction(
        action_type=PlayerActionType.ACTIVATE_LIGHT,
        actor_name="비요른",
        target="횃불",
        rationale="어둠 본질, 빛 활성 필요",
    )
    assert a.action_type == PlayerActionType.ACTIVATE_LIGHT
    assert a.actor_name == "비요른"
    assert a.target == "횃불"


def test_player_action_no_target() -> None:
    a = PlayerAction(
        action_type=PlayerActionType.WAIT,
        actor_name="에르웬",
    )
    assert a.target is None


def test_turn_log_basic() -> None:
    a = PlayerAction(action_type=PlayerActionType.WAIT, actor_name="X")
    log = TurnLog(
        turn_number=1,
        actor_name="X",
        action=a,
        success=True,
        message="시간 흐름",
        hp_before=100,
        hp_after=100,
    )
    assert log.turn_number == 1
    assert log.success
    assert log.hp_before == 100


def test_sim_config_default() -> None:
    c = SimConfig()
    assert c.scenario_id == "barbarian_v2_floor1"
    assert c.max_turns == 50
    assert c.stop_on_permadeath
    assert not c.stop_on_floor_exit


def test_sim_config_custom() -> None:
    c = SimConfig(
        scenario_id="test",
        max_turns=10,
        player_llm_model="9b-q3",
        gm_llm_model="27b-q4",
    )
    assert c.max_turns == 10
    assert c.player_llm_model == "9b-q3"


def test_sim_result_default() -> None:
    r = SimResult(
        sim_id="test_sim",
        config_summary="test",
        total_turns=50,
        completed_turns=0,
    )
    assert r.sim_id == "test_sim"
    assert len(r.turn_logs) == 0
    assert r.total_player_llm_cost == 0.0


def test_sim_result_with_logs() -> None:
    a = PlayerAction(action_type=PlayerActionType.WAIT, actor_name="X")
    log = TurnLog(
        turn_number=1, actor_name="X", action=a, success=True, message=""
    )
    r = SimResult(
        sim_id="test",
        config_summary="",
        total_turns=50,
        completed_turns=1,
        turn_logs=[log],
    )
    assert len(r.turn_logs) == 1
