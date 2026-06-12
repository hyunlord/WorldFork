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
from service.sim.dungeon_map import crystal_cave
from service.sim.party import (
    PartyWorld,
    command_all,
    command_member,
    detect_branch,
    party_step,
)
from service.sim.world_memory import WorldState, judge_permanence, npc_attitude, record

router = APIRouter(prefix="/api/v3", tags=["v3-rtwp"])

# 슬라이스 고정 타일맵(미궁 1층 수정 동굴) — 세션 공유. 충돌·광원의 단일 출처.
_MAP = crystal_cave()

# 적 종류 → 픽셀 스프라이트(public/assets/pixel/<sprite>.png). 미정의는 enemy 기본.
_ENEMY_SPRITE = {"고블린": "goblin", "노움": "gnome", "구울": "wraith"}

# DungeonView 범례 — 게임 화면 명칭(원작: 비요른). 동료/적은 일반 라벨(unmaskIp는 다음 단계).
_LEGEND: list[dict[str, str]] = [
    {"ch": "@", "type": "player", "label": "비요른"},
    {"ch": "n", "type": "npc", "label": "동료"},
    {"ch": "E", "type": "enemy", "label": "적"},
    {"ch": ">", "type": "stair", "label": "계단"},
]


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
    """파티 = 비요른(플레이어) + 투르윈/셰인/가론(V3 동료). 좌표는 수정 동굴 바닥에 배치."""
    stair = _MAP.stair()
    return PartyWorld(
        companions=[
            Companion("투르윈", PRESET_BERSERKER, pos=(1, 2), hp=120, max_hp=120, attack=16),
            Companion("셰인", PRESET_SCOUT, pos=(2, 2), hp=80, max_hp=80, attack=10),
            Companion("가론", PRESET_GUARDIAN, pos=(1, 3), hp=140, max_hp=140, attack=12),
        ],
        player_pos=(2, 3),
        unexplored_pos=stair,
        blocked=_MAP.is_blocked,
    )


def _dungeon(s: _Session) -> DungeonData:
    """탑다운 픽셀 렌더 데이터 — 타일맵 지형 위에 파티/적 엔티티를 얹는다.

    수정 광원 밖(is_lit=False)은 어둠(blank). 엔티티는 항상 표시(시야의 주체).
    """
    w = s.world
    # 엔티티 점유: (x, y) → (TileType, sprite). 동료가 플레이어와 겹치면 동료 우선.
    occ: dict[tuple[int, int], tuple[str, str]] = {w.player_pos: ("player", "player")}
    for c in w.companions:
        occ[c.pos] = ("npc", "npc")
    for e in w.enemies:
        if e.hp > 0:
            occ[e.pos] = ("enemy", _ENEMY_SPRITE.get(e.name, "enemy"))

    rows: list[list[TileModel]] = []
    for y in range(_MAP.height):
        row: list[TileModel] = []
        for x in range(_MAP.width):
            ent = occ.get((x, y))
            if ent is not None:
                row.append(TileModel(ch="@", type=ent[0], sprite=ent[1]))
                continue
            ch = _MAP.char(x, y)
            if _MAP.is_wall(x, y):
                row.append(
                    TileModel(ch="#", type="wall")
                    if _MAP.is_lit(x, y)
                    else TileModel(ch=" ", type="blank")
                )
            elif ch == ">":
                row.append(TileModel(ch=">", type="stair", sprite="stair"))
            elif _MAP.is_lit(x, y):
                row.append(TileModel(ch=".", type="floor"))
            else:
                row.append(TileModel(ch=" ", type="blank"))
        rows.append(row)
    return DungeonData(turn=w.tick, rows=rows, legend=_LEGEND)


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


class TileModel(BaseModel):
    """DungeonView 한 칸 — 프론트 components/game/types.ts Tile과 정합."""

    ch: str
    type: str  # wall/floor/player/enemy/npc/item/stair/door/blank
    sprite: str | None = None


class DungeonData(BaseModel):
    """탑다운 픽셀 렌더 데이터 — 프론트 DungeonViewData와 정합."""

    turn: int
    rows: list[list[TileModel]]
    legend: list[dict[str, str]] = Field(default_factory=list)


class RenderState(BaseModel):
    session_id: str
    tick: int
    party: list[MemberView]
    enemies: list[EnemyView]
    flags: dict[str, str]
    relationships: dict[str, int]
    branch: list[str]  # 분기점(일시정지 권장 — LLM 개입 후보)
    dungeon: DungeonData  # 탑다운 픽셀 렌더(ASCII 폐기)
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
        dungeon=_dungeon(s),
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
        s.world.enemies = [TickEnemy("고블린", pos=(9, 2), hp=40)]
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
