"""Phase D — POST /api/v2/freeform_action endpoint.

Phase D step 4: session_id 기반 서버사이드 state holder.
Phase D step 3: intent path → dispatch_action (deterministic handler).
fallback path: 27B free-form (변경 없음).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from copy import deepcopy
from typing import Literal, cast

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from service.api.schemas.freeform_action import (
    FreeformActionRequest,
    FreeformActionResponse,
    SessionSummary,
    StateDelta,
)
from service.canon.context import get_canon_facts, get_spawn_table
from service.sim import predictive_cache
from service.sim.action_context import ActionContext, ActionResult
from service.sim.action_handlers import dispatch_action
from service.sim.dungeon_clock import RETURN_TIME_ADVANCE_HOURS, check_warning, should_force_return
from service.sim.encounter_narrative import compose_encounter_line
from service.sim.equipment import equipment_set_from_dict
from service.sim.freeform_handler import freeform_action, stream_freeform_narrative
from service.sim.gm_narrator import (
    GM_NARRATE_ACTIONS,
    build_gm_canon,
    compose_gm_narrative,
    gm_model_label,
    is_pivotal_gm,
    stream_gm_narrative,
)
from service.sim.intent_classifier import classify_intent, mechanical_classify
from service.sim.session_manager import SessionState, get_session_manager
from service.sim.spawn_trigger import determine_location_type, trigger_spawn
from service.sim.story_progression import (
    PHASE_DEPARTURE,
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


def _post_apply_spawn(state: SessionState) -> str | None:
    """action 적용 후 encounter auto spawn check — state 인플레이스 갱신.

    ★ 서빙 2단계: 새 적대 적이 스폰되면 등장 라인을 반환(호출자가 narrative에
    이어 붙임) — 보스만 연출되고 일반 적은 조용히 출현하던 결함(진단 A) 해소.
    비적대 NPC seed/스폰 없음 시 None.
    """
    if state.encounters:
        return None
    spawn_table = get_spawn_table()
    if spawn_table is None:
        return None
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
        floor_number=state.floor_number,  # ★ 4단계 — 얕은 층 고증 게이팅
    )
    if not new_encounters:
        return None
    state.encounters = new_encounters
    state.last_spawn_turn = state.turn_count
    # ★ 첫 적대 적의 등장 라인 (0-토큰 mechanical — "적을 마주했다" 맥락).
    hostile = next(
        (e for e in new_encounters if e.get("hostile") or e.get("is_hostile")),
        None,
    )
    if hostile is None:
        return None
    return compose_encounter_line(hostile, state.turn_count)


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
    # ★ 버그4 — '더 깊이 나아간다'는 균열 내(rift_sub_area)에서만 유효(MOVE_CHAMBER).
    #   균열 밖 던전 floor에서 추천하면 'handle_move_chamber: 균열 안에 있지 않거나…'
    #   실행 불가 응답. 균열 밖에서는 항상 실행 가능한 탐색(EXPLORE)을 추천한다.
    deeper = "더 깊이 나아간다" if state.rift_sub_area else "안쪽을 탐색한다"
    if npcs:
        npc_name = str(npcs[0].get("name") or "상대")
        tail = "무기를 점검한다" if state.floor_number < 1 else deeper
        return [f"{npc_name}에게 말을 건다", "주변을 둘러본다", tail]
    if state.floor_number < 1:
        return ["주변을 둘러본다", "무기를 점검한다", "길을 나선다"]
    return ["주변을 살핀다", deeper, "잠시 휴식한다"]


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
    # ★ Canon Contract 주입(고증 RAG) — 성년식 장면: 위치/persona/무기 앵커.
    canon = build_gm_canon(req.user_input, ctx.location, npc, None, chosen)
    gm_text = await asyncio.to_thread(
        compose_gm_narrative,
        req.user_input,
        fact,
        ctx.location,
        npc,
        recent,
        canon,
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
        gm_model="27b",  # ★ 성년식 무기 선택 = pivotal 27B
    )


# ("token", str) — narrative 토큰 점진 / ("complete", FreeformActionResponse) — 최종
_StreamEvent = tuple[str, object]


async def _run_action_stream(
    req: FreeformActionRequest,
) -> AsyncIterator[_StreamEvent]:
    """자연어 input 처리 코어 — 토큰 스트리밍 + 최종 응답을 이벤트로 산출.

    JSON 엔드포인트와 SSE 엔드포인트가 이 단일 코어를 공유한다(동작 정합 보장).
    GM 서사형 intent 경로는 27B 토큰을 ('token', delta)로 점진 전달하고,
    마지막에 ('complete', FreeformActionResponse)로 canonical 응답(시스템/clock/tip
    포함)을 1회 산출한다. 그 외 경로(무기 선택·fallback)는 complete만 산출한다.

    Step 1: 9B classifier → Step 2: intent dispatch → Step 3: free-form fallback
    Step 4: session 반영. (직전 단일 함수와 동일 로직 — 흐름만 generator로 전환)
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

    # ★ 예측 생성 캐시 히트 — 유휴 시간에 미리 생성한 선택지면 즉시 반환(0초 체감).
    #   turn_count 일치 = 상태 그대로 → 예측한 다음 상태를 커밋. 자유 입력은 미스(폴백).
    if session_state is not None:
        cached = predictive_cache.take(
            session_state.session_id, session_state.turn_count, req.user_input
        )
        if cached is not None:
            await mgr.save_state(cached.next_state)
            yield ("complete", cached.response)
            return

    # ★ 도그푸딩 속도: 명백한 행동(방위 이동·휴식)은 0토큰 규칙으로 즉시 분류해
    #   ~6s LLM classify를 건너뛴다(원칙 #5 Mechanical 우선). 모호하면 LLM.
    intent = mechanical_classify(req.user_input)
    if intent is None:
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
            resp = await _handle_weapon_choice(req, session_state, chosen, ctx)
            yield ("complete", resp)
            return

    # ★ departure 단계 던전 진입 보조 (intent 정확도) — 무기 선택 후 departure는
    #   던전 향하는 단계라 '미궁/던전' 류 입력은 진입 의도. 9B가 enter_dungeon으로
    #   분류 못 해도 단계 기반으로 강제(intent flaky 회피). 9B confidence는 조작하지
    #   않고 별도 forced_action으로 둬, classifier 출력 투명성을 유지한다.
    forced_action: PlayerActionType | None = None
    if (
        session_state is not None
        and session_state.story_phase == PHASE_DEPARTURE
        and any(kw in req.user_input for kw in ("미궁", "던전", "들어가", "향한"))
    ):
        forced_action = PlayerActionType.ENTER_DUNGEON

    # forced_action(단계 기반) 우선, 없으면 9B intent(임계값 충족 시).
    action_value = (
        forced_action.value
        if forced_action is not None
        else (
            intent.matched_action
            if intent.confidence >= INTENT_THRESHOLD
            else None
        )
    )

    action_type: PlayerActionType | None = None
    if action_value is not None:
        try:
            action_type = PlayerActionType(action_value)
        except ValueError:
            action_type = None

    if action_type is not None:
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
        #   서빙 1단계(스트리밍): GM 토큰을 점진 전달(체감 지연 제거).
        #   GM 실패/단문 시 handler template narrative로 fallback.
        npc_name = next(
            (
                str(e.get("name"))
                for e in ctx.encounters
                if e.get("hostile") is False
            ),
            None,
        )
        gm_model: str | None = None
        # ★ 무대상 공격(적 없는데 ATTACK) 등 no_target 실패는 GM 서술을 건너뛴다 —
        #   handler가 이미 time_advance=0(턴 미소모)로 처리하는데 GM이 27B로 '빈 공기를
        #   베는…'을 굳이 서술하던 낭비 제거(체감 + 27B 비용). 터스 안내만 노출.
        if (
            session_state is not None
            and action_type in GM_NARRATE_ACTIONS
            and result.fail_reason != "no_target"
        ):
            recent = await mgr.get_recent_turns(session_state.session_id)
            # 전투 시 적 상태(이름/HP)를 GM 컨텍스트에 — 약점/위기 묘사 정합.
            hostile_state = [
                f"{e.get('name')}(HP {e.get('hp')}/{e.get('max_hp')})"
                for e in ctx.encounters
                if e.get("hostile")
            ]
            surroundings = (
                ", ".join(hostile_state)
                if hostile_state
                else (npc_name or "특이사항 없음")
            )
            # ★ 서빙 3단계 — 하이브리드 라우팅: pivotal(성년식 단계·전투·적대
            #   조우)은 27B 품질, 순수 단순 행동은 9B(빠름). '애매하면 27B' 안전.
            pivotal = is_pivotal_gm(
                action_type, session_state.story_phase, bool(hostile_state)
            )
            gm_model = gm_model_label(pivotal)
            # ★ Canon Contract 주입(고증 RAG) — 위치/적 등급·출몰/persona/무기 정합.
            hostile_names = [
                str(e.get("name")) for e in ctx.encounters if e.get("hostile")
            ]
            weapon_eq = (session_state.equipment or {}).get("weapon")
            weapon_name = (
                str(weapon_eq.get("name") or "")
                if isinstance(weapon_eq, dict)
                else ""
            )
            canon = build_gm_canon(
                req.user_input, ctx.location, surroundings,
                hostile_names, weapon_name,
            )
            pieces: list[str] = []
            async for delta in stream_gm_narrative(
                req.user_input,
                result.narrative,
                ctx.location,
                surroundings,
                recent,
                canon,
                PHASE_LABEL.get(session_state.story_phase, ""),
                pivotal=pivotal,
            ):
                pieces.append(delta)
                yield ("token", delta)
            gm_text = "".join(pieces).strip()
            if len(gm_text) >= 20:
                # ★ 「」 시스템 메시지(EXP/처치/HP 경고 등)는 mechanical fact —
                #   GM 서사 뒤에 보존(정확 수치 손실 방지, 04 정합).
                system_lines = [
                    ln
                    for ln in result.narrative.split("\n")
                    if ln.strip().startswith("「")
                ]
                result.narrative = (
                    gm_text + "\n\n" + "\n".join(system_lines)
                    if system_lines
                    else gm_text
                )

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
            # ★ 서빙 2단계: 새 적 스폰 시 등장 라인을 GM 서사 뒤에 — 조용한 출현 해소.
            encounter_msg = _post_apply_spawn(session_state)
            clock_msg = _post_apply_dungeon_clock(
                session_state,
                prev_hours,
                last_advance_min=int(round(result.time_advance * 60)),
            )
            tip_msg = _build_tip_message(session_state.stone_balance, prev_stone)
            needs_save = False
            if encounter_msg:
                final_narrative = f"{final_narrative}\n\n{encounter_msg}"
                needs_save = True
            if clock_msg:
                final_narrative = f"{final_narrative}\n\n{clock_msg}"
                needs_save = True
            if tip_msg:
                final_narrative = f"{final_narrative}\n\n{tip_msg}"
                needs_save = True
            if needs_save:
                await mgr.save_state(session_state)

        yield (
            "complete",
            FreeformActionResponse(
                resolved_path=resolved_path,
                matched_action=action_type.value,
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
                session_state=(
                    _session_summary(session_state) if session_state else None
                ),
                suggested_actions=_suggest_actions(session_state),
                gm_model=gm_model,
            ),
        )
        return

    # ★ 도그푸딩 속도: free-form도 메인 경로처럼 토큰 스트리밍(첫 토큰 ~1s 체감).
    #   스트림 무출력 시에만 sync freeform_action 백업(안전 서사 보장 — 502 금지).
    fb_pieces: list[str] = []
    async for piece in stream_freeform_narrative(
        req.user_input, req.rationale, intent.entities
    ):
        fb_pieces.append(piece)
        yield ("token", piece)
    narrative = "".join(fb_pieces).strip()
    state_delta = StateDelta(time_advance=1)
    if len(narrative) < 10:
        narrative, state_delta = await asyncio.to_thread(
            freeform_action,
            req.user_input,
            req.rationale,
            intent.entities,
        )

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
        encounter_msg_fb = _post_apply_spawn(session_state)
        clock_msg_fb = _post_apply_dungeon_clock(
            session_state,
            prev_hours_fb,
            last_advance_min=int(round(pseudo_result.time_advance * 60)),
        )
        tip_msg_fb = _build_tip_message(session_state.stone_balance, prev_stone_fb)
        needs_save_fb = False
        if encounter_msg_fb:
            final_narrative_fb = f"{final_narrative_fb}\n\n{encounter_msg_fb}"
            needs_save_fb = True
        if clock_msg_fb:
            # ★ final_narrative_fb 기준으로 체이닝(encounter_msg_fb 보존)
            final_narrative_fb = f"{final_narrative_fb}\n\n{clock_msg_fb}"
            needs_save_fb = True
        if tip_msg_fb:
            final_narrative_fb = f"{final_narrative_fb}\n\n{tip_msg_fb}"
            needs_save_fb = True
        if needs_save_fb:
            await mgr.save_state(session_state)

    yield (
        "complete",
        FreeformActionResponse(
            resolved_path=resolved_path_fb,
            confidence=intent.confidence,
            narrative=final_narrative_fb,
            state_delta=state_delta,
            fallback_reason=intent.reason,
            session_id=session_state.session_id if session_state else None,
            session_state=(
                _session_summary(session_state) if session_state else None
            ),
            suggested_actions=_suggest_actions(session_state),
        ),
    )


@router.post("/freeform_action", response_model=FreeformActionResponse)
async def freeform_action_endpoint(
    req: FreeformActionRequest,
) -> FreeformActionResponse:
    """자연어 input → intent dispatch 또는 free-form fallback (full JSON).

    스트리밍 코어(_run_action_stream)를 소진해 최종 응답만 반환 — 토큰 이벤트는
    버린다. 비스트리밍 클라이언트/기존 테스트 호환 경로(동작 불변).
    """
    final: FreeformActionResponse | None = None
    async for kind, payload in _run_action_stream(req):
        if kind == "complete":
            final = cast(FreeformActionResponse, payload)
    if final is None:
        raise HTTPException(status_code=500, detail="no response produced")
    return final


def _sse(event: str, data: dict[str, object]) -> str:
    """SSE 1 이벤트 프레임 (event + data, 한글 그대로)."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/freeform_action/stream")
async def freeform_action_stream_endpoint(
    req: FreeformActionRequest,
) -> StreamingResponse:
    """자연어 input → SSE 토큰 점진 노출 (서빙 1단계 — 체감 지연 제거).

    event: token  — narrative 토큰 delta ({"text": ...}), 점진 노출용
    event: complete — canonical FreeformActionResponse(시스템/clock/tip 포함)
    event: error  — 처리 실패 ({"detail": ...})

    프론트는 token으로 미리보기를 그리고, complete의 narrative로 확정(상태 권위는
    complete). GM 비대상/무기선택/fallback은 token 없이 complete만 온다.
    """

    async def _gen() -> AsyncIterator[str]:
        try:
            async for kind, payload in _run_action_stream(req):
                if kind == "token":
                    yield _sse("token", {"text": cast(str, payload)})
                else:
                    resp = cast(FreeformActionResponse, payload)
                    yield _sse("complete", resp.model_dump())
        except HTTPException as exc:
            yield _sse("error", {"detail": str(exc.detail)})
        except Exception as exc:  # noqa: BLE001 — 스트림 중 오류도 클라이언트에 전달
            yield _sse("error", {"detail": str(exc)})

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx/proxy 버퍼링 방지(즉시 flush)
        },
    )


# ─── 예측 생성 (서빙 — 체감 0초) ────────────────────────────────────────────────
class PredictRequest(BaseModel):
    """유휴 시간 예측 생성 요청 — 다음 후보 행동(추천 버튼)을 미리 생성."""

    session_id: str
    actions: list[str] = Field(default_factory=list, max_length=4)


# ★ 예측 확대 — 추천 3개 다 예측(적중률 1/3→3/3). 출력 길이 최적화로 예측 1개 생성이
#   ~3.6s(종전 11.5s)로 짧아져 GPU 경합이 완화돼 3개로 확대 가능(곱셈 효과).
_PREDICT_MAX = 3


async def _predict_one(real_session_id: str, action: str) -> bool:
    """행동 1개를 상태 복사본에 dry-run해 캐시. 성공 시 True.

    기존 _run_action_stream을 무수정 재사용 — 복사본을 임시 session_id로 등록해 그 위에서
    돌리면 영속화가 복사본에만 일어난다(real 세션 무영향). 결과 응답·다음 상태를 real id로
    고쳐 캐시. turn_count 키라 다음 턴이 진행되면 자동 무효.
    """
    mgr = get_session_manager()
    real = await mgr.get_session(real_session_id)
    if real is None:
        return False
    turn = real.turn_count
    if predictive_cache.has(real_session_id, turn, action):
        return False  # 이미 예측됨(중복 생성 방지)
    # 전투 맥락(적대 조우)은 RNG + 이미 빠른 mechanical → 예측 제외(잘못된 결과 커밋 회피).
    if any(e.get("hostile") for e in real.encounters):
        return False

    copy = deepcopy(real)
    temp_id = f"__pred__{real_session_id}__{turn}__{abs(hash(action))}"
    copy.session_id = temp_id
    mgr._cache[temp_id] = copy
    try:
        preq = FreeformActionRequest(
            user_input=action,
            session_id=temp_id,
            current_hp=real.current_hp,
            max_hp=real.max_hp,
            inventory=list(real.inventory),
            location=real.location,
        )
        response: FreeformActionResponse | None = None
        async for kind, payload in _run_action_stream(preq):
            if kind == "complete":
                response = cast(FreeformActionResponse, payload)
        next_state = mgr._cache.get(temp_id)
        if response is None or next_state is None:
            return False
        # 커밋용으로 real id 복원 + 응답을 real 기준으로 고쳐 캐시.
        next_state.session_id = real_session_id
        fixed = response.model_copy(
            update={
                "session_id": real_session_id,
                "session_state": _session_summary(next_state),
            }
        )
        predictive_cache.put(
            real_session_id,
            turn,
            action,
            predictive_cache.Prediction(fixed, next_state),
        )
        return True
    finally:
        mgr._cache.pop(temp_id, None)  # 임시 세션 정리


@router.post("/freeform_action/predict")
async def predict_endpoint(req: PredictRequest) -> dict[str, int]:
    """유휴 시간 백그라운드 예측 — 추천 버튼 후보를 미리 생성(클릭 시 캐시 히트 0초).

    프론트가 한 턴을 그린 뒤(사용자가 읽는 동안) suggested_actions로 호출한다.
    실제 행동 제출은 _run_action_stream이 캐시를 투명하게 확인하므로 별도 처리 불필요.
    """
    made = 0
    for action in req.actions[:_PREDICT_MAX]:
        try:
            if await _predict_one(req.session_id, action):
                made += 1
        except Exception:  # noqa: BLE001 — 예측은 best-effort(실패해도 실 플레이 무영향)
            continue
    return {"predicted": made}
