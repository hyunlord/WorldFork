"""SimRunner — 단순 오케스트레이터 (★ agent X).

본인 결정 (★ 단계적 4 commit):
- 1차 commit: schema + 빈 run() (★ MockPlayerAgent caller = tests)
- 2차 commit (★ 본 commit): 1턴 진짜 실행
- 3차 commit: 50턴 자동
- 4차 commit: 통계 분석

본 commit 본격:
- run_single_turn() — 1턴 진짜 실행
- _execute_action() — PlayerAction → turn_handler 매핑
  * WAIT → advance_time (★ Stage 7 production wire 진짜 사용)
  * 다른 ActionType: 인식만 (★ 후속 commit이 진짜 mutate)
- run() — 1턴만 호출
"""

from __future__ import annotations

import time
from typing import Any

from service.game.state_v2 import Character, WorldState
from service.game.turn_handler_v2 import advance_time

from .player_agent import MockPlayerAgent, PlayerAgent
from .types import (
    PlayerAction,
    PlayerActionType,
    SimConfig,
    SimResult,
    TurnLog,
)


def _action_to_turn_log(
    turn_number: int,
    action: PlayerAction,
    party: dict[str, Character],
    world: WorldState,
    success: bool,
    message: str,
    side_effects: list[str],
    hp_before: int,
) -> TurnLog:
    """행동 결과 → TurnLog (★ 분석 자료)."""
    actor = party.get(action.actor_name)

    return TurnLog(
        turn_number=turn_number,
        actor_name=action.actor_name,
        action=action,
        success=success,
        message=message,
        side_effects=side_effects,
        hp_before=hp_before,
        hp_after=actor.hp if actor else 0,
        essence_slots_used=actor.essence_slots_used() if actor else 0,
        has_active_light=actor.has_active_light() if actor else False,
        hours_in_dungeon=world.hours_in_dungeon,
    )


def _execute_action(
    action: PlayerAction,
    party: dict[str, Character],
    world: WorldState,
) -> tuple[bool, str, list[str]]:
    """PlayerAction → turn_handler 매핑 + mutate.

    본 commit 2차: WAIT만 진짜 mutate (★ advance_time)
    다른 ActionType은 'recognized but not yet wired' 처리 (★ 3차 commit이 본격)

    Returns:
        (success, message, side_effects)
    """
    if action.action_type == PlayerActionType.WAIT:
        result = advance_time(
            list(party.values()),
            world,
            elapsed_hours=1.0,
        )
        return result.success, result.message, result.side_effects

    return (
        True,
        f"[{action.action_type.value}] 인식 (★ 후속 commit이 진짜 mutate)",
        [],
    )


class SimRunner:
    """단순 오케스트레이터 (★ agent X).

    1턴 흐름:
    1. PlayerAgent → action 생성
    2. action → turn_handler 매핑 → mutate
    3. TurnLog 누적
    """

    def __init__(
        self,
        config: SimConfig,
        player_agent: MockPlayerAgent | PlayerAgent | None = None,
    ) -> None:
        self.config = config
        self.player_agent = player_agent or MockPlayerAgent()

    def run_single_turn(
        self,
        turn_number: int,
        actor_name: str,
        party: dict[str, Character],
        world: WorldState,
        game_context: dict[str, Any] | None = None,
    ) -> TurnLog:
        """단일 턴 진짜 실행 (★ 본 commit 2차).

        - PlayerAgent.generate_action() 진짜 호출
        - PlayerAction → turn_handler 매핑
        - WorldState / Character 진짜 mutate (WAIT 시 advance_time)
        - TurnLog 진짜 작성
        """
        actor = party.get(actor_name)
        if actor is None:
            raise ValueError(f"actor_name not in party: {actor_name}")

        hp_before = actor.hp
        ctx = game_context or {}

        response = self.player_agent.generate_action(actor_name, ctx)
        action = response.action

        success, message, side_effects = _execute_action(action, party, world)

        return _action_to_turn_log(
            turn_number=turn_number,
            action=action,
            party=party,
            world=world,
            success=success,
            message=message,
            side_effects=side_effects,
            hp_before=hp_before,
        )

    def run(
        self,
        party: dict[str, Character] | None = None,
        world: WorldState | None = None,
    ) -> SimResult:
        """N턴 시뮬 실행.

        본 commit 2차: 1턴만 (★ 첫 actor)
        3차 commit: 50턴 + 모든 파티

        Returns:
            SimResult (★ 1턴 turn_log 포함)
        """
        if party is None or world is None:
            return SimResult(
                sim_id=f"sim_{self.config.scenario_id}",
                config_summary=self._config_summary(),
                total_turns=self.config.max_turns,
                completed_turns=0,
                end_reason="no_party_or_world_provided",
            )

        if not party:
            return SimResult(
                sim_id=f"sim_{self.config.scenario_id}",
                config_summary=self._config_summary(),
                total_turns=self.config.max_turns,
                completed_turns=0,
                end_reason="empty_party",
            )

        start_time = time.monotonic()

        first_actor_name = next(iter(party))
        log = self.run_single_turn(
            turn_number=1,
            actor_name=first_actor_name,
            party=party,
            world=world,
        )
        turn_logs = [log]

        elapsed = time.monotonic() - start_time

        final_hp = {name: c.hp for name, c in party.items()}
        essences_count = {
            name: c.essence_slots_used() for name, c in party.items()
        }

        return SimResult(
            sim_id=f"sim_{self.config.scenario_id}",
            config_summary=self._config_summary(),
            total_turns=self.config.max_turns,
            completed_turns=1,  # ★ 본 commit 2차: 1턴만
            turn_logs=turn_logs,
            end_reason="single_turn_2차_commit",
            final_hp_by_actor=final_hp,
            essences_absorbed_by_actor=essences_count,
            final_hours_in_dungeon=world.hours_in_dungeon,
            total_latency_seconds=elapsed,
        )

    def _config_summary(self) -> str:
        return (
            f"max_turns={self.config.max_turns}, "
            f"player={self.config.player_llm_model}, "
            f"gm={self.config.gm_llm_model}"
        )
