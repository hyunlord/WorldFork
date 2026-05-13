"""Phase 8 a-3 — A4 TIME_LIMIT_REACHED 시 마을 location mutation 본격.

검증 본질 (★ docs/village_spec.md §7.1 정합):
- apply_time_limit_village_return → location.realm=CITY + city_id + sub_area
- PARTY_DEFEATED는 마을 X (★ 본인 답: 시신 = 사물)
- FLOOR_TRANSITION은 마을 X (★ C, 2층)
- sim_runner 본격 TIME_LIMIT 종료 시 자동 호출
"""

from __future__ import annotations

from service.game.cities.registry import (
    DEFAULT_CITY_ENTRY_SUB_AREA,
    DEFAULT_CITY_ID,
)
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import apply_time_limit_village_return
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerAction, PlayerActionType, SimConfig

# ─── 1. apply_time_limit_village_return helper ───


def test_village_return_sets_realm_city() -> None:
    loc = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="진입점",
    )
    apply_time_limit_village_return(loc)
    assert loc.realm == Realm.CITY
    assert loc.floor == 0  # ★ 본인 답 7.2: 마을 = 0
    assert loc.sub_area == DEFAULT_CITY_ENTRY_SUB_AREA == "district_7_plaza"
    assert loc.city_id == DEFAULT_CITY_ID == "rapdonia"


def test_village_return_resets_rift_state() -> None:
    """균열 내부에서 168h 도달 시도 본격 본격 본격 본격 본격 본격 본격 본격 본격."""
    loc = Location(
        realm=Realm.RIFT,
        floor=1,
        sub_area="bc_ch3",
        rift_id="bloody_castle",
        rift_sub_area="bc_ch3",
        rift_is_variant=True,
    )
    apply_time_limit_village_return(loc)
    assert loc.realm == Realm.CITY
    assert loc.rift_id is None
    assert loc.rift_sub_area is None
    assert loc.rift_is_variant is False


def test_village_return_sets_light_environment() -> None:
    """마을 = 빛 환경 (★ namu §4 도시)."""
    loc = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="진입점",
        has_light=False,
        visibility_meters=10,
    )
    apply_time_limit_village_return(loc)
    assert loc.has_light is True
    assert loc.visibility_meters >= 100


# ─── 2. sim_runner 본격 자동 호출 (★ e2e) ───


def _strong_party() -> dict[str, Character]:
    return {
        "투르윈": Character(
            name="투르윈",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            is_player=True,
        ),
    }


def _loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


def test_sim_runner_time_limit_triggers_village_return() -> None:
    """WAIT 반복 → 168h 도달 → location 본격 마을 mutation 자동 발현."""
    party = _strong_party()
    world = WorldState(party_members=list(party.keys()))
    loc = _loc()

    actions = [
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="투르윈"),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=200,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=loc)

    assert result.end_reason == "time_limit_168h"
    assert world.simulation_status == SimulationStatus.TIME_LIMIT_REACHED
    # ★ 본 commit 본격 — location 마을 mutation 본격 자동 발현
    assert loc.realm == Realm.CITY
    assert loc.floor == 0
    assert loc.sub_area == "district_7_plaza"
    assert loc.city_id == "rapdonia"


def test_sim_runner_party_defeated_no_village_return() -> None:
    """전원 사망 → 마을 X (★ 본인 답: 시신 = 미궁 연료)."""
    weak_party = {
        "투르윈": Character(
            name="투르윈",
            race=Race.BARBARIAN,
            hp=10,
            hp_max=150,
            physical=5,
            strength=5,
            bone_strength=2,
            is_player=True,
        ),
    }
    world = WorldState(party_members=list(weak_party.keys()))
    loc = _loc()

    actions = [
        PlayerAction(
            action_type=PlayerActionType.ATTACK,
            actor_name="투르윈",
            target="고블린",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=50,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,  # ★ enum 분기 검증
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=weak_party, world=world, location=loc)

    assert result.end_reason == "party_defeated"
    assert world.simulation_status == SimulationStatus.PARTY_DEFEATED
    # ★ 마을 mutation X (★ 본인 답: 시신 본격 마을 X)
    assert loc.realm == Realm.DUNGEON
    assert loc.floor == 1
    assert loc.city_id is None
