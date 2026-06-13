"""AI GM 오프닝 슬라이스 — 서사 세션 API (/api/gm).

NARRATIVE_DESIGN 코어: GM이 비트를 펼치고(narration/choices), state_delta가 실제 세션
상태(flags·HP·관계·인벤·비트 전환)를 구동한다 — 장식이 아니라 진짜 시스템의 외피.
혼합 입력(선택지/자유)·성향 동료 반응은 Phase 2, 전투 메커니즘·일러스트는 Phase 3,
표현(/gm 페이지)·결과 기록 표면화는 Phase 4. 이름은 변환명(화면 unmask는 프론트).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from service.sim.disposition import Companion
from service.sim.loot import Inventory
from service.sim.narrative_gm import GMBeatResult, gm_beat
from service.sim.opening_canon import (
    COMING_OF_AGE_WEAPONS,
    KAIRA_DISPOSITION,
    KAIRA_NAME,
    Beat,
    next_beat,
    parse_beat,
)
from service.sim.world_memory import WorldState, adjust_relationship

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


def _apply_delta(s: _GMSession, result: GMBeatResult) -> None:
    """★ state_delta를 실제 세션 상태에 반영(장식 금지) — 이후 비트·서술에 영향."""
    d = result.state_delta
    s.world.flags.update(d.flags)
    if d.hp_change:
        s.hp = max(0, min(s.max_hp, s.hp + d.hp_change))
    for name, delta in d.relationship_delta.items():
        adjust_relationship(s.world, name, delta)
    s.items.extend(d.inventory_add)
    # 비트 전환 — 바로 다음 비트로만(끌개 순서 보존: 건너뛰기·역행 차단).
    if d.scene_transition is not None:
        target = parse_beat(d.scene_transition)
        if target is not None and target is next_beat(s.beat):
            s.beat = target
    if result.narration:
        s.history.append(result.narration)
        s.history[:] = s.history[-_HISTORY_MAX:]
    s.last = result


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
    free_text: str = Field(default="", max_length=300)  # 자유 입력(Phase 2 해석 강화)


@router.post("/session/act", response_model=GMRender)
async def act(req: ActRequest) -> GMRender:
    """플레이어 행동(선택지 또는 자유) → GM 진전 + state_delta 반영."""
    s = _get(req.session_id)
    action = req.free_text.strip()
    if not action and req.choice_id and s.last is not None:
        chosen = next((c for c in s.last.choices if c.id == req.choice_id), None)
        action = chosen.label if chosen else req.choice_id
    if not action:
        raise HTTPException(status_code=400, detail="choice_id 또는 free_text 필요")
    # ★ 성인식 무기 확정(=빌드) — choice_id로 결정적(GM 임의 flag 키에 의존 X).
    if s.beat is Beat.COMING_OF_AGE and req.choice_id and not s.weapon:
        weapon = next((w for w in COMING_OF_AGE_WEAPONS if w.id == req.choice_id), None)
        if weapon is not None:
            s.weapon = weapon.label
    _run_beat(s, action=action)
    return _render(req.session_id, s)


@router.get("/session/{sid}", response_model=GMRender)
async def get_state(sid: str) -> GMRender:
    """현재 서사 렌더."""
    return _render(sid, _get(sid))
