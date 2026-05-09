"""H commit 본격 initial hours + time scale 검증.

본 commit 본격 (★ G ceiling 7/13 직접 답):
- SimConfig.initial_hours_in_dungeon=48.0 default
- SimConfig.time_scale=2.0 default
- action_hours_delta(action_type, time_scale=N) 본격
- SimRunner.run() initial hours 적용 + time_scale 통합
- = 50턴 본격 RIFT phase (h>72) 도달
"""

from __future__ import annotations

from typing import Any

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_gm_agent import MockSimGMAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import (
    PlayerAction,
    PlayerActionType,
    SimConfig,
    action_hours_delta,
)

# ─── time_scale 단위 ───


def test_action_hours_delta_default_scale_1() -> None:
    """default time_scale=1.0 (★ G commit 본격 backward compat)."""
    assert action_hours_delta(PlayerActionType.REST) == 4.0
    assert action_hours_delta(PlayerActionType.EXPLORE) == 1.0


def test_action_hours_delta_scale_2() -> None:
    """H commit scale=2.0 본격."""
    assert action_hours_delta(PlayerActionType.REST, time_scale=2.0) == 8.0
    assert action_hours_delta(PlayerActionType.EXPLORE, time_scale=2.0) == 2.0
    assert action_hours_delta(PlayerActionType.MOVE, time_scale=2.0) == 1.0
    assert (
        action_hours_delta(PlayerActionType.ABSORB_ESSENCE, time_scale=2.0)
        == 0.2
    )


def test_action_hours_delta_scale_arbitrary() -> None:
    """time_scale 본격 임의 배율."""
    assert action_hours_delta(PlayerActionType.REST, time_scale=0.5) == 2.0
    assert action_hours_delta(PlayerActionType.REST, time_scale=3.0) == 12.0


def test_simconfig_default_initial_hours_72() -> None:
    """SimConfig default initial_hours=72.0 (★ I commit, RIFT 시작).

    H commit (★ 9498338): 48.0 (★ 1-3h 미달)
    I commit (★ 본 commit): 72.0 (★ 첫 turn RIFT phase 본격)
    """
    config = SimConfig()
    assert config.initial_hours_in_dungeon == 72.0


def test_simconfig_default_time_scale_2() -> None:
    """SimConfig default time_scale=2.0 (★ H commit)."""
    config = SimConfig()
    assert config.time_scale == 2.0


def test_simconfig_custom_values() -> None:
    """SimConfig custom 본격."""
    config = SimConfig(
        max_turns=100,
        initial_hours_in_dungeon=24.0,
        time_scale=1.5,
    )
    assert config.max_turns == 100
    assert config.initial_hours_in_dungeon == 24.0
    assert config.time_scale == 1.5


# ─── SimRunner 통합 ───


def _setup() -> tuple[
    dict[str, Character], WorldState, Location, dict[str, Any]
]:
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            physical=14,
            strength=16,
            bone_strength=12,
            is_player=True,
        ),
    }
    world = WorldState(
        current_round=1,
        hours_in_dungeon=0,
        is_dark_zone=True,
        party_members=["비요른"],
    )
    location = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="진입점",
        visibility_meters=10,
        has_light=False,
    )
    ctx: dict[str, Any] = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": False,
                "essence_slots_used": 0,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 0,
            "party_members": ["비요른"],
            "current_round": 1,
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "진입점",
            "visibility_meters": 10,
            "has_light": False,
        },
    }
    return party, world, location, ctx


def test_sim_runner_applies_initial_hours_default() -> None:
    """default config 시 시작 hours=72 본격 (★ I commit RIFT)."""
    actions = [
        PlayerAction(
            action_type=PlayerActionType.WAIT,
            actor_name="비요른",
            target=None,
            rationale="",
        )
    ]
    player_agent = MockPlayerAgent(mock_actions=actions)
    gm_agent = MockSimGMAgent()
    config = SimConfig(max_turns=5)  # ★ I default: initial=72, scale=2.0
    runner = SimRunner(
        config=config, player_agent=player_agent, gm_agent=gm_agent
    )

    party, world, location, ctx = _setup()

    runner.run(
        party=party, world=world, location=location, game_context=ctx
    )

    # I default: 시작 72 + 5 × WAIT(2 × 2 = 4h) = 72 + 20 = 92h (RIFT)
    assert world.hours_in_dungeon >= 72
    assert 85 <= world.hours_in_dungeon <= 100


def test_sim_runner_no_override_if_already_higher() -> None:
    """world.hours가 이미 initial 이상이면 X override."""
    actions = [
        PlayerAction(
            action_type=PlayerActionType.EXPLORE,
            actor_name="비요른",
            target=None,
            rationale="",
        )
    ]
    player_agent = MockPlayerAgent(mock_actions=actions)
    gm_agent = MockSimGMAgent()
    config = SimConfig(
        max_turns=5,
        initial_hours_in_dungeon=48.0,
        time_scale=1.0,
    )
    runner = SimRunner(
        config=config, player_agent=player_agent, gm_agent=gm_agent
    )

    party, world, location, ctx = _setup()
    world.hours_in_dungeon = 60  # 이미 60h

    runner.run(
        party=party, world=world, location=location, game_context=ctx
    )

    # 60h 본격 유지 + 진행 (★ 60 + 5×EXPLORE(1h scale=1.0) = 65h)
    assert world.hours_in_dungeon >= 60


def test_sim_runner_starts_at_rift_phase_default() -> None:
    """I commit default: SimRunner 첫 turn RIFT phase (★ h>=72)."""
    actions = [
        PlayerAction(
            action_type=PlayerActionType.WAIT,
            actor_name="비요른",
            target=None,
            rationale="",
        )
    ]
    player_agent = MockPlayerAgent(mock_actions=actions)
    gm_agent = MockSimGMAgent()
    config = SimConfig(max_turns=1)  # ★ I default
    runner = SimRunner(
        config=config, player_agent=player_agent, gm_agent=gm_agent
    )

    party, world, location, ctx = _setup()

    runner.run(
        party=party, world=world, location=location, game_context=ctx
    )

    # 시작 72h 본격 적용 (★ 1 turn 진행 후 76h 본격)
    assert world.hours_in_dungeon >= 72


def test_50_turns_h_default_reaches_rift_phase() -> None:
    """H default config 50턴 → RIFT phase (h≥72) 본격 도달."""
    diverse_actions = [
        PlayerAction(
            action_type=at,
            actor_name="비요른",
            target=None,
            rationale="",
        )
        for at in [
            PlayerActionType.ACTIVATE_LIGHT,
            PlayerActionType.MOVE,
            PlayerActionType.EXPLORE,
            PlayerActionType.ABSORB_ESSENCE,
            PlayerActionType.ATTACK,
            PlayerActionType.USE_ITEM,
        ]
    ]
    player_agent = MockPlayerAgent(mock_actions=diverse_actions)
    gm_agent = MockSimGMAgent()
    config = SimConfig(max_turns=50)  # ★ H default
    runner = SimRunner(
        config=config, player_agent=player_agent, gm_agent=gm_agent
    )

    party, world, location, ctx = _setup()

    runner.run(
        party=party, world=world, location=location, game_context=ctx
    )

    # 시작 72 + 50 × 평균 0.6h × 2 scale = 72 + 60 = 132h → RIFT 깊숙히
    assert world.hours_in_dungeon >= 90, (
        f"50턴 후 미궁 시간 {world.hours_in_dungeon}h "
        "— RIFT phase 본격 X (★ I 회귀)"
    )


def test_h_explicit_g_compat() -> None:
    """H config로 explicit G 본격 호환 (★ initial=0, scale=1.0)."""
    actions = [
        PlayerAction(
            action_type=PlayerActionType.EXPLORE,
            actor_name="비요른",
            target=None,
            rationale="",
        )
    ]
    player_agent = MockPlayerAgent(mock_actions=actions)
    gm_agent = MockSimGMAgent()
    config = SimConfig(
        max_turns=10,
        initial_hours_in_dungeon=0.0,
        time_scale=1.0,
    )
    runner = SimRunner(
        config=config, player_agent=player_agent, gm_agent=gm_agent
    )

    party, world, location, ctx = _setup()

    runner.run(
        party=party, world=world, location=location, game_context=ctx
    )

    # G 본격: initial=0 + 10 × EXPLORE(1h scale=1.0) = 10h
    assert 9 <= world.hours_in_dungeon <= 11
