"""Phase D — POST /api/v2/freeform_action endpoint.

Phase D step 4: session_id 기반 서버사이드 state holder.
Phase D step 3: intent path → dispatch_action (deterministic handler).
fallback path: 27B free-form (변경 없음).
"""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException

from service.api.schemas.freeform_action import (
    FreeformActionRequest,
    FreeformActionResponse,
    SessionSummary,
    StateDelta,
)
from service.canon.context import get_canon_facts, get_spawn_table
from service.sim.action_context import ActionContext, ActionResult
from service.sim.action_handlers import dispatch_action
from service.sim.dungeon_clock import RETURN_TIME_ADVANCE_HOURS, check_warning, should_force_return
from service.sim.equipment import equipment_set_from_dict
from service.sim.freeform_handler import freeform_action
from service.sim.gm_narrator import GM_NARRATE_ACTIONS, compose_gm_narrative
from service.sim.intent_classifier import classify_intent
from service.sim.session_manager import SessionState, get_session_manager
from service.sim.spawn_trigger import determine_location_type, trigger_spawn
from service.sim.story_progression import (
    PHASE_LABEL,
    PHASE_WEAPON_CHOICE,
    advance_story,
    phase_suggestions,
)
from service.sim.types import PlayerActionType
from service.sim.weapon_choice import make_weapon_equipment, match_weapon_in_text

router = APIRouter(prefix="/api/v2", tags=["tier2-freeform"])

INTENT_THRESHOLD = 0.8


def _force_return_narrative() -> str:
    """강제 귀환 연출 — ep_0016 + ep_0036 본문 정합."""
    return (
        "「층계 폐쇄까지 1분 남았습니다.」\n\n"
        "빛이 눈앞을 뒤덮고, 그보다 옅은 빛이 얹어지며 시야가 돌아온다. "
        "나는 멍하니 하늘을 올려다보았다. 라스카니아 차원광장이다.\n\n"
        "「미궁이 폐쇄되었습니다.」\n"
        "「캐릭터가 라스카니아로 이동합니다.」"
    )


def _force_return_to_city(state: SessionState, undo_min: int = 0) -> None:
    """168h 도달 시 강제 귀환 — state 인플레이스 변경.

    - inventory / level / xp / absorbed_essences 유지 (ep_0016 정합)
    - status_effects 해제 (마을 안전)
    - encounters / hours_in_dungeon 초기화
    - floor_number → 0, location → 차원광장
    - time_elapsed += 1440min - undo_min — wiki 010 "다음날 정오"
      apply_result가 이미 더한 분량(undo_min)을 상쇄 후 24h 스킵만 적용
    """
    state.floor_number = 0
    state.location = "라스카니아 · 차원광장"
    state.encounters = []
    state.status_effects = []
    state.hours_in_dungeon = 0.0
    state.last_spawn_turn = -10
    state.time_elapsed += int(RETURN_TIME_ADVANCE_HOURS * 60) - undo_min


def _post_apply_dungeon_clock(
    state: SessionState,
    prev_hours: float,
    last_advance_min: int = 0,
) -> str | None:
    """dungeon clock 체크 — 강제 귀환 또는 경고 메시지 반환.

    강제 귀환 시 state를 인플레이스 변경하고 narrative를 반환.
    경고만 있으면 경고 메시지 반환.
    이상 없으면 None 반환.
    last_advance_min: apply_result가 이미 time_elapsed에 더한 분량 (force_return 시 상쇄).
    """
    floor = state.floor_number
    if floor < 1:
        return None

    new_hours = state.hours_in_dungeon

    if should_force_return(floor, new_hours):
        _force_return_to_city(state, undo_min=last_advance_min)
        return _force_return_narrative()

    warning = check_warning(floor, prev_hours, new_hours)
    if warning:
        return warning.message

    return None


def _build_tip_message(new_balance: int, prev_balance: int) -> str | None:
    """잔액 변동 시 「TIP」 시스템 메시지 (본문 정합 ep_0018)."""
    if new_balance == prev_balance:
        return None
    return (
        f"「TIP: 현재 캐릭터의 총 소지금은 {new_balance:,}스톤입니다."
        " 이를 사용해 캐릭터의 종합 전투 지수를 올려 보세요!」"
    )


def _post_apply_spawn(state: SessionState) -> None:
    """action 적용 후 encounter auto spawn check — state 인플레이스 갱신."""
    if state.encounters:
        return
    spawn_table = get_spawn_table()
    if spawn_table is None:
        return
    facts = get_canon_facts()
    loc_type = determine_location_type(state.location, facts)
    rift_defs = None
    if state.rift_sub_area:
        from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS
        rift_defs = FLOOR1_RIFT_DEFS
    new_encounters = trigger_spawn(
        location_name=state.location,
        location_type=loc_type,
        turn_count=state.turn_count,
        last_spawn_turn=state.last_spawn_turn,
        spawn_table=spawn_table,
        rift_sub_area=state.rift_sub_area,
        rift_defs=rift_defs,
    )
    if new_encounters:
        state.encounters = new_encounters
        state.last_spawn_turn = state.turn_count


def _build_context(req: FreeformActionRequest, state: SessionState | None) -> ActionContext:
    """세션 상태 우선, 없으면 inline request 값 사용."""
    if state is not None:
        eq_set = equipment_set_from_dict(state.equipment) if state.equipment else None
        return ActionContext(
            current_hp=state.current_hp,
            max_hp=state.max_hp,
            inventory=list(state.inventory),
            location=state.location,
            encounters=list(state.encounters),
            user_input=req.user_input,
            status_effects=list(state.status_effects),
            equipment=eq_set,
            player_level=state.player_level,
            player_xp=state.player_xp,
            max_essences=state.max_essences,
            soul_power=state.soul_power,
            absorbed_essences=list(state.absorbed_essences),
            defeated_monster_types=list(state.defeated_monster_types),
            floor_number=state.floor_number,
            rift_id=state.rift_id,
            rift_sub_area=state.rift_sub_area,
            rift_is_variant=state.rift_is_variant,
            portal_first_opened=state.portal_first_opened,
            race=state.race,
            player_sensitivities=dict(state.player_sensitivities),
        )
    return ActionContext(
        current_hp=req.current_hp,
        max_hp=req.max_hp,
        inventory=list(req.inventory),
        location=req.location,
        encounters=list(req.encounters),
        user_input=req.user_input,
    )


def _session_summary(state: SessionState) -> SessionSummary:
    return SessionSummary(
        current_hp=state.current_hp,
        max_hp=state.max_hp,
        inventory=state.inventory,
        location=state.location,
        turn_count=state.turn_count,
    )


def _suggest_actions(state: SessionState | None) -> list[str]:
    """현재 상황 정합 추천 행동 3항목 (frontend 추천 버튼).

    ★ encounters 정합 — 실재 대상만 추천(정적 추천 X). 적대 → 전투,
    비적대 NPC 존재 → 그 NPC에게 말 걸기, 아무도 없으면 탐색 위주.
    이로써 '부족장에게 말을 건다 → 대화할 상대가 없다' 막다른 응답 해소.
    """
    if state is None:
        return ["주변을 살핀다", "앞으로 나아간다", "잠시 쉰다"]

    hostiles = [e for e in state.encounters if e.get("hostile")]
    npcs = [e for e in state.encounters if e.get("hostile") is False]
    npc_name = str(npcs[0].get("name") or "상대") if npcs else None

    # ★ 적대 조우는 전투 우선 (단계 무관)
    if hostiles:
        return ["적을 공격한다", "대화를 시도한다", "뒤로 물러선다"]

    # ★ 스토리 단계 기반 동적 추천 (단계 진전 유도 — 정적 반복 해소)
    phase_sugg = phase_suggestions(state.story_phase, npc_name)
    if phase_sugg is not None:
        return phase_sugg
    if npcs:
        npc_name = str(npcs[0].get("name") or "상대")
        tail = "무기를 점검한다" if state.floor_number < 1 else "더 깊이 나아간다"
        return [f"{npc_name}에게 말을 건다", "주변을 둘러본다", tail]
    if state.floor_number < 1:
        return ["주변을 둘러본다", "무기를 점검한다", "길을 나선다"]
    return ["주변을 살핀다", "더 깊이 나아간다", "잠시 휴식한다"]


async def _handle_weapon_choice(
    req: FreeformActionRequest,
    session_state: SessionState,
    chosen: str,
    ctx: ActionContext,
) -> FreeformActionResponse:
    """성인식 무기 선택 — 장착(element) + chosen_weapon flag + departure 전진.

    Rule Engine이 하드 상태(장비/인벤/단계)를 확정하고, GM이 선택 장면을 서술한다.
    """
    mgr = get_session_manager()
    # inventory 반영 → turn 기록(히스토리) 후 장비/단계 확정.
    add = [chosen] if chosen not in session_state.inventory else []
    fact = f"성년의 증표로 {chosen}을(를) 골라 손에 쥐었다"

    recent = await mgr.get_recent_turns(session_state.session_id)
    npc = next(
        (str(e.get("name")) for e in ctx.encounters if e.get("hostile") is False),
        "부족장",
    )
    new_phase, new_flags = advance_story(
        session_state.story_phase,
        session_state.story_flags,
        PlayerActionType.EQUIP,
        npc,
        chose_weapon=True,
    )
    gm_text = await asyncio.to_thread(
        compose_gm_narrative,
        req.user_input,
        fact,
        ctx.location,
        npc,
        recent,
        "",
        PHASE_LABEL.get(new_phase, ""),
    )
    narrative = gm_text or f"나는 {chosen}을(를) 손에 쥐었다. 성년의 증표다."

    result = ActionResult(narrative=narrative, inventory_add=add, time_advance=1)
    session_state = await mgr.apply_result(
        session_state.session_id, result, user_input=req.user_input,
        resolved_path="intent",
    )
    # 장비/단계 확정 (apply_result 이후 — 한 번 더 저장)
    session_state.equipment["weapon"] = make_weapon_equipment(chosen)
    session_state.story_phase = new_phase
    session_state.story_flags = new_flags
    await mgr.save_state(session_state)

    return FreeformActionResponse(
        resolved_path="intent",
        matched_action="equip",
        confidence=1.0,
        narrative=narrative,
        state_delta=StateDelta(inventory_add=add, time_advance=1),
        session_id=session_state.session_id,
        session_state=_session_summary(session_state),
        suggested_actions=_suggest_actions(session_state),
    )


@router.post("/freeform_action", response_model=FreeformActionResponse)
async def freeform_action_endpoint(
    req: FreeformActionRequest,
) -> FreeformActionResponse:
    """자연어 input → intent dispatch 또는 free-form fallback.

    Step 1: 9B classifier 호출
    Step 2: confidence ≥ INTENT_THRESHOLD + matched_action 존재 시
            ActionContext 빌드 → dispatch_action → StateDelta 반환
    Step 3: 위 미충족 시 27B free-form fallback
    Step 4: session_id 존재 시 결과를 세션 상태에 반영
    """
    # 세션 조회 (session_id 있을 때만)
    session_state: SessionState | None = None
    mgr = get_session_manager()

    if req.session_id is not None:
        session_state = await mgr.get_session(req.session_id)
        if session_state is None:
            # session_id 제공했지만 없으면 자동 생성
            session_state = await mgr.create_session(
                inventory=list(req.inventory),
                location=req.location or None,
                current_hp=req.current_hp,
                max_hp=req.max_hp,
            )

    try:
        intent = await asyncio.to_thread(classify_intent, req.user_input)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"intent classifier failed: {exc}",
        ) from exc

    ctx = _build_context(req, session_state)
    ctx.extracted_entities = intent.entities

    # ★ 성인식 무기 선택 (게임 엔진 3단계 — ep_0002 고증): weapon_choice 단계에서
    #   플레이어가 무기를 고르면 장착(element 정합) + departure 전진. intent 분류와
    #   무관하게 단계+무기명으로 직접 처리(부족장 '골라라' → 게임 내 선택).
    if (
        session_state is not None
        and session_state.story_phase == PHASE_WEAPON_CHOICE
    ):
        chosen = match_weapon_in_text(req.user_input)
        if chosen is not None:
            return await _handle_weapon_choice(req, session_state, chosen, ctx)

    if (
        intent.matched_action is not None
        and intent.confidence >= INTENT_THRESHOLD
    ):
        try:
            action_type = PlayerActionType(intent.matched_action)
        except ValueError:
            pass
        else:
            try:
                result = await dispatch_action(action_type, ctx)
            except Exception as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"action handler failed: {exc}",
                ) from exc

            # ★ GM 서사 레이어 (재설계 1단계) — 서사형 action은 handler가 수치를
            #   확정하고, GM이 누적 히스토리 맥락으로 narrative를 주도한다.
            #   같은 행동도 맥락 따라 다른 전개 → intent template 반복 해소.
            #   GM 실패 시 handler template narrative로 fallback.
            npc_name = next(
                (
                    str(e.get("name"))
                    for e in ctx.encounters
                    if e.get("hostile") is False
                ),
                None,
            )
            if session_state is not None and action_type in GM_NARRATE_ACTIONS:
                recent = await mgr.get_recent_turns(session_state.session_id)
                surroundings = npc_name or "특이사항 없음"
                gm_text = await asyncio.to_thread(
                    compose_gm_narrative,
                    req.user_input,
                    result.narrative,
                    ctx.location,
                    surroundings,
                    recent,
                    "",
                    PHASE_LABEL.get(session_state.story_phase, ""),
                )
                if gm_text:
                    result.narrative = gm_text

            # ★ 스토리 전진 (Rule Engine — 07 정합): 행동 결과로 단계/플래그 전진.
            #   GM은 읽기만, 여기서만 세계 상태를 바꾼다.
            if session_state is not None:
                new_phase, new_flags = advance_story(
                    session_state.story_phase,
                    session_state.story_flags,
                    action_type,
                    npc_name,
                )
                session_state.story_phase = new_phase
                session_state.story_flags = new_flags

            resolved_path: Literal["intent", "fallback"] = "intent"
            final_narrative = result.narrative
            if session_state is not None:
                prev_hours = session_state.hours_in_dungeon
                prev_stone = session_state.stone_balance
                session_state = await mgr.apply_result(
                    session_state.session_id,
                    result,
                    user_input=req.user_input,
                    resolved_path=resolved_path,
                )
                _post_apply_spawn(session_state)
                clock_msg = _post_apply_dungeon_clock(
                    session_state,
                    prev_hours,
                    last_advance_min=int(round(result.time_advance * 60)),
                )
                tip_msg = _build_tip_message(session_state.stone_balance, prev_stone)
                needs_save = False
                if clock_msg:
                    final_narrative = f"{final_narrative}\n\n{clock_msg}"
                    needs_save = True
                if tip_msg:
                    final_narrative = f"{final_narrative}\n\n{tip_msg}"
                    needs_save = True
                if needs_save:
                    await mgr.save_state(session_state)

            return FreeformActionResponse(
                resolved_path=resolved_path,
                matched_action=intent.matched_action,
                confidence=intent.confidence,
                narrative=final_narrative,
                action_success=result.success,
                fail_reason=result.fail_reason,
                state_delta=StateDelta(
                    hp_change=result.hp_change,
                    inventory_add=result.inventory_add,
                    inventory_remove=result.inventory_remove,
                    location=result.location,
                    time_advance=min(result.time_advance, 24),
                    affinity_changes=result.affinity_changes,
                    encounter_resolved=result.encounter_resolved,
                    xp_gain=result.xp_gain,
                    level_up=result.level_up,
                    new_level=result.new_level,
                    floor_number=(
                        session_state.floor_number if session_state else None
                    ),
                    floor_change=result.floor_change,
                    stone_change=result.stone_change,
                ),
                session_id=session_state.session_id if session_state else None,
                session_state=_session_summary(session_state) if session_state else None,
                suggested_actions=_suggest_actions(session_state),
            )

    try:
        narrative, state_delta = await asyncio.to_thread(
            freeform_action,
            req.user_input,
            req.rationale,
            intent.entities,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"free-form handler failed: {exc}",
        ) from exc

    resolved_path_fb: Literal["intent", "fallback"] = "fallback"
    final_narrative_fb = narrative
    if session_state is not None:
        from service.sim.action_context import ActionResult

        prev_hours_fb = session_state.hours_in_dungeon
        prev_stone_fb = session_state.stone_balance
        pseudo_result = ActionResult(
            narrative=narrative,
            hp_change=state_delta.hp_change,
            inventory_add=list(state_delta.inventory_add),
            inventory_remove=list(state_delta.inventory_remove),
            location=state_delta.location,
            time_advance=state_delta.time_advance,
            affinity_changes=dict(state_delta.affinity_changes),
            stone_change=state_delta.stone_change,
        )
        session_state = await mgr.apply_result(
            session_state.session_id,
            pseudo_result,
            user_input=req.user_input,
            resolved_path=resolved_path_fb,
        )
        _post_apply_spawn(session_state)
        clock_msg_fb = _post_apply_dungeon_clock(
            session_state,
            prev_hours_fb,
            last_advance_min=int(round(pseudo_result.time_advance * 60)),
        )
        tip_msg_fb = _build_tip_message(session_state.stone_balance, prev_stone_fb)
        needs_save_fb = False
        if clock_msg_fb:
            final_narrative_fb = f"{narrative}\n\n{clock_msg_fb}"
            needs_save_fb = True
        if tip_msg_fb:
            final_narrative_fb = f"{final_narrative_fb}\n\n{tip_msg_fb}"
            needs_save_fb = True
        if needs_save_fb:
            await mgr.save_state(session_state)

    return FreeformActionResponse(
        resolved_path=resolved_path_fb,
        confidence=intent.confidence,
        narrative=final_narrative_fb,
        state_delta=state_delta,
        fallback_reason=intent.reason,
        session_id=session_state.session_id if session_state else None,
        session_state=_session_summary(session_state) if session_state else None,
        suggested_actions=_suggest_actions(session_state),
    )
