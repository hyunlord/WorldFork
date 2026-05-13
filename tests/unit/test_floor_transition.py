"""Phase 8 C — 2층 진입 + 4 경로 + 최초 진입 보너스 unit 본격.

검증 본질:
- FLOOR_TWO_PORTAL_SUB_AREAS 본격 4 portal (동/서/남/북)
- SimulationStatus.FLOOR_TRANSITION 재도입 (★ A4 codex YAGNI 제거 → 본격 사용)
- FloorTwoState default + WorldState.floor_two
- enter_floor_two:
  * portal sub_area 밖 → 실패
  * portal sub_area 본격 → 진입, status FLOOR_TRANSITION, Location 본격 2층
  * 최초 진입 → 전 alive 멤버 +500 exp + level up
  * 같은 sim 재진입 → 보너스 X
  * 사망자 본격 보너스 X
- exit_to_floor_one:
  * 미진입 → 실패
  * 진입 후 → 복귀, location 본격 entry_sub_area, status ACTIVE 복원
"""

from __future__ import annotations

from service.game.floors.floor1 import FLOOR_TWO_PORTAL_SUB_AREAS
from service.game.state_v2 import (
    Character,
    FloorTwoState,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
    level_for_exp,
)
from service.game.turn_handler_v2 import (
    FIRST_FLOOR_TWO_ENTRY_EXP_BONUS,
    enter_floor_two,
    exit_to_floor_one,
)


def _strong_party() -> list[Character]:
    return [
        Character(
            name="투르윈",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            is_player=True,
        ),
        Character(
            name="셰인",
            race=Race.HUMAN,
            hp=120,
            hp_max=120,
        ),
    ]


def _loc(sub_area: str = "진입점", floor: int = 1) -> Location:
    return Location(realm=Realm.DUNGEON, floor=floor, sub_area=sub_area)


# ─── 1. Portal sub_area whitelist ───


def test_4_portal_sub_areas_exist() -> None:
    assert len(FLOOR_TWO_PORTAL_SUB_AREAS) == 4
    assert FLOOR_TWO_PORTAL_SUB_AREAS == frozenset({
        "동쪽 포탈 통로",
        "서쪽 포탈 통로",
        "남쪽 포탈 통로",
        "북쪽 포탈 통로",
    })


# ─── 2. SimulationStatus.FLOOR_TRANSITION ───


def test_floor_transition_status_re_added() -> None:
    values = {s.value for s in SimulationStatus}
    assert "transition" in values
    assert SimulationStatus.FLOOR_TRANSITION.value == "transition"


# ─── 3. FloorTwoState + WorldState defaults ───


def test_floor_two_state_defaults() -> None:
    s = FloorTwoState()
    assert s.entered is False
    assert s.entry_turn is None
    assert s.entry_sub_area_from_floor1 is None
    assert s.returned_to_floor1 is False
    assert s.current_sub_area == "2층 도착 지점"


def test_world_state_floor_two_defaults() -> None:
    w = WorldState()
    assert isinstance(w.floor_two, FloorTwoState)
    assert w.floor_two.entered is False
    assert w.first_floor_two_entry_party is False


# ─── 4. enter_floor_two ───


def test_enter_floor_two_fails_when_not_at_portal() -> None:
    party = _strong_party()
    world = WorldState()
    loc = _loc("진입점")
    result = enter_floor_two(party, world, loc, turn_number=1)
    assert result.success is False
    assert "포탈 통로가 아니다" in result.message
    assert world.floor_two.entered is False
    assert world.simulation_status == SimulationStatus.ACTIVE
    assert loc.floor == 1


def test_enter_floor_two_fails_when_sim_not_active() -> None:
    party = _strong_party()
    world = WorldState(simulation_status=SimulationStatus.TIME_LIMIT_REACHED)
    loc = _loc("동쪽 포탈 통로")
    result = enter_floor_two(party, world, loc, turn_number=10)
    assert result.success is False
    assert "Simulation 종료" in result.message
    assert world.floor_two.entered is False


def test_enter_floor_two_succeeds_at_each_portal() -> None:
    for portal in FLOOR_TWO_PORTAL_SUB_AREAS:
        party = _strong_party()
        world = WorldState()
        loc = _loc(portal)
        result = enter_floor_two(party, world, loc, turn_number=20)
        assert result.success is True, f"{portal} 실패"
        assert world.floor_two.entered is True
        assert world.floor_two.entry_sub_area_from_floor1 == portal
        assert world.floor_two.entry_turn == 20
        assert world.simulation_status == SimulationStatus.FLOOR_TRANSITION
        assert loc.floor == 2
        assert loc.sub_area == "2층 도착 지점"


def test_enter_floor_two_side_effect_markers() -> None:
    party = _strong_party()
    world = WorldState()
    loc = _loc("동쪽 포탈 통로")
    result = enter_floor_two(party, world, loc, turn_number=15)
    assert result.success is True
    assert "floor_transition=2" in result.side_effects
    assert "entry_from=동쪽 포탈 통로" in result.side_effects


# ─── 5. 최초 진입 보너스 (★ 본인 답) ───


def test_first_entry_grants_bonus_to_all_alive() -> None:
    party = _strong_party()
    world = WorldState()
    loc = _loc("동쪽 포탈 통로")
    result = enter_floor_two(party, world, loc, turn_number=10)
    assert result.success is True
    assert world.first_floor_two_entry_party is True
    for m in party:
        assert m.experience == FIRST_FLOOR_TWO_ENTRY_EXP_BONUS == 500
        # threshold 500 = level 4
        assert m.level == 4 == level_for_exp(500)
    # marker 본격
    assert "first_floor_two_party=true" in result.side_effects
    assert (
        f"exp_gained=투르윈:{FIRST_FLOOR_TWO_ENTRY_EXP_BONUS}"
        in result.side_effects
    )
    assert "level_up=투르윈:4" in result.side_effects


def test_second_entry_no_bonus() -> None:
    """본 sim 본격 두 번째 진입 = 보너스 X (★ 한달마다 1회)."""
    party = _strong_party()
    world = WorldState()
    loc = _loc("동쪽 포탈 통로")
    enter_floor_two(party, world, loc, turn_number=10)
    # 1층 복귀 후 재진입
    exit_to_floor_one(party, world, loc, turn_number=20)
    loc.sub_area = "서쪽 포탈 통로"  # 다른 portal
    pre_exp = {m.name: m.experience for m in party}

    result = enter_floor_two(party, world, loc, turn_number=30)

    assert result.success is True
    # 보너스 두 번째 X
    for m in party:
        assert m.experience == pre_exp[m.name]
    assert "first_floor_two_party=true" not in result.side_effects
    assert not any(
        s.startswith("exp_gained=") for s in result.side_effects
    )


def test_first_entry_dead_member_no_bonus() -> None:
    """HP=0 멤버 본격 보너스 X (★ alive only)."""
    party = _strong_party()
    party[1].hp = 0  # 셰인 사망
    world = WorldState()
    loc = _loc("동쪽 포탈 통로")
    result = enter_floor_two(party, world, loc, turn_number=10)
    assert result.success is True
    # 투르윈만 보너스
    assert party[0].experience == FIRST_FLOOR_TWO_ENTRY_EXP_BONUS
    assert party[1].experience == 0
    assert "exp_gained=셰인:500" not in result.side_effects


# ─── 6. exit_to_floor_one ───


def test_exit_fails_when_not_entered() -> None:
    party = _strong_party()
    world = WorldState()
    loc = _loc("진입점")
    result = exit_to_floor_one(party, world, loc, turn_number=1)
    assert result.success is False
    assert "진입 기록 없음" in result.message


def test_exit_restores_location_and_status() -> None:
    party = _strong_party()
    world = WorldState()
    loc = _loc("남쪽 포탈 통로")
    enter_floor_two(party, world, loc, turn_number=10)
    # 진입 후 상태 본격
    assert loc.floor == 2
    assert world.simulation_status == SimulationStatus.FLOOR_TRANSITION

    result = exit_to_floor_one(party, world, loc, turn_number=15)

    assert result.success is True
    assert loc.floor == 1
    assert loc.sub_area == "남쪽 포탈 통로"  # ★ 진입 sub_area 복귀
    assert world.simulation_status == SimulationStatus.ACTIVE
    assert world.simulation_over_reason is None
    assert world.simulation_over_turn is None
    assert world.floor_two.returned_to_floor1 is True
    # side effect marker
    assert "floor_transition=1" in result.side_effects
    assert "return_to=남쪽 포탈 통로" in result.side_effects


# ─── 7. _format_simulation_status (★ transition header 재도입) ───


def test_format_simulation_status_transition_header() -> None:
    from service.game.gm_agent import _format_simulation_status
    ctx = {
        "v2_world_state": {
            "simulation_status": "transition",
            "simulation_over_reason": "2층 진입: 동쪽 포탈 통로 → 2층 도착 지점",
            "simulation_over_turn": 25,
        }
    }
    out = _format_simulation_status(ctx)
    assert "2층 진입" in out
    assert "25" in out
    # GM 행동 가이드 본격
    assert "1층 행동" in out


def test_format_simulation_status_active_still_empty() -> None:
    """transition header 추가 후에도 ACTIVE는 빈 문자열 유지."""
    from service.game.gm_agent import _format_simulation_status
    assert _format_simulation_status({"v2_world_state": {}}) == ""
