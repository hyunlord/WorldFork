"""G commit 본격 time advancement 검증.

본 commit:
- ACTION_HOURS_DELTA dict 본격 (★ 13 ActionType)
- action_hours_delta() (★ 작품 본문 정합)
- determine_phase G 완화 (★ h<2 ENTRY)
- SimRunner time advancement 통합
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
    ACTION_HOURS_DELTA,
    DungeonPhase,
    PlayerAction,
    PlayerActionType,
    SimConfig,
    action_hours_delta,
    determine_phase,
)

# ─── ACTION_HOURS_DELTA / action_hours_delta ───


def test_action_hours_delta_immediate() -> None:
    """즉시 ActionType (★ 작품 본문)."""
    assert action_hours_delta(PlayerActionType.ACTIVATE_LIGHT) < 0.5
    assert action_hours_delta(PlayerActionType.ABSORB_ESSENCE) < 0.5
    assert action_hours_delta(PlayerActionType.USE_ITEM) < 0.5


def test_action_hours_delta_rest_4_hours() -> None:
    """REST 4시간 (★ 27화 본문 본격)."""
    assert action_hours_delta(PlayerActionType.REST) == 4.0


def test_action_hours_delta_explore_1_hour() -> None:
    """EXPLORE 1시간 (★ 정탐 본격)."""
    assert action_hours_delta(PlayerActionType.EXPLORE) == 1.0


def test_action_hours_delta_wait_2_hours() -> None:
    """WAIT 2시간."""
    assert action_hours_delta(PlayerActionType.WAIT) == 2.0


def test_action_hours_delta_offer_to_stone_1h() -> None:
    """OFFER_TO_STONE 1시간 (★ 374화 비석 본문)."""
    assert action_hours_delta(PlayerActionType.OFFER_TO_STONE) == 1.0


def test_action_hours_delta_all_actions_mapped() -> None:
    """모든 ActionType 본격 dict 매핑 (★ Phase 9 본격 마을 actions 0.0 허용)."""
    # Phase 9 마을 actions (★ WAIT_IN_VILLAGE / ENTER_DUNGEON)는 별도 day counter 본격
    # → hours_in_dungeon 영향 X → delta=0.0 본격 본격.
    village_actions = {
        PlayerActionType.WAIT_IN_VILLAGE,
        PlayerActionType.ENTER_DUNGEON,
        PlayerActionType.HEAL_AT_TEMPLE,
        PlayerActionType.DIALOGUE,
        PlayerActionType.LIBRARY_SEARCH,
    }
    for at in PlayerActionType:
        assert at in ACTION_HOURS_DELTA, f"{at} 본격 누락"
        delta = action_hours_delta(at)
        if at in village_actions:
            assert delta == 0.0, f"{at}: 마을 action 본격 0.0 본격 ({delta})"
        else:
            assert delta > 0, f"{at}: delta={delta}"


def test_action_hours_delta_default_for_unknown() -> None:
    """매핑 X 시 default 0.5 (★ 안전)."""
    # ★ unknown은 PlayerActionType에 X, 본격 dict get default 0.5
    # → 모든 PlayerActionType 매핑 본격 검증 후 default 본격 보장
    assert all(at in ACTION_HOURS_DELTA for at in PlayerActionType)


# ─── determine_phase G 완화 ───


def test_determine_phase_g_entry_h2_boundary() -> None:
    """G commit ENTRY h<2 본격 (★ F의 h<5 완화)."""
    assert determine_phase(0) == DungeonPhase.ENTRY
    assert determine_phase(1) == DungeonPhase.ENTRY
    # ★ G commit: h=2 → EXPLORE 본격
    assert determine_phase(2) == DungeonPhase.EXPLORE


def test_determine_phase_g_explore_h24_boundary() -> None:
    assert determine_phase(2) == DungeonPhase.EXPLORE
    assert determine_phase(23) == DungeonPhase.EXPLORE
    assert determine_phase(24) == DungeonPhase.COMBAT


def test_determine_phase_g_combat_h72_boundary() -> None:
    assert determine_phase(24) == DungeonPhase.COMBAT
    assert determine_phase(71) == DungeonPhase.COMBAT
    assert determine_phase(72) == DungeonPhase.RIFT


def test_determine_phase_g_rift_full_range() -> None:
    assert determine_phase(72) == DungeonPhase.RIFT
    assert determine_phase(167) == DungeonPhase.RIFT


# ─── SimRunner time advancement 통합 ───


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


def test_explore_advances_time_per_turn() -> None:
    """EXPLORE 매 turn 1h 본격 (★ G semantics: scale=1.0, initial=0)."""
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
    # ★ G semantics: explicit initial=0, scale=1.0 (★ H default override)
    config = SimConfig(
        max_turns=10, initial_hours_in_dungeon=0.0, time_scale=1.0
    )
    runner = SimRunner(
        config=config, player_agent=player_agent, gm_agent=gm_agent
    )

    party, world, location, ctx = _setup()

    runner.run(
        party=party, world=world, location=location, game_context=ctx
    )

    # 10 turn × EXPLORE 1h = 10h 본격
    assert world.hours_in_dungeon >= 9
    assert world.hours_in_dungeon <= 11


def test_rest_advances_4h() -> None:
    """REST 4h 본격 (★ 27화 본문, G semantics)."""
    actions = [
        PlayerAction(
            action_type=PlayerActionType.REST,
            actor_name="비요른",
            target=None,
            rationale="",
        )
    ]
    player_agent = MockPlayerAgent(mock_actions=actions)
    gm_agent = MockSimGMAgent()
    config = SimConfig(
        max_turns=1, initial_hours_in_dungeon=0.0, time_scale=1.0
    )
    runner = SimRunner(
        config=config, player_agent=player_agent, gm_agent=gm_agent
    )

    party, world, location, ctx = _setup()

    runner.run(
        party=party, world=world, location=location, game_context=ctx
    )

    assert world.hours_in_dungeon == 4


def test_50_turns_diverse_actions_reach_combat_or_rift() -> None:
    """50턴 다양 ActionType → COMBAT/RIFT phase 본격 도달.

    avg delta = ~0.7-1.0h × 50 turn = 35-50h+
    → COMBAT (24h+) 또는 RIFT (72h+) 본격.
    """
    diverse_actions = [
        PlayerAction(
            action_type=at, actor_name="비요른", target=None, rationale=""
        )
        for at in [
            PlayerActionType.ACTIVATE_LIGHT,
            PlayerActionType.MOVE,
            PlayerActionType.EXPLORE,
            PlayerActionType.ABSORB_ESSENCE,
            PlayerActionType.ATTACK,
            PlayerActionType.REST,
            PlayerActionType.USE_ITEM,
            PlayerActionType.WAIT,
        ]
    ]
    player_agent = MockPlayerAgent(mock_actions=diverse_actions)
    gm_agent = MockSimGMAgent()
    config = SimConfig(
        max_turns=50, initial_hours_in_dungeon=0.0, time_scale=1.0
    )
    runner = SimRunner(
        config=config, player_agent=player_agent, gm_agent=gm_agent
    )

    party, world, location, ctx = _setup()

    runner.run(
        party=party, world=world, location=location, game_context=ctx
    )

    assert world.hours_in_dungeon >= 24, (
        f"50턴 후 미궁 시간 {world.hours_in_dungeon}h "
        "— COMBAT 도달 X (★ G 회귀)"
    )


def test_absorb_only_still_advances_slowly() -> None:
    """ABSORB만 50턴 → 5h 본격 (★ 0.1×50, EXPLORE 본격 도달, G semantics)."""
    actions = [
        PlayerAction(
            action_type=PlayerActionType.ABSORB_ESSENCE,
            actor_name="비요른",
            target=None,
            rationale="",
        )
    ]
    player_agent = MockPlayerAgent(mock_actions=actions)
    gm_agent = MockSimGMAgent()
    config = SimConfig(
        max_turns=50, initial_hours_in_dungeon=0.0, time_scale=1.0
    )
    runner = SimRunner(
        config=config, player_agent=player_agent, gm_agent=gm_agent
    )

    party, world, location, ctx = _setup()

    runner.run(
        party=party, world=world, location=location, game_context=ctx
    )

    # 0.1 × 50 = 5h → EXPLORE phase 본격 (★ G h<2 ENTRY 탈출)
    assert world.hours_in_dungeon >= 4
    assert determine_phase(world.hours_in_dungeon) == DungeonPhase.EXPLORE
