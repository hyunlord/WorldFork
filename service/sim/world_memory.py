"""V3 Phase 2 — 영구 세계 (자유 행동이 세계에 남는다).

DESIGN_disposition_engine.md 4장. 자유 행동·지시 결과 중 '중요한 것'만 세계에 영구히
남긴다 — world flags(세계 변화), npc memory(NPC가 기억하는 사건), relationship(관계).
일회성(이번 전투 버프·잡몹 처치)은 휘발. ★ LLM은 '무엇이 영구인지' 판정만 하고, 기록은
코드(결정적)가 한다 — 안정. LLM 실패 시 결정적 키워드 휴리스틱 폴백.

재등장 시 코드가 반영: NPC 태도(배신 → 적대), 세계(무너진 천장 → 막힘), 관계 누적.
Phase 0/1 토대 위 — 성향 자율(0)·지시 해석(1)의 결과가 여기로 흘러들어 영구가 된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.llm.client import LLMError, Prompt
from core.llm.local_client import LocalLLMClient, pivotal_gm_client

# 관계 점수 범위(-100 적대 ~ +100 헌신).
_REL_MIN, _REL_MAX = -100, 100
# 세계 막힘 신호어 — flag 값에 이 중 하나라도 포함되면 통행 불가(LLM 서술형도 포착).
_BLOCKED_WORDS = ("무너", "붕괴", "막힘", "막혔", "폐쇄", "차단", "blocked")
# 결정적 폴백 — 영구로 남길 만한 사건의 신호어.
_PERMANENT_WORDS = ("무너", "붕괴", "파괴", "불태", "배신", "약속", "맹세", "구원", "살려", "죽")
_BETRAY_WORDS = ("배신", "공격", "버리", "죽이", "속였")


class PermanenceKind(StrEnum):
    """영구 기록의 종류."""

    FLAG = "flag"  # 세계 변화(무너진 천장 등)
    MEMORY = "memory"  # NPC가 기억하는 사건
    RELATIONSHIP = "relationship"  # 관계 변화
    NONE = "none"  # 영구 아님(휘발)


class Attitude(StrEnum):
    """재등장 NPC의 태도 — 관계·기억으로 코드가 결정."""

    HOSTILE = "hostile"
    WARY = "wary"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    DEVOTED = "devoted"


@dataclass
class PermanenceRecord:
    """LLM 판정 결과 — 영구 여부 + 무엇을 어떻게 남길지."""

    permanent: bool
    kind: PermanenceKind
    subject: str  # NPC명 / 장소 / 동료
    content: str  # 남길 한 줄(예: "비요른에게 배신당함")
    relationship_delta: int = 0  # RELATIONSHIP일 때 관계 증감


@dataclass
class WorldState:
    """영구 세계 상태 — 결정적 코드. 선택적 영구(핵심만)로 폭발 방지."""

    flags: dict[str, str] = field(default_factory=dict)  # 장소/사건 → 상태
    npc_memories: dict[str, list[str]] = field(default_factory=dict)  # NPC → 기억
    relationships: dict[str, int] = field(default_factory=dict)  # 이름 → 점수


def _clamp(v: int) -> int:
    return max(_REL_MIN, min(_REL_MAX, v))


def record(world: WorldState, rec: PermanenceRecord) -> bool:
    """영구 기록을 코드 상태에 반영. 휘발(NONE/비영구)은 무시. 기록했으면 True.

    ★ 선택적 영구 — permanent=False 또는 kind=NONE이면 세계에 남기지 않는다(폭발 방지).
    """
    if not rec.permanent or rec.kind is PermanenceKind.NONE:
        return False
    if rec.kind is PermanenceKind.FLAG:
        world.flags[rec.subject] = rec.content
    elif rec.kind is PermanenceKind.MEMORY:
        world.npc_memories.setdefault(rec.subject, []).append(rec.content)
    elif rec.kind is PermanenceKind.RELATIONSHIP:
        world.relationships[rec.subject] = _clamp(
            world.relationships.get(rec.subject, 0) + rec.relationship_delta
        )
        if rec.content:
            world.npc_memories.setdefault(rec.subject, []).append(rec.content)
    return True


# ─── 재등장 반영 (과거 → 나중 의미) ──────────────────────────────────────────────
def npc_attitude(world: WorldState, npc: str) -> Attitude:
    """재등장 NPC 태도 — 관계 점수 + 기억(배신 등)으로 코드가 결정."""
    score = world.relationships.get(npc, 0)
    mems = world.npc_memories.get(npc, [])
    betrayed = any(any(w in m for w in _BETRAY_WORDS) for m in mems)
    if betrayed and score < 0:
        return Attitude.HOSTILE
    if score <= -40:
        return Attitude.HOSTILE
    if score < 0:
        return Attitude.WARY
    if score >= 60:
        return Attitude.DEVOTED
    if score >= 20:
        return Attitude.FRIENDLY
    return Attitude.NEUTRAL


def is_blocked(world: WorldState, location: str) -> bool:
    """세계 재방문 — 무너뜨린 천장 등으로 통행 불가인가(서술형 flag도 부분 매칭)."""
    val = world.flags.get(location, "")
    return any(w in val for w in _BLOCKED_WORDS)


def adjust_relationship(world: WorldState, name: str, delta: int, note: str = "") -> None:
    """성향 자율(Phase 0)·지시(Phase 1)의 누적을 관계로 — 동료 도움 등."""
    record(
        world,
        PermanenceRecord(True, PermanenceKind.RELATIONSHIP, name, note, delta),
    )


# ─── LLM 영구 판정 (무엇이 남나) ─────────────────────────────────────────────────
_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "permanent": {"type": "boolean"},
        "kind": {"type": "string", "enum": ["flag", "memory", "relationship", "none"]},
        "subject": {"type": "string", "maxLength": 60},
        "content": {"type": "string", "maxLength": 100},
        "relationship_delta": {"type": "integer", "minimum": -50, "maximum": 50},
    },
    "required": ["permanent", "kind", "subject", "content", "relationship_delta"],
    "additionalProperties": False,
}

_SYSTEM = (
    "너는 게임 세계의 '영구성 판정자'다. 방금 일어난 행동·결과가 세계에 영구히 남을 만한지 "
    "판정한다.\n"
    "영구(permanent=true): 세계 변화(천장 붕괴·다리 소실 → flag), NPC가 기억할 사건"
    "(배신·약속·구원 → memory), 관계 변화(우정·원한 → relationship).\n"
    "휘발(permanent=false, kind=none): 일회성(이번 전투 버프, 잡몹 처치, 평범한 이동).\n"
    "subject는 대상(NPC명/장소/동료). content는 남길 한 줄. relationship_delta는 "
    "relationship일 때만 -50~50(우호+/원한-). 핵심 사건만 영구로 — 남발 금지."
)


def judge_permanence(
    action: str,
    outcome: str,
    *,
    client: LocalLLMClient | None = None,
) -> PermanenceRecord:
    """행동·결과 → '영구인가' LLM 판정 (★ 중요 사건만, 개입/결정적 순간에 호출).

    LLM은 판정만, 기록은 record()(코드). LLM/파싱 실패 시 결정적 휴리스틱 폴백.
    """
    llm = client if client is not None else pivotal_gm_client()
    user = f"# 행동\n{action}\n# 결과\n{outcome}\nJSON으로 영구성 판정:"
    try:
        resp = llm.generate_json(
            Prompt(system=_SYSTEM, user=user),
            schema=_SCHEMA,
            max_tokens=160,
            temperature=0.2,
        )
        p = resp.parsed
        return PermanenceRecord(
            permanent=bool(p["permanent"]),
            kind=PermanenceKind(str(p["kind"])),
            subject=str(p["subject"]),
            content=str(p["content"]),
            relationship_delta=int(p["relationship_delta"]),
        )
    except (LLMError, KeyError, ValueError, TypeError):
        return _fallback(action, outcome)


def _fallback(action: str, outcome: str) -> PermanenceRecord:
    """결정적 폴백 — 신호어로 영구 여부 판정(LLM 없이 안정)."""
    text = f"{action} {outcome}"
    if not any(w in text for w in _PERMANENT_WORDS):
        return PermanenceRecord(False, PermanenceKind.NONE, "", "", 0)
    if any(w in text for w in _BETRAY_WORDS):
        # 배신 = 관계 변화 + 기억(record가 둘 다 반영).
        content = f"배신: {action}"[:100]
        return PermanenceRecord(True, PermanenceKind.RELATIONSHIP, "관련 인물", content, -40)
    if any(w in text for w in ("무너", "붕괴", "파괴", "불태")):
        return PermanenceRecord(True, PermanenceKind.FLAG, "해당 장소", "무너짐", 0)
    return PermanenceRecord(True, PermanenceKind.MEMORY, "관련 인물", action[:100], 0)
