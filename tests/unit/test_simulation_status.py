"""Phase 8 A4 — 1층 종료 mechanism unit 본격.

검증 본질:
- SimulationStatus enum 4 values
- check_time_limit / check_party_defeated state mutation
- idempotent (★ 이미 종료 상태에선 no-op)
- _check_end_condition 본격 state read
- gm_agent prompt 본격 status header inject (★ ACTIVE 시 빈 문자열)
"""

from __future__ import annotations

from service.game.gm_agent import _format_simulation_status
from service.game.state_v2 import (
    Character,
    Race,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    TIME_LIMIT_HOURS,
    check_party_defeated,
    check_time_limit,
)

# ─── 1. Enum ───


def test_simulation_status_has_4_values() -> None:
    """4 status (★ Phase 8 A4 본격 3개 + Phase 8 C FLOOR_TRANSITION 재도입)."""
    values = {s.value for s in SimulationStatus}
    assert values == {"active", "time_limit", "party_defeated", "transition"}


def test_world_state_default_active() -> None:
    ws = WorldState()
    assert ws.simulation_status == SimulationStatus.ACTIVE
    assert ws.simulation_over_reason is None
    assert ws.simulation_over_turn is None


# ─── 2. check_time_limit ───


def test_time_limit_under_threshold_no_change() -> None:
    world = WorldState(hours_in_dungeon=100)
    triggered = check_time_limit(world, turn_number=10)
    assert triggered is False
    assert world.simulation_status == SimulationStatus.ACTIVE
    assert world.simulation_over_reason is None


def test_time_limit_at_threshold_triggers() -> None:
    world = WorldState(hours_in_dungeon=TIME_LIMIT_HOURS)
    triggered = check_time_limit(world, turn_number=81)
    assert triggered is True
    assert world.simulation_status == SimulationStatus.TIME_LIMIT_REACHED
    assert world.simulation_over_reason is not None
    assert "168" in world.simulation_over_reason
    assert world.simulation_over_turn == 81


def test_time_limit_above_threshold_triggers() -> None:
    world = WorldState(hours_in_dungeon=200)
    triggered = check_time_limit(world, turn_number=5)
    assert triggered is True
    assert world.simulation_status == SimulationStatus.TIME_LIMIT_REACHED


def test_time_limit_idempotent_when_already_over() -> None:
    world = WorldState(
        hours_in_dungeon=300,
        simulation_status=SimulationStatus.PARTY_DEFEATED,
        simulation_over_reason="기존 사유",
        simulation_over_turn=10,
    )
    triggered = check_time_limit(world, turn_number=20)
    assert triggered is False
    # 기존 상태 보존 (★ time_limit override X)
    assert world.simulation_status == SimulationStatus.PARTY_DEFEATED
    assert world.simulation_over_reason == "기존 사유"
    assert world.simulation_over_turn == 10


# ─── 3. check_party_defeated ───


def _make_char(name: str, hp: int) -> Character:
    return Character(name=name, race=Race.HUMAN, hp=hp, hp_max=100)


def test_party_defeated_all_alive_no_change() -> None:
    party = [_make_char("a", 50), _make_char("b", 30)]
    world = WorldState()
    triggered = check_party_defeated(party, world, turn_number=5)
    assert triggered is False
    assert world.simulation_status == SimulationStatus.ACTIVE


def test_party_defeated_partial_dead_no_change() -> None:
    party = [_make_char("a", 0), _make_char("b", 10)]
    world = WorldState()
    triggered = check_party_defeated(party, world, turn_number=5)
    assert triggered is False
    assert world.simulation_status == SimulationStatus.ACTIVE


def test_party_defeated_all_dead_triggers() -> None:
    party = [_make_char("a", 0), _make_char("b", 0)]
    world = WorldState()
    triggered = check_party_defeated(party, world, turn_number=42)
    assert triggered is True
    assert world.simulation_status == SimulationStatus.PARTY_DEFEATED
    assert world.simulation_over_reason == "탐사대 전원 사망."
    assert world.simulation_over_turn == 42


def test_party_defeated_empty_party_no_trigger() -> None:
    """빈 party는 종료 트리거 X — caller가 empty_party로 별도 처리."""
    world = WorldState()
    triggered = check_party_defeated([], world, turn_number=1)
    assert triggered is False
    assert world.simulation_status == SimulationStatus.ACTIVE


def test_party_defeated_idempotent_when_time_limit_already() -> None:
    world = WorldState(
        simulation_status=SimulationStatus.TIME_LIMIT_REACHED,
        simulation_over_reason="기존 사유",
        simulation_over_turn=80,
    )
    party = [_make_char("a", 0), _make_char("b", 0)]
    triggered = check_party_defeated(party, world, turn_number=85)
    assert triggered is False
    # 기존 종료 상태 보존
    assert world.simulation_status == SimulationStatus.TIME_LIMIT_REACHED
    assert world.simulation_over_reason == "기존 사유"
    assert world.simulation_over_turn == 80


# ─── 4. _format_simulation_status (★ GM prompt 본격) ───


def test_prompt_active_returns_empty() -> None:
    ctx = {"v2_world_state": {"simulation_status": "active"}}
    assert _format_simulation_status(ctx) == ""


def test_prompt_no_world_state_returns_empty() -> None:
    """ctx에 v2_world_state 없을 때 안전 fallback."""
    assert _format_simulation_status({}) == ""


def test_prompt_time_limit_header_present() -> None:
    ctx = {
        "v2_world_state": {
            "simulation_status": "time_limit",
            "simulation_over_reason": "7일 (168시간) 만료. 미궁 자동 마을 포탈 귀환.",
            "simulation_over_turn": 81,
        }
    }
    out = _format_simulation_status(ctx)
    assert "7일 만료" in out
    assert "마을" in out
    assert "81" in out
    # GM 행동 가이드 본격
    assert "행동" in out and "선택지" in out


def test_prompt_party_defeated_header_present() -> None:
    ctx = {
        "v2_world_state": {
            "simulation_status": "party_defeated",
            "simulation_over_reason": "탐사대 전원 사망.",
            "simulation_over_turn": 50,
        }
    }
    out = _format_simulation_status(ctx)
    assert "전원 사망" in out
    assert "50" in out
