"""SimRunner 단위 테스트 (★ 1차 commit, schema만 + F7 location 본격 검증)."""

from __future__ import annotations

from service.game.state_v2 import Character, Location, Race, Realm, WorldState
from service.sim.sim_runner import SimRunner, _execute_action
from service.sim.types import PlayerAction, PlayerActionType, SimConfig, SimResult


def test_sim_runner_init_default() -> None:
    config = SimConfig()
    runner = SimRunner(config=config)
    assert runner.config.max_turns == 50
    assert runner.player_agent is not None  # mock 자동


def test_sim_runner_run_no_party_returns_empty_schema() -> None:
    """run() 인자 없이 호출 → 빈 결과 schema (★ 2차 commit 갱신)."""
    config = SimConfig(max_turns=5)
    runner = SimRunner(config=config)

    result = runner.run()

    assert isinstance(result, SimResult)
    assert result.total_turns == 5
    assert result.completed_turns == 0
    assert "no_party_or_world" in result.end_reason


def test_sim_runner_config_summary_in_result() -> None:
    """config 진짜 result에 반영."""
    config = SimConfig(
        max_turns=10,
        player_llm_model="9b-test",
        gm_llm_model="27b-test",
    )
    runner = SimRunner(config=config)

    result = runner.run()
    assert "max_turns=10" in result.config_summary
    assert "9b-test" in result.config_summary
    assert "27b-test" in result.config_summary


# ─── F7: ENTER_RIFT / EXIT_RIFT 본격 location 변경 검증 ───


def _make_test_party_world_location() -> tuple[
    dict[str, Character], WorldState, Location
]:
    """F7 테스트용 파티 + 1층 DUNGEON + active rift 본격 setup."""
    bjorn = Character(name="비요른", race=Race.BARBARIAN, is_player=True)
    party = {"비요른": bjorn}
    world = WorldState(
        active_rifts=["bloody_castle"],  # ★ 이미 활성 본격 (★ offer 후 가정)
        party_members=["비요른"],
    )
    location = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="포탈 근처",
        has_light=True,
    )
    return party, world, location


def test_enter_rift_success_updates_location_realm() -> None:
    """★ F7: ENTER_RIFT success → location.realm = RIFT + rift_id 본격 설정."""
    party, world, location = _make_test_party_world_location()
    action = PlayerAction(
        actor_name="비요른",
        action_type=PlayerActionType.ENTER_RIFT,
        target="핏빛성채",  # ★ 한국어 alias (F6 본격)
        rationale="균열 진입",
    )

    success, _msg, _side_effects = _execute_action(action, party, world, location)

    assert success
    assert location.realm == Realm.RIFT
    assert location.rift_id == "bloody_castle"  # ★ canonical 본격


def test_enter_rift_inactive_no_location_change() -> None:
    """★ F7: ENTER_RIFT 본격 active_rifts X 본격 success=False → location 그대로."""
    bjorn = Character(name="비요른", race=Race.BARBARIAN, is_player=True)
    party = {"비요른": bjorn}
    world = WorldState(active_rifts=[], party_members=["비요른"])  # ★ empty
    location = Location(realm=Realm.DUNGEON, floor=1, sub_area="포탈 근처")
    action = PlayerAction(
        actor_name="비요른",
        action_type=PlayerActionType.ENTER_RIFT,
        target="핏빛성채",
        rationale="진입 시도",
    )

    success, _msg, _side = _execute_action(action, party, world, location)

    assert not success
    # ★ 실패 시 location 본격 그대로
    assert location.realm == Realm.DUNGEON
    assert location.rift_id is None


def test_exit_rift_success_returns_to_dungeon() -> None:
    """★ F7: EXIT_RIFT success → location.realm = DUNGEON + rift_id None."""
    party, world, _initial_location = _make_test_party_world_location()
    # ★ 균열 안 본격 setup (★ ENTER_RIFT 후 가정)
    location = Location(
        realm=Realm.RIFT,
        floor=1,
        sub_area="균열 내부",
        rift_id="bloody_castle",
        has_light=True,
    )
    action = PlayerAction(
        actor_name="비요른",
        action_type=PlayerActionType.EXIT_RIFT,
        target="핏빛성채",
        rationale="1층 복귀",
    )

    success, _msg, _side = _execute_action(action, party, world, location)

    assert success
    assert location.realm == Realm.DUNGEON
    assert location.rift_id is None


def test_enter_then_exit_rift_round_trip() -> None:
    """★ F7: ENTER → EXIT 본격 라운드트립 본격 location 본격 정상 본격."""
    party, world, location = _make_test_party_world_location()

    # 1. ENTER
    enter = PlayerAction(
        actor_name="비요른",
        action_type=PlayerActionType.ENTER_RIFT,
        target="핏빛성채",
        rationale="진입",
    )
    s1, _, _ = _execute_action(enter, party, world, location)
    assert s1
    assert location.realm == Realm.RIFT
    assert location.rift_id == "bloody_castle"

    # 2. EXIT
    exit_a = PlayerAction(
        actor_name="비요른",
        action_type=PlayerActionType.EXIT_RIFT,
        target="bloody_castle",  # rift_id 본격
        rationale="복귀",
    )
    s2, _, _ = _execute_action(exit_a, party, world, location)
    assert s2
    assert location.realm == Realm.DUNGEON
    assert location.rift_id is None
