"""V3 게임 통합 MVP — RTwP 세션 API (엔진 → 실제 플레이).

V3 엔진 4조각(자율/지시/영구/파티)을 HTTP 플레이 루프로 잇는다. 서버가 PartyWorld +
WorldState를 세션별로 들고, 평소 tick(party_step, 코드 0토큰)으로 진행하다 플레이어가
일시정지하고 자연어 지시(command, Phase 1 LLM)하면 성향대로 반영한다. 영구(Phase 2)는
flags/relationships로 렌더에 노출. 어떤 클라이언트로도 플레이하도록 ASCII 그리드를 함께 준다.

★ DispositionSession/party의 프로덕션 호출자(made-but-never-used 해소). 풀 UI는 후속 —
MVP는 핵심 경험(자율 파티 + 일시정지 지시 + 영구)만.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from service.sim.disposition import (
    PRESET_BERSERKER,
    PRESET_GUARDIAN,
    PRESET_SCOUT,
    Companion,
)
from service.sim.party import (
    PartyWorld,
    command_all,
    command_member,
    detect_branch,
    party_step,
)
from service.sim.world_memory import WorldState, judge_permanence, npc_attitude, record

router = APIRouter(prefix="/api/v3", tags=["v3-rtwp"])

_GRID_W, _GRID_H = 10, 6


@dataclass
class _Session:
    world: PartyWorld
    memory: WorldState = field(default_factory=WorldState)


_SESSIONS: dict[str, _Session] = {}
_NEXT = {"n": 0}


def _new_id() -> str:
    _NEXT["n"] += 1
    return f"v3_{_NEXT['n']}"


def _new_party() -> PartyWorld:
    return PartyWorld(
        companions=[
            Companion("투르윈", PRESET_BERSERKER, pos=(1, 2), hp=120, max_hp=120, attack=16),
            Companion("셰인", PRESET_SCOUT, pos=(1, 3), hp=80, max_hp=80, attack=10),
            Companion("가론", PRESET_GUARDIAN, pos=(1, 4), hp=140, max_hp=140, attack=12),
        ],
        player_pos=(0, 3),
        unexplored_pos=(8, 3),
    )


def _ascii(s: _Session) -> list[str]:
    """최소 2D 렌더 — @ 플레이어 / 동료 이름 첫 글자 / E 적 / · 미탐색."""
    grid = [["." for _ in range(_GRID_W)] for _ in range(_GRID_H)]
    w = s.world
    if w.unexplored_pos is not None:
        ux, uy = w.unexplored_pos
        if 0 <= ux < _GRID_W and 0 <= uy < _GRID_H:
            grid[uy][ux] = "·"
    px, py = w.player_pos
    if 0 <= px < _GRID_W and 0 <= py < _GRID_H:
        grid[py][px] = "@"
    for e in w.enemies:
        if e.hp > 0 and 0 <= e.pos[0] < _GRID_W and 0 <= e.pos[1] < _GRID_H:
            grid[e.pos[1]][e.pos[0]] = "E"
    for c in w.companions:
        cx, cy = c.pos
        if 0 <= cx < _GRID_W and 0 <= cy < _GRID_H:
            grid[cy][cx] = c.name[0]
    return ["".join(row) for row in grid]


class MemberView(BaseModel):
    name: str
    pos: tuple[int, int]
    hp: int
    max_hp: int
    order: str | None
    disposition: dict[str, int]


class EnemyView(BaseModel):
    name: str
    pos: tuple[int, int]
    hp: int


class RenderState(BaseModel):
    session_id: str
    tick: int
    party: list[MemberView]
    enemies: list[EnemyView]
    flags: dict[str, str]
    relationships: dict[str, int]
    branch: list[str]  # 분기점(일시정지 권장 — LLM 개입 후보)
    grid: list[str]
    log: list[str] = Field(default_factory=list)


def _render(sid: str, s: _Session, log: list[str] | None = None) -> RenderState:
    w = s.world
    return RenderState(
        session_id=sid,
        tick=w.tick,
        party=[
            MemberView(
                name=c.name, pos=c.pos, hp=c.hp, max_hp=c.max_hp,
                order=c.current_order.value if c.current_order else None,
                disposition={
                    "충성": c.disposition.loyalty, "저돌": c.disposition.aggression,
                    "지혜": c.disposition.wisdom, "변덕": c.disposition.whimsy,
                    "유대": c.disposition.bond,
                },
            )
            for c in w.companions
        ],
        enemies=[EnemyView(name=e.name, pos=e.pos, hp=e.hp) for e in w.enemies if e.hp > 0],
        flags=dict(s.memory.flags),
        relationships=dict(s.memory.relationships),
        branch=[r.value for r in detect_branch(w)],
        grid=_ascii(s),
        log=log or [],
    )


def _get(sid: str) -> _Session:
    s = _SESSIONS.get(sid)
    if s is None:
        raise HTTPException(status_code=404, detail=f"세션 없음: {sid}")
    return s


@router.post("/session/start", response_model=RenderState)
async def start() -> RenderState:
    """새 RTwP 세션 — 파티 3명 + 세계 생성."""
    sid = _new_id()
    _SESSIONS[sid] = _Session(world=_new_party())
    return _render(sid, _SESSIONS[sid], ["성지를 나선 일행이 미궁 1층 입구에 들어섰다."])


class TickRequest(BaseModel):
    session_id: str
    steps: int = Field(default=1, ge=1, le=20)
    spawn_enemy: bool = False  # 데모용 — 적 출현 트리거


@router.post("/session/tick", response_model=RenderState)
async def tick(req: TickRequest) -> RenderState:
    """평소 진행 — 파티가 성향대로 자율(★ 코드 0토큰). 분기점이면 branch에 표시."""
    from service.sim.disposition_tick import TickEnemy

    s = _get(req.session_id)
    log: list[str] = []
    if req.spawn_enemy and not s.world.enemies:
        s.world.enemies = [TickEnemy("고블린", pos=(7, 3), hp=40)]
        log.append("고블린이 어둠 속에서 모습을 드러냈다!")
    for _ in range(req.steps):
        results = party_step(s.world)
        log.extend(r.note for r in results if r.note.split(": ", 1)[-1])
    return _render(req.session_id, s, log[-8:])


class CommandRequest(BaseModel):
    session_id: str
    target: str = "all"  # "all" 또는 동료 이름
    text: str = Field(..., min_length=1, max_length=300)
    situation: str = Field(default="", max_length=300)


@router.post("/session/command", response_model=RenderState)
async def command(req: CommandRequest) -> RenderState:
    """일시정지 + 자연어 지시 — 성향 통과(순응/변형/거부, Phase 1 LLM)."""
    s = _get(req.session_id)
    log: list[str] = []
    sit = req.situation or ("전투 중" if s.world.enemies else "탐험 중")
    if req.target == "all":
        out = command_all(s.world, req.text, sit)
        for name, resp in out.items():
            log.append(f"{name}: 「{resp.reaction.value}」 {resp.speech}")
    else:
        one = command_member(s.world, req.target, req.text, sit)
        if one is None:
            raise HTTPException(status_code=404, detail=f"동료 없음: {req.target}")
        log.append(f"{req.target}: 「{one.reaction.value}」 {one.speech}")
    return _render(req.session_id, s, log)


class EventRequest(BaseModel):
    session_id: str
    action: str = Field(..., min_length=1, max_length=200)
    outcome: str = Field(default="", max_length=200)
    subject: str = Field(..., min_length=1, max_length=60)


@router.post("/session/event", response_model=RenderState)
async def event(req: EventRequest) -> RenderState:
    """중요 사건의 영구성 판정(Phase 2) → 세계에 남김. 재방문/재등장에 반영."""
    s = _get(req.session_id)
    rec = judge_permanence(req.action, req.outcome)
    rec.subject = req.subject
    recorded = record(s.memory, rec)
    att = npc_attitude(s.memory, req.subject).value
    note = "영구히 남았다" if recorded else "스쳐 지나갔다(일회성)"
    return _render(req.session_id, s, [f"{req.action} — {note}. [{req.subject}: {att}]"])


@router.get("/session/{sid}", response_model=RenderState)
async def get_state(sid: str) -> RenderState:
    """현재 렌더 상태."""
    return _render(sid, _get(sid))
