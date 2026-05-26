"""Tier 2 state API (★ Phase 7a + 7j + 9.18-a).

본 router 본격:
- GET /api/v2/state — 현재 (party + world + location) JSON 본격
- GET /api/v2/state/recent_actions — 최근 N 행동 본격
- POST /api/v2/state/reset — 새 본격 default 본격
- POST /api/v2/action — execute (★ Phase 7j) + encounter wire (★ Phase 9.18-a)

본격 본질:
- singleton holder (★ 본격 단순 — 후속 session-aware 본격)
- default party/world/location (★ E2E 본격 패턴 동일):
  투르윈 (바바리안) + 실렌 (요정), 1층 진입점 DUNGEON
- recent_actions 본격 빈 list (★ 본 commit /action 시 본격 append)

Phase 9.18-a 본격 (★ §E fix from 30턴 playthrough):
- _V2StateHolder.active_encounters 필드
- _V2StateHolder._sim_gm_agent lazy init (★ 9B Q3 / 8083)
- post_action 본격 SimGMAgent.generate_encounters 호출 (★ 던전 한정)
- side_effect handlers (★ encounter_consumed / trigger_encounter_after_rest /
  essence_spawn — sim_runner pattern reuse)
- ActionResponse.encounters 필드

frontend 본격 (Phase 7b 이하 + 본 commit).
"""

from __future__ import annotations

import logging
import random
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.llm.local_client import get_qwen35_9b_q3, get_qwen36_27b_q3
from service.game.gm_agent import GMAgent
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.state_v2_serialize import game_state_v2_to_dict
from service.sim.sim_gm_agent import SimGMAgent
from service.sim.sim_runner import (
    _BOSS_REWARD_ESSENCE_LABEL,
    _execute_action,
    _generate_encounter_after_rest,
    _refresh_context,
)
from service.sim.types import (
    ENCOUNTER_TTL,
    Encounter,
    EncounterType,
    PlayerAction,
    PlayerActionType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["tier2-state"])


# ─── singleton holder (★ 단순, 후속 session 본격) ───


class _V2StateHolder:
    """본격 in-process (party, world, location, recent_actions) holder.

    Phase 9.18-a 본격 확장 (★ encounter wire):
    - active_encounters: GM 본격 spawn 본격 본격 — TTL 본격 자연 소멸
    - _sim_gm_agent: lazy init (★ 9B Q3 / 8083, encounter generator 한정)
    """

    def __init__(self) -> None:
        self.party: dict[str, Character] = {}
        self.world: WorldState = WorldState()
        self.location: Location = Location(realm=Realm.DUNGEON)
        self.recent_actions: list[dict[str, Any]] = []
        self.turn: int = 0
        # ★ Phase 9.18-a — encounter wire
        self.active_encounters: list[Encounter] = []
        self._sim_gm_agent: SimGMAgent | None = None
        # ★ Phase 9.18-c — V2 narrative (★ 27B SGLang FP8 + MTP / 8081)
        self._gm_narrator: GMAgent | None = None
        self._init_default()

    def _init_default(self) -> None:
        """E2E 패턴 동일 default — 투르윈 + 실렌, 1층 진입점."""
        self.party = {
            "투르윈": Character(
                name="투르윈",
                race=Race.BARBARIAN,
                hp=150,
                hp_max=150,
                physical=14,
                strength=16,
                bone_strength=12,
                is_player=True,
            ),
            "실렌": Character(
                name="실렌",
                race=Race.FAERIE,
                hp=90,
                hp_max=90,
                soul_power=60,
                soul_power_max=60,
            ),
        }
        self.world = WorldState(party_members=["투르윈", "실렌"])
        self.location = Location(
            realm=Realm.DUNGEON,
            floor=1,
            sub_area="진입점",
            visibility_meters=10,
            has_light=False,
        )
        self.recent_actions = []
        self.turn = 0
        # ★ Phase 9.18-a — encounter state reset (★ SimGMAgent instance 본격 보존)
        self.active_encounters = []

    def reset(self) -> None:
        """default 본격 재초기화 (★ SimGMAgent instance 본격 본격 본격)."""
        self._init_default()

    def get_sim_gm_agent(self) -> SimGMAgent:
        """SimGMAgent lazy init — 9B Q3 (port 8083) for encounter generator.

        ★ Phase 9.18-a — narrative 본격 본격 본격 (★ 본격 B.2b 본격).
        9B Q3 본격 38 tok/s × 400 max_tokens ≈ 5-10s/turn.
        """
        if self._sim_gm_agent is None:
            self._sim_gm_agent = SimGMAgent(
                llm_client=get_qwen35_9b_q3(),
            )
        return self._sim_gm_agent

    def get_gm_narrator(self) -> GMAgent:
        """GMAgent lazy init — 27B SGLang FP8 + MTP (port 8081) for V2 narrative.

        ★ Phase 9.18-c — §A 해소 본격.
        - verify_llm=None (★ V2 본격 verify mechanism 미정의)
        - Cross-Model 강제 본격 본격 본격 (★ GMAgent 본격 verify_llm None 본격 본격)
        - 27B Q3 ~14 tok/s × 400 max_tokens ≈ 23s/turn
        """
        if self._gm_narrator is None:
            self._gm_narrator = GMAgent(
                game_llm=get_qwen36_27b_q3(),
                verify_llm=None,
            )
        return self._gm_narrator


_HOLDER: _V2StateHolder | None = None


def get_holder() -> _V2StateHolder:
    """본격 singleton holder."""
    global _HOLDER
    if _HOLDER is None:
        _HOLDER = _V2StateHolder()
    return _HOLDER


# ─── Phase 9.18-a — encounter wire helpers ───


def _expire_encounters(
    active_encounters: list[Encounter],
    current_turn: int,
) -> list[str]:
    """TTL 만료 encounter 제거 (★ sim_runner pattern).

    sim_runner.run 본격 동일 — `is_expired(current_turn)` 본격 본격.

    Args:
        active_encounters: holder 본격 list (★ in-place mutation)
        current_turn: 현재 turn (★ TTL 계산 본격)

    Returns:
        제거된 encounter name list (★ trace 본격).
    """
    expired_names: list[str] = []
    remaining: list[Encounter] = []
    for e in active_encounters:
        if e.is_expired(current_turn):
            expired_names.append(e.name)
        else:
            remaining.append(e)
    active_encounters[:] = remaining
    return expired_names


def _serialize_encounter(enc: Encounter) -> dict[str, Any]:
    """Encounter → dict (★ ActionResponse.encounters JSON 본격)."""
    return {
        "name": enc.name,
        "type": enc.type.value,
        "location": enc.location,
        "description": enc.description,
        "spawned_at_turn": enc.spawned_at_turn,
        "ttl_turns": enc.ttl_turns,
        "ttl_remaining": max(
            0, enc.ttl_turns - (max(0, enc.spawned_at_turn) - enc.spawned_at_turn)
        ),
    }


def _handle_encounter_side_effects(
    side_effects: list[str],
    active_encounters: list[Encounter],
    location: Location,
    current_turn: int,
    rng: random.Random | None = None,
) -> None:
    """side_effect 처리 — sim_runner.run_single_turn pattern 재사용.

    본 commit (★ Phase 9.18-a):
    - encounter_consumed=NAME → active_encounters 본격 제거 (★ 9.17-c2/d 정합)
    - trigger_encounter_after_rest → REST encounter spawn (★ 9.17-e2 정합)
    - essence_spawn=COLOR → 떠다니는 정수 encounter (★ Phase 8 A3 정합)

    Mutation:
    - active_encounters (★ in-place)
    - side_effects (★ encounter_spawned_after_rest marker append)
    """
    rng = rng or random.Random()

    # encounter_consumed 본격 collect + 제거 (★ batch 본격 본격)
    consumed_names: set[str] = set()
    for eff in side_effects:
        if eff.startswith("encounter_consumed="):
            consumed_names.add(eff.split("=", 1)[1])
    if consumed_names:
        active_encounters[:] = [
            e for e in active_encounters if e.name not in consumed_names
        ]

    # trigger_encounter_after_rest 본격 REST encounter spawn
    if "trigger_encounter_after_rest" in side_effects:
        location_label = (
            location.rift_id
            or location.sub_area
            or "rest_site"
        )
        new_enc = _generate_encounter_after_rest(
            rng,
            location_label=location_label,
            turn_number=current_turn,
        )
        active_encounters.append(new_enc)
        side_effects.append(
            f"encounter_spawned_after_rest="
            f"{new_enc.name}:{new_enc.type.value}"
        )

    # essence_spawn 본격 boss 처치 본격 떠다니는 정수 (★ sim_runner pattern)
    for eff in side_effects:
        if eff.startswith("essence_spawn="):
            color = eff.split("=", 1)[1]
            essence_label = _BOSS_REWARD_ESSENCE_LABEL.get(
                color, f"{color} 정수"
            )
            active_encounters.append(
                Encounter(
                    type=EncounterType.ESSENCE,
                    name=essence_label,
                    location=(
                        location.rift_id or location.sub_area or ""
                    ),
                    description=(
                        "보스 처치 보상 — 떠다니는 정수 "
                        "(★ ABSORB_ESSENCE 본격)."
                    ),
                    spawned_at_turn=current_turn,
                    ttl_turns=ENCOUNTER_TTL.get(
                        EncounterType.ESSENCE, 30
                    ),
                )
            )


def _maybe_spawn_rift_encounters(holder: _V2StateHolder) -> None:
    """균열 내부 mechanical spawn — LLM 불필요, RiftSubAreaDef.monsters 사용."""
    if holder.active_encounters:
        return
    from service.canon.context import get_spawn_table
    from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS
    from service.sim.spawn_trigger import trigger_spawn

    spawn_table = get_spawn_table()
    if spawn_table is None:
        return

    new_encounters = trigger_spawn(
        location_name=holder.location.rift_id or "",
        location_type="rift",
        turn_count=holder.turn,
        last_spawn_turn=0,
        spawn_table=spawn_table,
        rift_sub_area=holder.location.rift_sub_area,
        rift_defs=FLOOR1_RIFT_DEFS,
    )
    for enc_dict in new_encounters:
        holder.active_encounters.append(
            Encounter(
                type=EncounterType.MONSTER,
                name=str(enc_dict.get("name", "몬스터")),
                location=holder.location.rift_sub_area or "",
                description="",
                details={},
                spawned_at_turn=holder.turn,
                ttl_turns=ENCOUNTER_TTL.get(EncounterType.MONSTER, 5),
            )
        )


def _maybe_spawn_encounters(holder: _V2StateHolder) -> None:
    """매 turn SimGMAgent.generate_encounters 호출 (★ 던전 한정).

    던전 외 (CITY / WILDERNESS 등) X — narrative 한정.
    균열 내부: mechanical spawn (_maybe_spawn_rift_encounters).
    LLM 실패 시 silent fallback (★ mechanical 계속 진행 보장).
    """
    if holder.location.realm != Realm.DUNGEON:
        return
    if holder.location.rift_id:
        _maybe_spawn_rift_encounters(holder)
        return
    try:
        gm_ctx = _refresh_context(
            holder.party,
            holder.world,
            holder.location,
            base_ctx=None,
            active_encounters=holder.active_encounters,
            current_turn=holder.turn,
        )
        gm_response = holder.get_sim_gm_agent().generate_encounters(
            turn_number=holder.turn,
            game_context=gm_ctx,
        )
        # 신규 encounters 본격 spawned_at_turn / TTL 부여 (★ sim_runner.run pattern)
        for e in gm_response.encounters:
            holder.active_encounters.append(
                Encounter(
                    type=e.type,
                    name=e.name,
                    location=e.location,
                    description=e.description,
                    details=dict(e.details),
                    spawned_at_turn=holder.turn,
                    ttl_turns=ENCOUNTER_TTL.get(e.type, 30),
                )
            )
    except Exception as exc:  # noqa: BLE001
        # LLM 실패 본격 silent — mechanical 본격 계속 진행
        logger.warning(
            "encounter generator failed (silent fallback): %s", exc
        )


# ─── Phase 9.18-c — V2 narrative wire helpers ───


def _serialize_char_min(c: Character) -> dict[str, Any]:
    """Character → narrative ctx 본격 minimal dict (★ noise 제거)."""
    return {
        "name": c.name,
        "race": c.race.value if hasattr(c.race, "value") else str(c.race),
        "hp": c.hp,
        "hp_max": c.hp_max,
        "level": c.level,
        "grade": c.grade,
        "class_type": c.class_type,
        "is_temporary": c.is_temporary,
        "has_active_light": c.has_active_light(),
        "essence_slots_used": c.essence_slots_used(),
    }


def _serialize_world_min(w: WorldState) -> dict[str, Any]:
    """WorldState → narrative ctx 본격 minimal dict."""
    return {
        "hours_in_dungeon": w.hours_in_dungeon,
        "month_number": w.month_number,
        "day_in_month": w.day_in_month,
        "active_rifts": list(w.active_rifts),
        "is_dark_zone": w.is_dark_zone,
    }


def _serialize_location_min(loc: Location) -> dict[str, Any]:
    """Location → narrative ctx 본격 minimal dict."""
    return {
        "realm": loc.realm.value if loc.realm else None,
        "floor": loc.floor,
        "sub_area": loc.sub_area,
        "rift_id": loc.rift_id,
        "rift_sub_area": loc.rift_sub_area,
        "has_light": loc.has_light,
        "visibility_meters": loc.visibility_meters,
    }


def _build_v2_ctx(holder: _V2StateHolder) -> dict[str, Any]:
    """V2 state → _gm_system_prompt ctx (★ Phase 9.18-c).

    V1 build_game_context 본격 본격 본격 — V2 native default Plan 본격 + V2 state.
    _gm_system_prompt required fields:
    - work_name / work_genre / world_setting / world_tone / world_rules
    - main_character_name / main_character_role / supporting_characters
    - current_location / current_turn
    - language / character_response
    - v2_characters / v2_world_state / v2_initial_location / active_encounters
    """
    main_name = "투르윈"
    supporting = [
        {"name": n, "role": "동료"}
        for n in holder.party
        if n != main_name
    ]

    return {
        "work_name": "1층 미궁",
        "work_genre": "판타지",
        "world_setting": "라스카니아",
        "world_tone": "차분하고 신중한 톤",
        "world_rules": [
            "1층 어둠 본질",
            "한국어만",
            "격식체",
            "라스카니아 본문 정합 — 추측 사실 X",
        ],
        "main_character_name": main_name,
        "main_character_role": "주인공",
        "supporting_characters": supporting,
        "current_location": holder.location.sub_area or "진입점",
        "current_turn": holder.turn,
        "language": "ko",
        "character_response": True,
        # V2 fields (★ _gm_system_prompt 본격 본격 schema 정합)
        "v2_characters": {
            n: _serialize_char_min(c) for n, c in holder.party.items()
        },
        "v2_world_state": _serialize_world_min(holder.world),
        "v2_initial_location": _serialize_location_min(holder.location),
        "active_encounters": [
            _serialize_encounter(e) for e in holder.active_encounters
        ],
    }


def _maybe_narrate(
    holder: _V2StateHolder,
    action: PlayerAction,
    result_message: str,
    result_side_effects: list[str],
    success: bool,
) -> str | None:
    """27B Q3 narrative — silent fallback (★ Phase 9.18-c).

    Policy:
    - success=False → None (★ fail 본격 mechanical 본격 본격)
    - LLM 실패 → None + log warning (★ silent)
    - 정상 → 한국어 narrative text
    """
    if not success:
        return None
    try:
        ctx = _build_v2_ctx(holder)
        narrator = holder.get_gm_narrator()
        result = narrator.narrate_action_v2(
            action, result_message, result_side_effects, ctx
        )
        # 본격 fallback 본격 본격 result_message 본격 본격 본격 — 본격 본격 None 본격 본격
        if result == result_message:
            return None
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("narrate_action_v2 failed: %s", exc)
        return None


# ─── response models ───


class StateResponse(BaseModel):
    """현재 Tier 2 state 본격."""

    state: dict[str, Any] = Field(
        description="characters + world + location 본격 JSON-serializable dict"
    )
    turn: int = Field(description="현재 turn 본격")


class RecentActionsResponse(BaseModel):
    """최근 N 행동 본격."""

    actions: list[dict[str, Any]] = Field(description="최근 행동 list")
    count: int = Field(description="반환 본격 횟수")
    total: int = Field(description="전체 누적 횟수")


class ResetResponse(BaseModel):
    """reset 응답."""

    status: str = Field(description="'reset' 본격")
    turn: int = Field(description="reset 본격 turn (★ 0)")


# ─── endpoints ───


@router.get("/state", response_model=StateResponse)
async def get_current_state() -> StateResponse:
    """현재 Tier 2 GameState V2 본격 본격.

    응답 본격:
    - state.characters: party 본격 본격 Character V2 (★ HP/스탯/슬롯)
    - state.world: WorldState (★ active_rifts, hours_in_dungeon, party_members)
    - state.location: Location (★ realm/floor/sub_area/rift_id)
    - turn: 현재 turn
    """
    h = get_holder()
    return StateResponse(
        state=game_state_v2_to_dict(h.party, h.world, h.location),
        turn=h.turn,
    )


@router.get("/state/recent_actions", response_model=RecentActionsResponse)
async def get_recent_actions(n: int = 10) -> RecentActionsResponse:
    """최근 N 행동 본격.

    args:
        n: 1-100 본격 (★ default 10)
    """
    if n < 1 or n > 100:
        raise HTTPException(
            status_code=400,
            detail="n must be 1-100",
        )
    h = get_holder()
    sliced = h.recent_actions[-n:]
    # holder는 dict 본격 저장 — 본격 본격 그대로 본격
    return RecentActionsResponse(
        actions=list(sliced),
        count=len(sliced),
        total=len(h.recent_actions),
    )


@router.post("/state/reset", response_model=ResetResponse)
async def reset_state() -> ResetResponse:
    """state 본격 default 본격 재초기화."""
    h = get_holder()
    h.reset()
    return ResetResponse(status="reset", turn=h.turn)


# ─── Phase 7j: action endpoint ───


class ActionRequest(BaseModel):
    """Player action 본격 request (★ Phase 7j)."""

    action_type: str = Field(
        description="13 PlayerActionType (★ value 본격, e.g. 'attack', 'enter_rift')"
    )
    actor: str | None = Field(
        default=None,
        description="실행 캐릭터 이름 (★ 본격 X 시 첫 party member)",
    )
    target: str | None = Field(
        default=None,
        description="target (★ monster/rift_id/sub_area/essence 본격)",
    )
    rationale: str = Field(default="", description="선택 이유 (★ LLM 본격 분석용)")


class ActionResponse(BaseModel):
    """action 본격 response."""

    success: bool = Field(description="_execute_action 본격 성공")
    message: str = Field(description="결과 메시지 (★ turn_handler 본격)")
    side_effects: list[str] = Field(description="state side effects 본격")
    state: dict[str, Any] = Field(description="post-action state 본격")
    turn: int = Field(description="post-action turn 본격")
    # ★ Phase 9.18-a — active encounters (★ frontend 본격 NPC encounter 본격)
    encounters: list[dict[str, Any]] = Field(
        default_factory=list,
        description="active encounters after action (★ 9.17 시리즈 consumer trigger)",
    )
    # ★ Phase 9.18-c — V2 narrative (★ 27B SGLang FP8 + MTP / 8081)
    narrative: str | None = Field(
        default=None,
        description=(
            "한국어 narrative text (★ §A — frontend 본격 본격 본격 본격). "
            "None = success=False 본격 LLM 실패 본격 silent fallback "
            "(★ message 본격 본격 사용)."
        ),
    )


def _resolve_actor(holder: _V2StateHolder, actor: str | None) -> str:
    """actor 본격 — None 시 첫 party member 본격."""
    if actor and actor in holder.party:
        return actor
    if holder.party:
        return next(iter(holder.party.keys()))
    return ""


@router.post("/action", response_model=ActionResponse)
async def post_action(req: ActionRequest) -> ActionResponse:
    """Player action 본격 execute + state mutation (★ Phase 7j + 9.18-a).

    flow (★ Phase 9.18-a 본격 확장 — encounter wire):
    1. action_type 본격 PlayerActionType 본격 검증 (★ 400 unknown)
    2. PlayerAction 본격 build
    3. TTL 만료 encounter 제거 (★ holder.active_encounters)
    4. SimGMAgent.generate_encounters (★ 던전 한정, silent fallback)
    5. sim_runner._execute_action(...active_encounters=...)
    6. side_effect handlers (★ encounter_consumed/trigger/essence_spawn)
    7. holder.turn++, recent_actions 본격 append
    8. ActionResponse 본격 반환 (★ encounters 필드 포함)
    """
    # ★ PlayerActionType StrEnum 본격 — value 본격 lookup
    try:
        action_type = PlayerActionType(req.action_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action_type: {req.action_type}",
        ) from exc

    h = get_holder()
    actor_name = _resolve_actor(h, req.actor)
    if not actor_name:
        raise HTTPException(
            status_code=400,
            detail="No actor available (★ party empty)",
        )

    action = PlayerAction(
        action_type=action_type,
        actor_name=actor_name,
        target=req.target,
        rationale=req.rationale,
    )

    # ★ Phase 9.18-a — TTL 만료 cleanup (★ 매 turn 시작)
    _expire_encounters(h.active_encounters, h.turn)

    # ★ Phase 9.18-a — encounter generator (★ 던전 한정, silent fallback)
    _maybe_spawn_encounters(h)

    # ★ mechanical handler 본격 active_encounters 전달 (★ 9.17 본격 consumer)
    success, message, side_effects = _execute_action(
        action,
        h.party,
        h.world,
        h.location,
        active_encounters=h.active_encounters,
    )

    # ★ Phase 9.18-a — side_effect handlers (★ sim_runner pattern reuse)
    _handle_encounter_side_effects(
        side_effects,
        h.active_encounters,
        h.location,
        h.turn,
    )

    # ★ Phase 9.18-c — V2 narrative (★ 27B Q3, silent fallback)
    # success=False 본격 None / LLM 실패 본격 None (★ frontend message 본격 본격)
    narrative = _maybe_narrate(
        h, action, message, side_effects, success
    )

    # ★ recent_actions 본격 append (★ frontend recent_actions API 본격)
    h.turn += 1
    h.recent_actions.append(
        {
            "turn": h.turn,
            "actor": actor_name,
            "action_type": action_type.value,
            "target": req.target,
            "success": success,
            "message": message,
            "side_effects": side_effects,
        }
    )

    return ActionResponse(
        success=success,
        message=message,
        side_effects=side_effects,
        state=game_state_v2_to_dict(h.party, h.world, h.location),
        turn=h.turn,
        encounters=[
            _serialize_encounter(e) for e in h.active_encounters
        ],
        narrative=narrative,
    )
