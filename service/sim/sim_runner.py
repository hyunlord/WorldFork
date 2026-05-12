"""SimRunner — 단순 오케스트레이터 (★ agent X).

본인 결정 (★ 단계적 4 commit):
- 1차: schema + mock
- 2차: 1턴 진짜 (★ WAIT만 mutate)
- 3차 (★ 본 commit): N턴 자동 + 13 ActionType 본격 mutate
- 4차: 통계 분석
"""

from __future__ import annotations

import time
from typing import Any

from service.game.state_v2 import Character, Location, Realm, WorldState
from service.game.turn_handler_v2 import (
    _resolve_rift_id,
    absorb_floating_essence,
    activate_light,
    advance_time,
    enter_rift,
    execute_attack,
    exit_rift,
    explore_area,
    flee_from_threat,
    move_to_sub_area,
    offer_to_stone,
    rest,
    send_message_stone,
    use_item,
)

from .player_agent import MockPlayerAgent, PlayerAgent
from .sim_gm_agent import MockSimGMAgent, SimGMAgent
from .types import (
    ENCOUNTER_TTL,
    Encounter,
    PlayerAction,
    PlayerActionType,
    SimConfig,
    SimResult,
    TurnLog,
    action_hours_delta,
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
    location: Location,
) -> tuple[bool, str, list[str]]:
    """PlayerAction → turn_handler 매핑 (★ 13 ActionType 모두 mutate).

    본 commit 3차 본격: 모든 ActionType이 진짜 production 함수 호출.
    """
    actor = party.get(action.actor_name)
    party_list = list(party.values())

    if action.action_type == PlayerActionType.WAIT:
        r = advance_time(party_list, world, elapsed_hours=1.0)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.ACTIVATE_LIGHT:
        if not actor or not action.target:
            return False, "actor 또는 target 없음.", []
        r = activate_light(actor, action.target)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.MOVE:
        if not action.target:
            return False, "target sub_area 없음.", []
        r = move_to_sub_area(party_list, world, location, action.target)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.ATTACK:
        if not actor or not action.target:
            return False, "actor 또는 target 없음.", []
        r = execute_attack(actor, action.target, party_list, world)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.ABSORB_ESSENCE:
        if not actor or not action.target:
            return False, "actor 또는 target 없음.", []
        r = absorb_floating_essence(actor, action.target)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.REST:
        r = rest(party_list, world)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.EXPLORE:
        r = explore_area(party_list, world)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.COMMUNICATE:
        if not actor or not action.target:
            return False, "actor 또는 target 없음.", []
        r = send_message_stone(actor, action.target, action.rationale or "")
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.FLEE:
        r = flee_from_threat(party_list, world, action.target or "위협")
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.USE_ITEM:
        if not actor or not action.target:
            return False, "actor 또는 target 없음.", []
        r = use_item(actor, action.target)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.OFFER_TO_STONE:
        if not actor or not action.target:
            return False, "actor 또는 target 없음.", []
        r = offer_to_stone(actor, action.target, world)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.ENTER_RIFT:
        if not action.target:
            return False, "target rift 없음.", []
        r = enter_rift(party_list, world, action.target)
        if r.success:
            # ★ F7: location 본격 변경 — RIFT realm + canonical rift_id
            canonical = _resolve_rift_id(action.target) or action.target
            location.realm = Realm.RIFT
            location.rift_id = canonical
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.EXIT_RIFT:
        if not action.target:
            return False, "target rift 없음.", []
        r = exit_rift(party_list, world, action.target)
        if r.success:
            # ★ F7: location 1층 복귀 — DUNGEON realm + rift_id 해제
            location.realm = Realm.DUNGEON
            location.rift_id = None
        return r.success, r.message, r.side_effects

    return False, f"unknown action: {action.action_type.value}", []


def _refresh_context(
    party: dict[str, Character],
    world: WorldState,
    location: Location,
    base_ctx: dict[str, Any] | None,
    active_encounters: list[Encounter] | None = None,
    current_turn: int = 0,
) -> dict[str, Any]:
    """매 턴 LLM 호출 전 ctx의 동적 필드를 현재 state로 갱신.

    본 commit (★ A. encounter 보강):
    - active_encounters의 spawned_at_turn / ttl_remaining 본격 출력
    - TTL 만료 검증은 caller (★ runner.run)이 처리
    """
    ctx: dict[str, Any] = dict(base_ctx) if base_ctx else {}

    chars_ctx = dict(ctx.get("v2_characters") or {})
    for name, c in party.items():
        existing = dict(chars_ctx.get(name) or {})
        existing.update(
            {
                "race": c.race.value,
                "hp": c.hp,
                "hp_max": c.hp_max,
                "physical": c.physical,
                "mental": c.mental,
                "special": c.special,
                "strength": c.strength,
                "agility": c.agility,
                "has_active_light": c.has_active_light(),
                "essence_slots_used": c.essence_slots_used(),
                "essence_slot_max": c.essence_slot_max(),
            }
        )
        chars_ctx[name] = existing
    ctx["v2_characters"] = chars_ctx

    world_ctx = dict(ctx.get("v2_world_state") or {})
    world_ctx.update(
        {
            "hours_in_dungeon": world.hours_in_dungeon,
            "is_dark_zone": world.is_dark_zone,
            "active_rifts": list(world.active_rifts),
            "party_members": list(world.party_members),
        }
    )
    ctx["v2_world_state"] = world_ctx

    loc_ctx = dict(ctx.get("v2_initial_location") or {})
    loc_ctx.update(
        {
            "realm": location.realm.value,
            "floor": location.floor,
            "sub_area": location.sub_area,
            "visibility_meters": location.visibility_meters,
            "has_light": location.has_light,
        }
    )
    ctx["v2_initial_location"] = loc_ctx

    # ★ C/A commit 본격: GM이 spawn한 encounters를 ctx에 통합
    # ★ A. encounter 보강: spawned_at_turn / ttl_remaining 추가
    ctx["active_encounters"] = [
        {
            "type": e.type.value,
            "name": e.name,
            "location": e.location,
            "description": e.description,
            "details": dict(e.details),
            "spawned_at_turn": e.spawned_at_turn,
            "ttl_remaining": max(
                0, e.ttl_turns - (current_turn - e.spawned_at_turn)
            ),
        }
        for e in (active_encounters or [])
    ]

    return ctx


def _check_end_condition(
    config: SimConfig,
    party: dict[str, Character],
    world: WorldState,
    completed_turns: int,
) -> str | None:
    """N턴 종료 조건 검증."""
    if completed_turns >= config.max_turns:
        return "max_turns"

    if config.stop_on_permadeath:
        for c in party.values():
            if c.is_player and not c.is_alive():
                return "permadeath"

    if world.hours_in_dungeon >= 168:
        return "time_limit_168h"

    return None


class SimRunner:
    """단순 오케스트레이터 (★ agent X).

    1턴 흐름:
    1. PlayerAgent → action 생성
    2. action → _execute_action → 13 ActionType 진짜 mutate
    3. TurnLog 누적
    4. 종료 조건 검증
    """

    def __init__(
        self,
        config: SimConfig,
        player_agent: MockPlayerAgent | PlayerAgent | None = None,
        gm_agent: MockSimGMAgent | SimGMAgent | None = None,
    ) -> None:
        self.config = config
        self.player_agent = player_agent or MockPlayerAgent()
        # ★ C commit: GM agent 주입 (★ default mock, real은 caller 지정)
        self.gm_agent = gm_agent or MockSimGMAgent()
        self._active_encounters: list[Encounter] = []

    def run_single_turn(
        self,
        turn_number: int,
        actor_name: str,
        party: dict[str, Character],
        world: WorldState,
        location: Location,
        game_context: dict[str, Any] | None = None,
    ) -> TurnLog:
        """단일 턴 진짜 실행 (★ 13 ActionType).

        ★ ctx의 동적 필드를 매 턴 현재 state로 새로 갱신
        (★ has_active_light / hp / essence_slots / hours / sub_area
        + active_encounters from GM).
        """
        actor = party.get(actor_name)
        if actor is None:
            raise ValueError(f"actor_name not in party: {actor_name}")

        hp_before = actor.hp
        ctx = _refresh_context(
            party,
            world,
            location,
            game_context,
            self._active_encounters,
            current_turn=turn_number,
        )

        response = self.player_agent.generate_action(actor_name, ctx)
        action = response.action

        success, message, side_effects = _execute_action(
            action, party, world, location
        )

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
        location: Location | None = None,
        game_context: dict[str, Any] | None = None,
    ) -> SimResult:
        """N턴 자동 시뮬 (★ 본 commit 3차 본격)."""
        if party is None or world is None or location is None:
            return SimResult(
                sim_id=f"sim_{self.config.scenario_id}",
                config_summary=self._config_summary(),
                total_turns=self.config.max_turns,
                completed_turns=0,
                end_reason="no_party_or_world_or_location",
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
        turn_logs: list[TurnLog] = []
        latency_total_seconds = 0.0
        gm_cost_total = 0.0

        # ★ A. encounter 보강: 시뮬 시작 시 history reset
        if hasattr(self.gm_agent, "reset_history"):
            self.gm_agent.reset_history()
        # ★ E commit: Player history도 reset (★ A.6 mirror)
        if hasattr(self.player_agent, "reset_history"):
            self.player_agent.reset_history()
        self._active_encounters = []

        # ★ H commit 본격: 시작 시 initial_hours 적용 (★ COMBAT phase 시작)
        # 기존 world.hours_in_dungeon이 더 작으면만 override (★ caller 선언적)
        initial = int(self.config.initial_hours_in_dungeon)
        if world.hours_in_dungeon < initial:
            world.hours_in_dungeon = initial

        # ★ G commit 본격: float 시간 누적기 (★ 0.1h 본격 보존)
        # WorldState.hours_in_dungeon은 int이지만 delta는 float
        # → 누적 후 int(buffer)로 sync
        hours_float = float(world.hours_in_dungeon)

        actor_names = list(party.keys())
        completed = 0
        end_reason = "max_turns"

        for turn_idx in range(self.config.max_turns):
            actor_name = actor_names[turn_idx % len(actor_names)]

            actor = party.get(actor_name)
            if actor is None or not actor.is_alive():
                continue

            current_turn = turn_idx + 1

            # ★ A. encounter 보강: TTL 만료 자동 제거
            self._active_encounters = [
                e
                for e in self._active_encounters
                if not e.is_expired(current_turn)
            ]

            # GM이 매 턴 encounter spawn (★ ctx 통합 + 직전 type tracking)
            gm_ctx = _refresh_context(
                party,
                world,
                location,
                game_context,
                self._active_encounters,
                current_turn=current_turn,
            )
            gm_response = self.gm_agent.generate_encounters(
                turn_number=current_turn,
                game_context=gm_ctx,
            )
            # ★ A. encounter 보강: 신규 encounter에 spawned_at_turn / TTL 부여
            new_encounters = [
                Encounter(
                    type=e.type,
                    name=e.name,
                    location=e.location,
                    description=e.description,
                    details=dict(e.details),
                    spawned_at_turn=current_turn,
                    ttl_turns=ENCOUNTER_TTL.get(e.type, 30),
                )
                for e in gm_response.encounters
            ]
            # 누적 (★ 직전 active + 신규)
            self._active_encounters.extend(new_encounters)
            gm_cost_total += gm_response.cost_usd

            log = self.run_single_turn(
                turn_number=turn_idx + 1,
                actor_name=actor_name,
                party=party,
                world=world,
                location=location,
                game_context=game_context,
            )
            turn_logs.append(log)
            completed += 1

            # ★ G commit 본격: time advancement 통합
            # ★ H commit 본격: time_scale 적용 (★ default 2.0 RIFT 도달)
            # 매 turn ActionType별 hours_delta × scale 본격 누적
            # turn_handler 내부 advance_time/rest 영향 X (★ 본 commit override)
            delta = action_hours_delta(
                log.action.action_type,
                time_scale=self.config.time_scale,
            )
            hours_float += delta
            world.hours_in_dungeon = int(hours_float)

            reason = _check_end_condition(self.config, party, world, completed)
            if reason is not None:
                end_reason = reason
                break

        latency_total_seconds = time.monotonic() - start_time

        final_hp = {name: c.hp for name, c in party.items()}
        essences_count = {
            name: c.essence_slots_used() for name, c in party.items()
        }

        # ★ A.6 본격: GM enforcement stats 수집 (★ F commit phase 추가)
        gm_retry = 0
        gm_fallback = 0
        gm_phase_mismatch = 0
        gm_stats = getattr(self.gm_agent, "enforcement_stats", None)
        if isinstance(gm_stats, dict):
            gm_retry = int(gm_stats.get("retry_count", 0))
            gm_fallback = int(gm_stats.get("fallback_count", 0))
            gm_phase_mismatch = int(gm_stats.get("phase_mismatch_count", 0))

        # ★ E commit 본격: Player enforcement stats 수집 (A.6 mirror)
        player_retry = 0
        player_fallback = 0
        player_stats = getattr(self.player_agent, "enforcement_stats", None)
        if isinstance(player_stats, dict):
            player_retry = int(player_stats.get("retry_count", 0))
            player_fallback = int(player_stats.get("fallback_count", 0))

        return SimResult(
            sim_id=f"sim_{self.config.scenario_id}",
            config_summary=self._config_summary(),
            total_turns=self.config.max_turns,
            completed_turns=completed,
            turn_logs=turn_logs,
            end_reason=end_reason,
            final_hp_by_actor=final_hp,
            essences_absorbed_by_actor=essences_count,
            final_hours_in_dungeon=world.hours_in_dungeon,
            total_latency_seconds=latency_total_seconds,
            total_gm_llm_cost=gm_cost_total,
            gm_retry_count=gm_retry,
            gm_fallback_count=gm_fallback,
            gm_phase_mismatch_count=gm_phase_mismatch,
            player_retry_count=player_retry,
            player_fallback_count=player_fallback,
        )

    def _config_summary(self) -> str:
        return (
            f"max_turns={self.config.max_turns}, "
            f"player={self.config.player_llm_model}, "
            f"gm={self.config.gm_llm_model}"
        )
