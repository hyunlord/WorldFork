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

from service.game.floors.registry import get_current_floor_definition
from service.game.state_v2 import (
    Character,
    Location,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    _resolve_rift_id,
    absorb_floating_essence,
    activate_light,
    advance_time,
    apply_time_limit_village_return,
    check_party_defeated,
    check_time_limit,
    enter_next_floor,
    enter_rift,
    exchange_mage_stones,
    execute_attack,
    execute_dialogue,
    execute_enter_dungeon,
    execute_heal_at_temple,
    execute_library_search,
    execute_recruit_from_guild,
    execute_wait_in_village,
    exit_rift,
    exit_to_prev_floor,
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
    EncounterType,
    PlayerAction,
    PlayerActionType,
    SimConfig,
    SimResult,
    TurnLog,
    action_hours_delta,
)

# ★ Phase 8 A3 — RiftDef.essence_color → 떠다니는 정수 한국어 라벨.
# 보스 처치 보상 marker 'essence_spawn={color}' 본격 매핑.
_BOSS_REWARD_ESSENCE_LABEL: dict[str, str] = {
    "red": "핏빛 정수",     # 핏빛성채 (★ 칼날늑대 정수 alias)
    "blue": "회청색 정수",   # 빙하굴 (★ 레이스 정수 alias)
    "green": "녹색 정수",    # 녹색탄광 (★ 위치스램프 정수 alias)
    "yellow": "노란 정수",   # 강철의 묘 (★ 본격 매핑 없음 — 후속 정합)
}


def _world_snapshot(world: WorldState) -> dict[str, Any]:
    """A3 E2E trace용 WorldState 직렬화 (★ per-turn snapshot)."""
    boss = world.active_boss_encounter
    return {
        "hours_in_dungeon": world.hours_in_dungeon,
        "active_rifts": list(world.active_rifts),
        "defeated_bosses": list(world.defeated_bosses),
        "cleared_rifts": list(world.cleared_rifts),
        "active_boss_encounter": (
            None
            if boss is None
            else {
                "rift_id": boss.rift_id,
                "boss_id": boss.boss_id,
                "boss_name": boss.boss_name,
                "boss_grade": boss.boss_grade,
                "is_variant": boss.is_variant,
                "hp": boss.hp,
                "hp_max": boss.hp_max,
                "weakness_element": boss.weakness_element,
            }
        ),
        # ★ Phase 8 A4 — 1층 종료 mechanism trace 본격
        "simulation_status": world.simulation_status.value,
        "simulation_over_reason": world.simulation_over_reason,
        "simulation_over_turn": world.simulation_over_turn,
        # ★ Phase 8 B — first kill mechanism trace (★ 정렬 본격 결정적)
        "first_killed_species": sorted(world.first_killed_species),
        # ★ Phase 8 C / R4 — 인접 층 진입 / 최초 보너스 trace (★ generic)
        "floor_states": {
            str(n): {
                "floor_number": fs.floor_number,
                "entered": fs.entered,
                "entry_sub_area_from_prev": fs.entry_sub_area_from_prev,
                "current_sub_area": fs.current_sub_area,
                "returned_to_prev": fs.returned_to_prev,
            }
            for n, fs in sorted(world.floor_states.items())
        },
        "first_entry_parties": sorted(world.first_entry_parties),
    }


def _location_snapshot(location: Location) -> dict[str, Any]:
    """A3 E2E trace용 Location 직렬화."""
    return {
        "realm": location.realm.value,
        "floor": location.floor,
        "sub_area": location.sub_area,
        "rift_id": location.rift_id,
        "rift_sub_area": location.rift_sub_area,
        "rift_is_variant": location.rift_is_variant,
    }


def _action_to_turn_log(
    turn_number: int,
    action: PlayerAction,
    party: dict[str, Character],
    world: WorldState,
    success: bool,
    message: str,
    side_effects: list[str],
    hp_before: int,
    location: Location | None = None,
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
        world_snapshot=_world_snapshot(world),
        location_snapshot=(
            _location_snapshot(location) if location is not None else None
        ),
    )


def _execute_action(
    action: PlayerAction,
    party: dict[str, Character],
    world: WorldState,
    location: Location,
    force_variant: bool | None = None,
) -> tuple[bool, str, list[str]]:
    """PlayerAction → turn_handler 매핑 (★ 13 ActionType 모두 mutate).

    본 commit 3차 본격: 모든 ActionType이 진짜 production 함수 호출.

    Phase 8 A3 E2E:
    - force_variant: SimConfig 본격 ENTER_RIFT 변종 강제 (★ True/False/None).
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
        # ★ Phase 8 A1 — RIFT 내부 이동 성공 시 rift_sub_area 본격 갱신
        if r.success and location.realm == Realm.RIFT:
            for eff in r.side_effects:
                if eff.startswith("target_rift_sub_area="):
                    location.rift_sub_area = eff.split("=", 1)[1]
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.ATTACK:
        if not actor or not action.target:
            return False, "actor 또는 target 없음.", []
        # ★ Phase 8 A3 — attack_element 본격 (보스 약점 2배 enabler)
        attack_element_val = action.metadata.get("attack_element")
        attack_element = (
            attack_element_val if isinstance(attack_element_val, str) else None
        )
        r = execute_attack(
            actor, action.target, party_list, world, attack_element
        )
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
        # ★ Phase 8 A3 E2E — config.force_variant 본격 enter_rift 전달
        r = enter_rift(
            party_list, world, action.target, force_variant=force_variant
        )
        if r.success:
            # ★ F7: location 본격 변경 — RIFT realm + canonical rift_id
            # ★ Phase 8 A1: rift_sub_area 본격 entrance_id 전파
            # ★ Phase 8 A2: rift_is_variant 본격 enter_rift 결정 전파
            canonical = _resolve_rift_id(action.target) or action.target
            location.realm = Realm.RIFT
            location.rift_id = canonical
            for eff in r.side_effects:
                if eff.startswith("target_rift_sub_area="):
                    location.rift_sub_area = eff.split("=", 1)[1]
                elif eff.startswith("target_rift_is_variant="):
                    location.rift_is_variant = (
                        eff.split("=", 1)[1] == "True"
                    )
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.EXIT_RIFT:
        if not action.target:
            return False, "target rift 없음.", []
        r = exit_rift(party_list, world, action.target)
        if r.success:
            # ★ F7: location 1층 복귀 — DUNGEON realm + rift_id 해제
            # ★ Phase 8 A1: rift_sub_area / rift_is_variant 본격 reset
            location.realm = Realm.DUNGEON
            location.rift_id = None
            location.rift_sub_area = None
            location.rift_is_variant = False
        return r.success, r.message, r.side_effects

    # ★ Phase 8 C — 2층 진입 / 1층 복귀
    if action.action_type == PlayerActionType.ENTER_NEXT_FLOOR:
        r = enter_next_floor(party_list, world, location)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.EXIT_TO_PREV_FLOOR:
        r = exit_to_prev_floor(party_list, world, location)
        return r.success, r.message, r.side_effects

    # ★ Phase 8 exchange — 환전소 본격 마석 → 스톤
    if action.action_type == PlayerActionType.EXCHANGE_MAGE_STONES:
        if not actor:
            return False, "actor 없음.", []
        r = exchange_mage_stones(actor, location)
        return r.success, r.message, r.side_effects

    # ★ Phase 9 — 마을 turn loop (★ TIME_LIMIT_REACHED status 본격 본격)
    # 본 commit option 3 additive — sim_runner _check_end_condition 본격
    # TIME_LIMIT_REACHED 본격 종료 X 본격 본격 본격 (★ 본격 후속 commit 본격).
    # 본 dispatch는 직접 caller (★ test / 후속 turn loop runner) 본격 호출용.
    if action.action_type == PlayerActionType.WAIT_IN_VILLAGE:
        r = execute_wait_in_village(action.actor_name, party_list, world)
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.ENTER_DUNGEON:
        r = execute_enter_dungeon(
            action.actor_name, party_list, world, location
        )
        return r.success, r.message, r.side_effects

    # ★ Phase 9.5 — 삼신교 신전 부상 치료 (★ 268/55/72화 정합)
    if action.action_type == PlayerActionType.HEAL_AT_TEMPLE:
        r = execute_heal_at_temple(
            action.actor_name, party_list, world, location
        )
        return r.success, r.message, r.side_effects

    # ★ Phase 9.7 — NPC 대화 + 도서관 서적 탐지 (★ 19화 정합)
    if action.action_type == PlayerActionType.DIALOGUE:
        r = execute_dialogue(
            action.actor_name, action.target, party_list, world, location
        )
        return r.success, r.message, r.side_effects

    if action.action_type == PlayerActionType.LIBRARY_SEARCH:
        r = execute_library_search(
            action.actor_name, action.target, party_list, world, location
        )
        return r.success, r.message, r.side_effects

    # ★ Phase 9.9-a — 길드 모집 minimal
    if action.action_type == PlayerActionType.RECRUIT_FROM_GUILD:
        r = execute_recruit_from_guild(
            action.actor_name, party_list, world, location
        )
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
                # ★ Phase 8 B — 레벨 + 경험치
                "level": c.level,
                "experience": c.experience,
                # ★ Phase 9.3 — 부상 (LLM narrative 본격)
                "injuries": [
                    {
                        "severity": inj.severity,
                        "body_part": inj.body_part,
                        "recovery_days": inj.recovery_days,
                        "scar": inj.scar,
                    }
                    for inj in c.injuries
                ],
                # ★ Phase 9.6 — 영구 흉터 (★ 25화 본문 정합)
                "scars": [
                    {
                        "body_part": s.body_part,
                        "origin_severity": s.origin_severity,
                    }
                    for s in c.scars
                ],
            }
        )
        chars_ctx[name] = existing
    ctx["v2_characters"] = chars_ctx

    world_ctx = dict(ctx.get("v2_world_state") or {})
    # ★ Phase 8 A3 — 보스 / 클리어 state 직렬화
    active_boss = world.active_boss_encounter
    boss_ctx: dict[str, Any] | None = None
    if active_boss is not None:
        boss_ctx = {
            "rift_id": active_boss.rift_id,
            "boss_id": active_boss.boss_id,
            "boss_name": active_boss.boss_name,
            "boss_grade": active_boss.boss_grade,
            "is_variant": active_boss.is_variant,
            "hp": active_boss.hp,
            "hp_max": active_boss.hp_max,
            "weakness_element": active_boss.weakness_element,
            "weakness_strategy": active_boss.weakness_strategy,
        }
    world_ctx.update(
        {
            "hours_in_dungeon": world.hours_in_dungeon,
            "is_dark_zone": world.is_dark_zone,
            "active_rifts": list(world.active_rifts),
            "party_members": list(world.party_members),
            "defeated_bosses": list(world.defeated_bosses),
            "cleared_rifts": list(world.cleared_rifts),
            "active_boss_encounter": boss_ctx,
            # ★ Phase 8 A4 — 1층 종료 mechanism (GM prompt 본격)
            "simulation_status": world.simulation_status.value,
            "simulation_over_reason": world.simulation_over_reason,
            "simulation_over_turn": world.simulation_over_turn,
            # ★ Phase 8 B — first kill species (★ GM 본격 본격 노출)
            "first_killed_species": sorted(world.first_killed_species),
            # ★ Phase 8 C / R4 — 인접 층 진입 state (★ GM prompt 본격, generic)
            "entered_floors": sorted(world.floor_states.keys()),
            "first_entry_parties": sorted(world.first_entry_parties),
            # ★ Phase 9.7 — NPC 호감도 (★ DIALOGUE / LIBRARY_SEARCH 본격)
            "npc_affinities": dict(world.npc_affinities),
            # ★ Phase 9.9-a — 파티 정원 (★ RECRUIT_FROM_GUILD 본격)
            "max_party_members": world.max_party_members,
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
            # ★ Phase 8 A3 — RIFT 내부 매 턴 refresh (A1/A2 본격 location 본격)
            "rift_id": location.rift_id,
            "rift_sub_area": location.rift_sub_area,
            "rift_is_variant": location.rift_is_variant,
            # ★ Phase 8 village mech — realm=CITY 시 도시 식별자 (★ a-2/a-3 본격)
            "city_id": location.city_id,
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
    """N턴 종료 조건 검증.

    Phase 8 A4: world.simulation_status 본격 state-level 종료를 read.
    호출자가 turn 직후 check_time_limit/check_party_defeated를 호출해 두면
    상태 enum이 곧 종료 사유와 매핑된다.
    """
    if completed_turns >= config.max_turns:
        return "max_turns"

    if config.stop_on_permadeath:
        for c in party.values():
            if c.is_player and not c.is_alive():
                return "permadeath"

    # ★ Phase 9 sim-cycle — TIME_LIMIT_REACHED 본격 sim 종료 X.
    # 마을 turn loop 계속 (★ WAIT_IN_VILLAGE / ENTER_DUNGEON 가능):
    # 1층 168h → check_time_limit → TIME_LIMIT_REACHED + 마을 mutation →
    # WAIT_IN_VILLAGE × 30 → 매월 1일 ENTER_DUNGEON → ACTIVE 재진입.
    # 본인 답: 전멸(PARTY_DEFEATED)만 게임 오버.
    # FLOOR_TRANSITION (★ Phase 8 C) 본격 위치 marker (★ 1층 vs 2층) — 종료 X.
    if world.simulation_status == SimulationStatus.PARTY_DEFEATED:
        return "party_defeated"

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
            action, party, world, location, self.config.force_variant
        )

        # ★ Phase 8 A3 — execute_attack 보스 처치 시 'essence_spawn={color}'
        # marker 발생 → active_encounters에 떠다니는 정수 Encounter push.
        # color → 한국어 색명 매핑 (★ floor1_rifts RiftDef.essence_color).
        for eff in side_effects:
            if eff.startswith("essence_spawn="):
                color = eff.split("=", 1)[1]
                essence_label = _BOSS_REWARD_ESSENCE_LABEL.get(
                    color, f"{color} 정수"
                )
                self._active_encounters.append(
                    Encounter(
                        type=EncounterType.ESSENCE,
                        name=essence_label,
                        location=location.rift_id or location.sub_area or "",
                        description=(
                            "보스 처치 보상 — 떠다니는 정수 "
                            "(★ ABSORB_ESSENCE 본격)."
                        ),
                        spawned_at_turn=turn_number,
                        ttl_turns=ENCOUNTER_TTL.get(EncounterType.ESSENCE, 30),
                    )
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
            location=location,
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

        # ★ R1/R2 — 본 sim 본격 floor_def (★ FLOOR_REGISTRY 본격 location.floor).
        # check_time_limit 본격 floor_def.base_time_hours 본격 전달.
        # R2: get_floor1_definition() → get_current_floor_definition(location)
        # (★ 2층 본격 본격 자동 정합).
        floor_def = get_current_floor_definition(location)

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

            # ★ Phase 8 A4 — 1층 종료 조건 state mutate
            # (★ time 누적/HP mutate 직후 호출 → _check_end_condition source).
            # ★ R1: floor_def.base_time_hours 본격 전달 (★ module 상수 제거 후 단일 source).
            time_limit_triggered = check_time_limit(
                world,
                time_limit_hours=floor_def.base_time_hours,
                turn_number=current_turn,
            )
            check_party_defeated(
                list(party.values()), world, turn_number=current_turn
            )

            # ★ Phase 8 a-3 — TIME_LIMIT_REACHED 시 마을 자동 귀환 location mutation
            # (★ docs/village_spec.md §7.1 정합: 라프도니아 7구역 중앙 광장).
            # PARTY_DEFEATED 본격 본격 X (★ 사망 = 미궁 연료, 본인 답).
            if time_limit_triggered:
                apply_time_limit_village_return(location)

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
