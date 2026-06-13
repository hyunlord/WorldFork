"""AI GM 오프닝 슬라이스 — 서사 세션 API (/api/gm).

NARRATIVE_DESIGN 코어: GM이 비트를 펼치고(narration/choices), state_delta가 실제 세션
상태(flags·HP·관계·인벤·비트 전환)를 구동한다 — 장식이 아니라 진짜 시스템의 외피.
혼합 입력(선택지/자유)·성향 동료 반응은 Phase 2, 전투 메커니즘·일러스트는 Phase 3,
표현(/gm 페이지)·결과 기록 표면화는 Phase 4. 이름은 변환명(화면 unmask는 프론트).
"""

from __future__ import annotations

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
from service.sim.narrative_gm import (
    GMBeatResult,
    astream_gm_beat,
    gm_beat,
    parse_beat_text,
)
from service.sim.opening_canon import (
    COMING_OF_AGE_WEAPONS,
    KAIRA_DISPOSITION,
    KAIRA_NAME,
    Beat,
    anchor_for,
    kaira_present,
    next_beat,
)
from service.sim.world_memory import WorldState, adjust_relationship

# 미궁 진입 의도 — DUNGEON_ENTRY exit 조건(코드 전환). intent 또는 키워드로 판정.
_ENTER_INTENTS = frozenset({"enter_dungeon", "move", "enter_next_floor", "explore"})
_ENTER_WORDS = ("진입", "들어", "미궁", "내려", "나아간", "전진", "안으로", "탐색")

router = APIRouter(prefix="/api/gm", tags=["gm-narrative"])

_HISTORY_MAX = 6  # GM 맥락용 최근 서술 보관 수


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
    items: list[str] = field(default_factory=list)  # GM이 준 서사 아이템
    history: list[str] = field(default_factory=list)
    last: GMBeatResult | None = None
    last_reaction: CommandResponse | None = None  # 카이라 성향 반응(직전)


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
    companion_reaction: CompanionReactionView | None = None  # 카이라 성향 반응


def _apply_delta(s: _GMSession, result: GMBeatResult) -> None:
    """★ state_delta를 실제 세션 상태에 반영(장식 금지) — 이후 비트·서술에 영향.

    ★ Phase 2: 비트 전환은 LLM scene_transition이 아니라 코드 exit 조건(_advance_if_done)이
    결정한다(모델 편차로 맴도는 문제 근절). 여기선 flags/HP/관계/아이템만 반영.
    """
    d = result.state_delta
    s.world.flags.update(d.flags)
    if d.hp_change:
        s.hp = max(0, min(s.max_hp, s.hp + d.hp_change))
    for name, delta in d.relationship_delta.items():
        adjust_relationship(s.world, name, delta)
    s.items.extend(d.inventory_add)
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
            s.world.flags["entered_floor1"] = "true"
            done = True
    elif s.beat is Beat.FIRST_ENCOUNTER:
        done = s.world.flags.get("first_foe_resolved") == "true"  # Phase 3 전투가 설정
    # AFTERMATH = 종착
    if done:
        nxt = next_beat(s.beat)
        if nxt is not None:
            s.beat = nxt


def _render(sid: str, s: _GMSession) -> GMRender:
    r = s.last
    return GMRender(
        session_id=sid,
        beat=s.beat.value,
        narration=r.narration if r else "",
        choices=[ChoiceView(id=c.id, label=c.label) for c in (r.choices if r else [])],
        speaker=r.speaker if r else None,
        hp=s.hp,
        max_hp=s.max_hp,
        weapon=s.weapon,
        stones=s.inv.stones,
        items=list(s.items),
        flags=dict(s.world.flags),
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
        flags=dict(s.world.flags),
        history="\n".join(s.history),
        action=action,
    )
    _apply_delta(s, result)


@router.post("/session/start", response_model=GMRender)
async def start() -> GMRender:
    """새 서사 세션 — 비트1(성인식) GM 장면을 연다."""
    sid = _new_id()
    s = _GMSession()
    _SESSIONS[sid] = s
    _run_beat(s, action="(성인식 장면을 연다)")
    return _render(sid, s)


class ActRequest(BaseModel):
    session_id: str
    choice_id: str = ""  # 선택지 id(혼합 입력)
    free_text: str = Field(default="", max_length=300)  # 자유 입력


def _resolve_action(s: _GMSession, req: ActRequest) -> tuple[str, IntentMatch | None]:
    """입력(선택지/자유) → 행동 문자열 + 해석된 intent. 혼합 입력의 단일 진입.

    ★ 입력 처리 순서(맴돎 근절): ① 행동 확정 ② 무기 결정적 확정 ③ 코드 전환(narrate 전).
    전환을 먼저 해 GM이 '현재(전환 후) 비트'를 서술 — 비트와 선택지가 항상 일치한다.
    """
    is_free = bool(req.free_text.strip())
    action = req.free_text.strip()
    if not action and req.choice_id and s.last is not None:
        chosen = next((c for c in s.last.choices if c.id == req.choice_id), None)
        action = chosen.label if chosen else req.choice_id
    if not action:
        raise HTTPException(status_code=400, detail="choice_id 또는 free_text 필요")
    # ★ 성인식 무기 확정(=빌드) — choice_id로 결정적(GM 임의 flag 키 의존 X).
    if s.beat is Beat.COMING_OF_AGE and req.choice_id and not s.weapon:
        weapon = next((w for w in COMING_OF_AGE_WEAPONS if w.id == req.choice_id), None)
        if weapon is not None:
            s.weapon = weapon.label
    intent = _interpret(action, is_free=is_free)
    _advance_if_done(s, action, intent)  # ★ 코드 전환을 narrate 전에
    return action, intent


@router.post("/session/act", response_model=GMRender)
async def act(req: ActRequest) -> GMRender:
    """플레이어 행동(혼합 입력) → 코드 전환 → GM 진전 + 카이라 성향 반응."""
    s = _get(req.session_id)
    action, _ = _resolve_action(s, req)
    _run_beat(s, action=action)
    _kaira_react(s, action)
    return _render(req.session_id, s)


@router.post("/session/act/stream")
async def act_stream(req: ActRequest) -> StreamingResponse:
    """★ Phase 2 보강 B — narration 토큰 스트리밍(체감 지연 완화).

    토큰을 SSE ``data:``로 흘려 보내고, 스트림 종료 후 누적 텍스트를 파싱해 state_delta·
    카이라 반응까지 반영한 최종 렌더를 ``event: done``으로 보낸다(구조화 파싱은 종료 후).
    화면 점진 표시는 Phase 4 /gm 페이지. 신뢰 경로는 비스트리밍 /session/act(guided JSON).
    """
    s = _get(req.session_id)
    action, _ = _resolve_action(s, req)

    async def _gen() -> AsyncIterator[str]:
        buf: list[str] = []
        async for token in astream_gm_beat(
            s.beat,
            hp=s.hp,
            max_hp=s.max_hp,
            weapon=s.weapon,
            stones=s.inv.stones,
            flags=dict(s.world.flags),
            history="\n".join(s.history),
            action=action,
        ):
            buf.append(token)
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        try:
            result = parse_beat_text("".join(buf))
        except (ValueError, json.JSONDecodeError):
            yield f"event: error\ndata: {json.dumps({'detail': '파싱 실패'})}\n\n"
            return
        _apply_delta(s, result)
        _kaira_react(s, action)
        final = _render(req.session_id, s).model_dump()
        yield f"event: done\ndata: {json.dumps(final, ensure_ascii=False)}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/session/{sid}", response_model=GMRender)
async def get_state(sid: str) -> GMRender:
    """현재 서사 렌더."""
    return _render(sid, _get(sid))
