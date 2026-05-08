"""AI Playtester smoke runner — 50턴 자동 시뮬 진짜 실행.

본 commit 3차: production caller (★ MBNU 차단 — 13 ActionType 모두 진짜 호출 가능).
실행: python -m tools.run_sim_smoke

본 CLI = MockPlayerAgent로 다양 ActionType 진짜 mutate 검증.
LLM 통합 시뮬은 PlayerAgent 인스턴스 교체로 가능 (★ get_qwen35_9b_q3 + PlayerAgent).
"""

from __future__ import annotations

import sys

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerAction, PlayerActionType, SimConfig


def _make_test_party() -> dict[str, Character]:
    return {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            physical=14,
            strength=16,
            is_player=True,
        ),
        "에르웬": Character(
            name="에르웬",
            race=Race.FAERIE,
            hp=90,
            hp_max=90,
            soul_power=60,
            soul_power_max=60,
        ),
    }


def _make_test_world() -> WorldState:
    return WorldState(
        current_round=1,
        hours_in_dungeon=0,
        is_dark_zone=True,
        party_members=["비요른", "에르웬"],
    )


def _make_test_location() -> Location:
    return Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="진입점",
        visibility_meters=10,
        has_light=False,
    )


def _make_mock_actions() -> list[PlayerAction]:
    """1층 시나리오 mock — 다양 ActionType (★ 13 모두 커버)."""
    return [
        PlayerAction(
            action_type=PlayerActionType.ACTIVATE_LIGHT,
            actor_name="비요른",
            target="횃불",
        ),
        PlayerAction(
            action_type=PlayerActionType.MOVE,
            actor_name="비요른",
            target="북쪽 통로",
        ),
        PlayerAction(
            action_type=PlayerActionType.EXPLORE,
            actor_name="에르웬",
        ),
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="비요른"),
        PlayerAction(
            action_type=PlayerActionType.ABSORB_ESSENCE,
            actor_name="비요른",
            target="고블린 정수",
        ),
        PlayerAction(
            action_type=PlayerActionType.OFFER_TO_STONE,
            actor_name="비요른",
            target="green_mine",
        ),
        PlayerAction(
            action_type=PlayerActionType.ENTER_RIFT,
            actor_name="비요른",
            target="green_mine",
        ),
        PlayerAction(
            action_type=PlayerActionType.EXPLORE,
            actor_name="에르웬",
        ),
        PlayerAction(action_type=PlayerActionType.REST, actor_name="비요른"),
        PlayerAction(
            action_type=PlayerActionType.EXIT_RIFT,
            actor_name="비요른",
            target="green_mine",
        ),
    ]


def main() -> int:
    config = SimConfig(max_turns=50, scenario_id="floor1_smoke")

    runner = SimRunner(
        config=config,
        player_agent=MockPlayerAgent(mock_actions=_make_mock_actions()),
    )

    party = _make_test_party()
    world = _make_test_world()
    location = _make_test_location()

    print("=== AI Playtester 50턴 smoke (★ Mock) ===")
    result = runner.run(party=party, world=world, location=location)

    print(f"\nsim_id: {result.sim_id}")
    print(f"completed: {result.completed_turns}/{result.total_turns}")
    print(f"end_reason: {result.end_reason}")
    print(f"final HP: {result.final_hp_by_actor}")
    print(f"essences: {result.essences_absorbed_by_actor}")
    print(f"final hours: {result.final_hours_in_dungeon}h / 168h")
    print(f"latency: {result.total_latency_seconds:.2f}s")
    print("\nturn_logs (★ 처음 10):")
    for log in result.turn_logs[:10]:
        status = "OK" if log.success else "X"
        print(
            f"  [{status}] 턴 {log.turn_number} [{log.actor_name}] "
            f"{log.action.action_type.value} → {log.message[:80]}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
