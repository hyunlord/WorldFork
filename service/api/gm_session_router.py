"""AI GM 오프닝 슬라이스 — 서사 세션 API (/api/gm).

NARRATIVE_DESIGN 코어: GM이 비트를 펼치고(narration/choices), state_delta가 실제 세션
상태(flags·HP·관계·인벤·비트 전환)를 구동한다 — 장식이 아니라 진짜 시스템의 외피.
혼합 입력(선택지/자유)·성향 동료 반응은 Phase 2, 전투 메커니즘·일러스트는 Phase 3,
표현(/gm 페이지)·결과 기록 표면화는 Phase 4. 이름은 변환명(화면 unmask는 프론트).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from service.api.schemas.freeform_action import IntentMatch
from service.sim.disposition import Companion
from service.sim.disposition_command import (
    CommandResponse,
    apply_order,
    interpret_command,
)
from service.sim.intent_classifier import classify_intent, mechanical_classify
from service.sim.loot import Inventory
from service.sim.narrative_combat import Foe, RoundResult, resolve_round
from service.sim.narrative_gm import (
    GMBeatResult,
    astream_gm_beat,
    extract_narration,
    gm_beat,
    parse_beat_text,
)
from service.sim.opening_canon import (
    COMING_OF_AGE_WEAPONS,
    KAIRA_DISPOSITION,
    KAIRA_NAME,
    Beat,
    anchor_for,
    beat_choices,
    kaira_present,
    next_beat,
)
from service.sim.status import StatusEffect, StatusType
from service.sim.world_memory import WorldState, adjust_relationship

# 미궁 진입 의도 — DUNGEON_ENTRY exit 조건(코드 전환). intent 또는 키워드로 판정.
_ENTER_INTENTS = frozenset({"enter_dungeon", "move", "enter_next_floor", "explore"})
_ENTER_WORDS = ("진입", "들어", "미궁", "내려", "나아간", "전진", "안으로", "탐색")

router = APIRouter(prefix="/api/gm", tags=["gm-narrative"])

_HISTORY_MAX = 6  # GM 맥락용 최근 서술 보관 수

# ★ 영구 세계(§6 PERSISTENT) — 관계·world memory만 세션을 넘어 유지. 새 런(start)이 이어받는다.
#   ★ PER-RUN(무기·인벤·소지금·빌드/진행 flag = run_flags)은 런마다 완전 리셋(§6 캐릭터 귀속).
#   GM은 flags를 쓰지 않는다(코드 소관) — 빌드/rite 누적 버그 차단.
_PERSISTENT_WORLD = WorldState()


def _new_kaira() -> Companion:
    return Companion(KAIRA_NAME, KAIRA_DISPOSITION, hp=140, max_hp=140, attack=14)


@dataclass
class _GMSession:
    beat: Beat = Beat.COMING_OF_AGE
    world: WorldState = field(default_factory=WorldState)  # flags·관계(Phase 2 영구)
    inv: Inventory = field(default_factory=Inventory)  # 소지금·마석·정수
    kaira: Companion = field(default_factory=_new_kaira)
    hp: int = 120
    max_hp: int = 120
    weapon: str = ""
    items: list[str] = field(default_factory=list)  # GM이 준 서사 아이템(PER-RUN)
    run_flags: dict[str, str] = field(default_factory=dict)  # ★ PER-RUN 진행/빌드 flag
    player_status: list[StatusEffect] = field(default_factory=list)  # 출혈 등
    foe: Foe | None = None  # 첫 조우 전투 적(내러티브 턴)
    history: list[str] = field(default_factory=list)
    last: GMBeatResult | None = None
    last_reaction: CommandResponse | None = None  # 카이라 성향 반응(직전)
    last_illustration: str | None = None  # 직전 비트 일러스트 스틸 키


_SESSIONS: dict[str, _GMSession] = {}
_NEXT = {"n": 0}


def _new_id() -> str:
    _NEXT["n"] += 1
    return f"gm_{_NEXT['n']}"


def _get(sid: str) -> _GMSession:
    s = _SESSIONS.get(sid)
    if s is None:
        raise HTTPException(status_code=404, detail=f"세션 없음: {sid}")
    return s


class ChoiceView(BaseModel):
    id: str
    label: str


class MemberView(BaseModel):
    name: str
    hp: int
    max_hp: int
    disposition: dict[str, int]


class CompanionReactionView(BaseModel):
    """카이라 성향 반응 — 화면에 또렷이 노출(차별점 가시화)."""

    name: str
    reaction: str  # comply / adapt / refuse
    action: str
    reason: str
    speech: str


class FoeView(BaseModel):
    """전투 적 — 좌표 없음(HP만)."""

    name: str
    hp: int
    max_hp: int


class GMRender(BaseModel):
    """서사 렌더 — 이름은 변환명(화면 unmask는 프론트 unmaskIp)."""

    session_id: str
    beat: str
    narration: str
    choices: list[ChoiceView]
    speaker: str | None
    hp: int
    max_hp: int
    weapon: str
    stones: int
    items: list[str]
    flags: dict[str, str]
    relationships: dict[str, int]
    party: list[MemberView]
    foe: FoeView | None = None  # 전투 적(첫 조우)
    bleeding: bool = False  # 비요른 출혈 상태
    illustration: str | None = None  # 띄울 스틸 키(Phase 4 렌더)
    companion_reaction: CompanionReactionView | None = None  # 카이라 성향 반응


def _apply_delta(s: _GMSession, result: GMBeatResult) -> None:
    """GM 서사 델타 반영 — ★ 관계(영구)·서사 아이템만. flags/HP/무기/전환은 코드 소관(GM 불가).

    비트 전환은 코드 exit(_advance_if_done), HP/무기/소지금은 코드. GM은 서술 + 관계/아이템만.
    """
    d = result.state_delta
    for name, delta in d.relationship_delta.items():
        adjust_relationship(s.world, name, delta)  # 관계는 영구(PERSISTENT)
    s.items.extend(d.inventory_add)  # PER-RUN 서사 아이템
    if result.illustration is not None:
        s.last_illustration = result.illustration
    if result.narration:
        s.history.append(result.narration)
        s.history[:] = s.history[-_HISTORY_MAX:]
    s.last = result


def _interpret(action: str, *, is_free: bool) -> IntentMatch | None:
    """자유 입력 해석 — mechanical(0토큰) 먼저, 자유·미분류면 classify_intent(9B).

    선택지 라벨은 0토큰 분류만(LLM 낭비 방지). 결과 intent로 장면 내 행동·전환을 판정한다.
    """
    m = mechanical_classify(action)
    if m is not None:
        return m
    return classify_intent(action) if is_free else None


def _situation(s: _GMSession) -> str:
    """카이라 성향 반응용 상황 요약 — 현 비트 장면 + 최근 서술."""
    scene = anchor_for(s.beat).scene
    recent = s.history[-1] if s.history else ""
    return f"{scene} 최근: {recent}" if recent else scene


def _kaira_react(s: _GMSession, action: str) -> None:
    """카이라(아이나르) 성향 반응 — 플레이어 행동을 지시로 받아 순응/변형/거부(LLM).

    화면에 또렷이 노출(차별점). 반응의 action을 current_order로 반영(거부는 자기 판단).
    """
    if not kaira_present(s.beat):
        s.last_reaction = None
        return
    resp = interpret_command(s.kaira, action, _situation(s))
    apply_order(s.kaira, resp)
    s.last_reaction = resp


def _advance_if_done(s: _GMSession, action: str, intent: IntentMatch | None) -> None:
    """★ 코드 구동 비트 전환 — 비트별 exit 조건을 상태로 판정(LLM 의존 폐기).

    조건 충족 시 next_beat로만 진행(끌개 순서 보존: 건너뛰기·역행 차단).
    """
    done = False
    if s.beat is Beat.COMING_OF_AGE:
        done = bool(s.weapon)  # 무기 확정 = 성인식 완료
    elif s.beat is Beat.DUNGEON_ENTRY:
        entered = (intent is not None and intent.matched_action in _ENTER_INTENTS) or any(
            w in action for w in _ENTER_WORDS
        )
        if entered:
            s.run_flags["entered_floor1"] = "true"
            done = True
    elif s.beat is Beat.FIRST_ENCOUNTER:
        done = s.run_flags.get("first_foe_resolved") == "true"  # 전투가 설정
    # AFTERMATH = 종착
    if done:
        if s.beat is Beat.COMING_OF_AGE:
            s.run_flags["rite_passed"] = "true"  # 코드가 성인식 완료를 기록(GM 아님)
        nxt = next_beat(s.beat)
        if nxt is not None:
            s.beat = nxt
            if nxt is Beat.FIRST_ENCOUNTER and s.foe is None:
                # 첫 조우 적 등장(내러티브 턴 전투 — 좌표 없음).
                s.foe = Foe("고블린", hp=36, max_hp=36, attack=8, essence_drop="고블린 정수")


def _render(sid: str, s: _GMSession) -> GMRender:
    r = s.last
    return GMRender(
        session_id=sid,
        beat=s.beat.value,
        narration=r.narration if r else "",
        # ★ 선택지는 코드 정의(즉시·결정적·캐논) — LLM 생성 아님.
        choices=[ChoiceView(id=c.id, label=c.label) for c in beat_choices(s.beat)],
        speaker=r.speaker if r else None,
        hp=s.hp,
        max_hp=s.max_hp,
        weapon=s.weapon,
        stones=s.inv.stones,
        items=list(s.items),
        flags=dict(s.run_flags),
        relationships=dict(s.world.relationships),
        party=[
            MemberView(
                name=s.kaira.name,
                hp=s.kaira.hp,
                max_hp=s.kaira.max_hp,
                disposition={
                    "충성": s.kaira.disposition.loyalty,
                    "저돌": s.kaira.disposition.aggression,
                    "지혜": s.kaira.disposition.wisdom,
                    "변덕": s.kaira.disposition.whimsy,
                    "유대": s.kaira.disposition.bond,
                },
            )
        ],
        foe=(
            FoeView(name=s.foe.name, hp=s.foe.hp, max_hp=s.foe.max_hp)
            if s.foe is not None
            else None
        ),
        bleeding=any(st.type is StatusType.BLEED for st in s.player_status),
        illustration=s.last_illustration,
        companion_reaction=(
            CompanionReactionView(
                name=s.kaira.name,
                reaction=s.last_reaction.reaction.value,
                action=s.last_reaction.action.value,
                reason=s.last_reaction.reason,
                speech=s.last_reaction.speech,
            )
            if s.last_reaction is not None
            else None
        ),
    )


def _run_beat(s: _GMSession, action: str) -> None:
    """GM 한 비트 호출 → state_delta 반영. 호출자가 _render."""
    result = gm_beat(
        s.beat,
        hp=s.hp,
        max_hp=s.max_hp,
        weapon=s.weapon,
        stones=s.inv.stones,
        flags=dict(s.run_flags),
        history="\n".join(s.history),
        action=action,
    )
    _apply_delta(s, result)


@router.post("/session/start", response_model=GMRender)
async def start() -> GMRender:
    """새 서사 세션(런) — 영구 세계(flags·관계·소지금) 이어받고, 캐릭터 상태는 리셋.

    비트1(성인식) GM 장면을 연다. world/inv는 영구 싱글톤 공유 → 세션을 넘어 유지(§6).
    """
    sid = _new_id()
    # 영구 세계(관계)만 이어받고, PER-RUN(무기·인벤·소지금·run_flags·HP)은 fresh default로 리셋.
    s = _GMSession(world=_PERSISTENT_WORLD)
    _SESSIONS[sid] = s
    _run_beat(s, action="(성인식 장면을 연다)")
    return _render(sid, s)


class ActRequest(BaseModel):
    session_id: str
    choice_id: str = ""  # 선택지 id(혼합 입력)
    free_text: str = Field(default="", max_length=300)  # 자유 입력


def _action_text(s: _GMSession, req: ActRequest) -> str:
    """입력(선택지/자유) → 행동 문자열. 선택지는 현 비트 코드 선택지에서 라벨 조회. 비면 400."""
    action = req.free_text.strip()
    if not action and req.choice_id:
        chosen = next((c for c in beat_choices(s.beat) if c.id == req.choice_id), None)
        action = chosen.label if chosen else req.choice_id
    if not action:
        raise HTTPException(status_code=400, detail="choice_id 또는 free_text 필요")
    return action


def _resolve_action(s: _GMSession, req: ActRequest) -> str:
    """행동 확정 → 무기 결정적 확정 → 코드 전환(narrate 전). 전환 후 비트를 GM이 서술해 일치."""
    action = _action_text(s, req)
    if s.beat is Beat.COMING_OF_AGE and req.choice_id and not s.weapon:
        weapon = next((w for w in COMING_OF_AGE_WEAPONS if w.id == req.choice_id), None)
        if weapon is not None:
            s.weapon = weapon.label
    intent = _interpret(action, is_free=bool(req.free_text.strip()))
    _advance_if_done(s, action, intent)
    return action


def _apply_combat(s: _GMSession, action: str) -> RoundResult:
    """한 라운드 코드 판정(권위) — 플레이어+카이라 성향+적. 처치 시 마무리로 전환.

    GM 서술은 호출자(비스트림/스트림)가 confirmed=rr.lines로 별도 수행(라운드당 1회).
    """
    assert s.foe is not None
    rr = resolve_round(
        player_action=action,
        weapon=s.weapon,
        player_hp=s.hp,
        player_max_hp=s.max_hp,
        player_status=s.player_status,
        foe=s.foe,
        kaira=s.kaira,
        inv=s.inv,
        situation=_situation(s),
    )
    s.hp = rr.player_hp
    s.player_status = rr.player_status
    s.last_reaction = rr.kaira_reaction
    if rr.foe_defeated:
        s.run_flags["first_foe_resolved"] = "true"
        s.foe = None
        _advance_if_done(s, action, None)  # → AFTERMATH
    return rr


def _absorb_narration(s: _GMSession, result: GMBeatResult, illust_fallback: str) -> None:
    """전투 GM 서술 흡수 — 코드가 권위라 narration/choices/illustration만 취한다."""
    s.last = result
    if result.narration:
        s.history.append(result.narration)
        s.history[:] = s.history[-_HISTORY_MAX:]
    s.last_illustration = result.illustration or illust_fallback


def _combat_round(s: _GMSession, sid: str, action: str) -> GMRender:
    """첫 조우 한 라운드(비스트림) — 코드 판정 → GM 서술(확정 결과만)."""
    rr = _apply_combat(s, action)
    result = gm_beat(
        s.beat,
        hp=s.hp,
        max_hp=s.max_hp,
        weapon=s.weapon,
        stones=s.inv.stones,
        flags=dict(s.run_flags),
        history="\n".join(s.history),
        action=action,
        confirmed=rr.lines,
    )
    _absorb_narration(s, result, rr.illustration)
    return _render(sid, s)


@router.post("/session/act", response_model=GMRender)
async def act(req: ActRequest) -> GMRender:
    """플레이어 행동(혼합 입력) → 전투 라운드 또는 비트 진전 + 카이라 성향 반응."""
    s = _get(req.session_id)
    # 첫 조우 + 생존 적 → 내러티브 턴 전투 라운드(코드 판정 + GM 서술 1회)
    if s.beat is Beat.FIRST_ENCOUNTER and s.foe is not None and s.foe.alive:
        return _combat_round(s, req.session_id, _action_text(s, req))
    # 일반 비트 — 코드 전환(narrate 전) → GM 진전 → 카이라 성향 반응
    action = _resolve_action(s, req)
    _run_beat(s, action=action)
    _kaira_react(s, action)
    return _render(req.session_id, s)


@router.post("/session/act/stream")
async def act_stream(req: ActRequest) -> StreamingResponse:
    """★ narration 스트리밍 플레이 경로(/gm 페이지) — 체감 지연 완화.

    narration을 정제해 SSE ``data:{narration}``로 흘리고, 종료 후 파싱해 상태 반영한 최종
    렌더를 ``event: done``으로 보낸다. 전투면 코드 판정(권위) 먼저 → GM은 확정 결과 서술.
    비전투면 카이라 성향 반응을 GM 스트림과 병렬(지연 완화). 신뢰 파싱 경로는 비스트림 /act.
    """
    s = _get(req.session_id)
    combat = s.beat is Beat.FIRST_ENCOUNTER and s.foe is not None and s.foe.alive
    action = _action_text(s, req) if combat else _resolve_action(s, req)

    async def _gen() -> AsyncIterator[str]:
        confirmed: list[str] | None = None
        illust_fallback: str | None = None
        kaira_task: asyncio.Task[None] | None = None
        if combat:
            rr = await asyncio.to_thread(_apply_combat, s, action)  # 코드 판정(+카이라)
            confirmed, illust_fallback = rr.lines, rr.illustration
        elif kaira_present(s.beat):
            # 비전투 카이라 반응을 GM 스트림과 병렬(지연 완화)
            kaira_task = asyncio.create_task(asyncio.to_thread(_kaira_react, s, action))

        buf: list[str] = []
        emitted = ""
        async for token in astream_gm_beat(
            s.beat,
            hp=s.hp,
            max_hp=s.max_hp,
            weapon=s.weapon,
            stones=s.inv.stones,
            flags=dict(s.run_flags),
            history="\n".join(s.history),
            action=action,
            confirmed=confirmed,
        ):
            buf.append(token)
            narr = extract_narration("".join(buf))
            if narr is not None and len(narr) > len(emitted):
                chunk = json.dumps({"narration": narr[len(emitted):]}, ensure_ascii=False)
                yield f"data: {chunk}\n\n"
                emitted = narr
        if kaira_task is not None:
            await kaira_task
        try:
            result = parse_beat_text("".join(buf))
        except (ValueError, json.JSONDecodeError):
            yield f"event: error\ndata: {json.dumps({'detail': '파싱 실패'})}\n\n"
            return
        if combat:
            _absorb_narration(s, result, illust_fallback or "ui_combat_bjorn_action")
        else:
            _apply_delta(s, result)
        final = _render(req.session_id, s).model_dump()
        yield f"event: done\ndata: {json.dumps(final, ensure_ascii=False)}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/session/{sid}", response_model=GMRender)
async def get_state(sid: str) -> GMRender:
    """현재 서사 렌더."""
    return _render(sid, _get(sid))
