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
    scene_details,
)
from service.sim.scene_effect import _POLICY, BEAT_THRESHOLD, map_effect, pull_flavor
from service.sim.status import StatusEffect, StatusType
from service.sim.world_memory import WorldState, adjust_relationship

# ★ A3.2: 이진 진입어 게이트 폐기 — DUNGEON_ENTRY 전환은 누적 progress 임계(BEAT_THRESHOLD)로.
#   레일 완전 해체: 어떤 단일 입력도 강제 전진시키지 않고, 활동이 쌓여 자연히 끌려간다(끌개).
# 첫 조우 회피·도주 대안 exit — 전투를 피하는 선택도 마무리로 전진(막다른 길 0).
_FLEE_WORDS = ("도망", "도주", "물러", "달아", "후퇴", "피한다", "피해", "회피", "빠져나")

# ★ 코드 선택지 id → 효과 분류(0토큰, 결정적) — 라벨 NL 분류에 의존하지 않게(예: "미궁 깊숙이
#   나아간다"엔 방위가 없어 mechanical move 미분류). 선택지는 코드 정의 = 효과도 코드가 안다.
_CHOICE_INTENT: dict[str, str] = {
    "advance": "move",  # 전진 = 주 동력
    "guard": "move",  # 경계하며 전진
    "descend": "move",  # 더 깊은 곳으로
    "scout": "explore",  # 둘러보기
    "talk": "dialogue",  # 동료와 한마디
    # loot("…챙긴다")은 라벨이 take 키워드로 잡힘 — 매핑 불필요.
}

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
    # A3.1 — 비트별 누적 진행도(끌개 토대, 전환 사용은 A3.2) + 공개된 장면 디테일(반복 방지).
    scene_progress: dict[str, int] = field(default_factory=dict)
    discovered: dict[str, list[str]] = field(default_factory=dict)
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


def _apply_delta(
    s: _GMSession, result: GMBeatResult, *, suppress_inventory: bool = False
) -> None:
    """GM 서사 델타 반영 — ★ 관계(영구)·서사 아이템만. flags/HP/무기/전환은 코드 소관(GM 불가).

    비트 전환은 코드 exit(_advance_if_done), HP/무기/소지금은 코드. GM은 서술 + 관계/아이템만.
    suppress_inventory: 코드 효과(take)가 이미 아이템을 부여한 턴 → GM inventory_add 무시
    (코드 권위 — 같은 물건 이중 부여 차단, A3.1).
    """
    d = result.state_delta
    for name, delta in d.relationship_delta.items():
        adjust_relationship(s.world, name, delta)  # 관계는 영구(PERSISTENT)
    if not suppress_inventory:
        s.items.extend(d.inventory_add)  # PER-RUN 서사 아이템(코드 미부여 턴만)
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


def _beat_done(s: _GMSession) -> bool:
    """★ A3.2 끌개 전환 판정 — 이벤트 게이트 OR 누적 progress 임계(둘 중 먼저). 코드 권위.

    - 성인식 → 미궁: 무기 확정(이벤트).
    - 미궁 → 첫 조우: scene_progress ≥ BEAT_THRESHOLD(누적 끌개 — 단일 입력 강제 전진 없음).
    - 첫 조우 → 마무리: 처치 OR 회피/도주(둘 다 전진 — 막다른 길 0).
    - 마무리 = 종착.
    """
    if s.beat is Beat.COMING_OF_AGE:
        return bool(s.weapon)  # 이벤트: 무기 확정
    if s.beat is Beat.DUNGEON_ENTRY:
        thr = BEAT_THRESHOLD.get(Beat.DUNGEON_ENTRY, 100)
        return s.scene_progress.get(s.beat.value, 0) >= thr  # 누적 끌개
    if s.beat is Beat.FIRST_ENCOUNTER:
        return (
            s.run_flags.get("first_foe_resolved") == "true"
            or s.run_flags.get("encounter_avoided") == "true"  # 회피/도주 대안 exit
        )
    return False  # AFTERMATH = 종착


def _advance_if_done(s: _GMSession, action: str, intent: IntentMatch | None) -> None:
    """전환 조건 충족 시 next_beat로만 진행(끌개 순서 보존: 건너뛰기·역행 차단)."""
    if not _beat_done(s):
        return
    if s.beat is Beat.COMING_OF_AGE:
        s.run_flags["rite_passed"] = "true"  # 코드가 성인식 완료를 기록(GM 아님)
    if s.beat is Beat.DUNGEON_ENTRY:
        s.run_flags["entered_floor1"] = "true"
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


def _discovered_texts(s: _GMSession, *, exclude: set[str] | None = None) -> list[str]:
    """이미 공개된 디테일의 서술 텍스트(반복 방지 프롬프트용). exclude=이번 턴 공개분."""
    seen = set(s.discovered.get(s.beat.value, [])) - (exclude or set())
    return [d.detail for d in scene_details(s.beat) if d.key in seen]


def _is_flee(action: str) -> bool:
    """첫 조우 회피/도주 의도(0토큰 키워드) — 전투 대신 마무리로 전진하는 대안 exit(A3.2)."""
    return any(w in action for w in _FLEE_WORDS)


def _run_beat(
    s: _GMSession,
    action: str,
    confirmed: list[str] | None = None,
    discovered: list[str] | None = None,
    *,
    pull: str | None = None,
    suppress_inventory: bool = False,
) -> None:
    """GM 한 비트 호출 → state_delta 반영. 호출자가 _render.

    confirmed: 자유 행동의 코드 확정 효과(A3.1, 서술만). discovered: 이미 공개된 디테일(반복 방지).
    pull: 끌개 견인 힌트(A3.2). suppress_inventory: 코드 take가 아이템 준 턴 → GM 인벤 무시.
    """
    result = gm_beat(
        s.beat,
        hp=s.hp,
        max_hp=s.max_hp,
        weapon=s.weapon,
        stones=s.inv.stones,
        flags=dict(s.run_flags),
        history="\n".join(s.history),
        action=action,
        confirmed=confirmed,
        discovered=discovered,
        pull=pull,
    )
    _apply_delta(s, result, suppress_inventory=suppress_inventory)


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


def _apply_scene_effect(
    s: _GMSession, action: str, intent: IntentMatch | None
) -> tuple[list[str], bool]:
    """A3.1 — 자유 행동을 코드 확정 효과로 환원·적용 → (confirmed 라인, 아이템 부여 여부).

    progress(단조)·discovered·서사 아이템·관계만 코드가 바꾼다. hp/무기/flags/전환/stones는
    여전히 코드 소관(여기서 안 건드림). 전환 판정은 호출자가 _advance_if_done로(A3.1 이진).
    """
    key = s.beat.value
    seen = s.discovered.setdefault(key, [])
    eff = map_effect(
        intent,
        action,
        s.beat,
        seen,
        kaira_name=s.kaira.name if kaira_present(s.beat) else "",
    )
    s.scene_progress[key] = s.scene_progress.get(key, 0) + eff.progress_delta  # 단조 누적
    seen.extend(eff.newly_discovered)
    s.items.extend(eff.inventory_add)
    for name, delta in eff.relationship_delta.items():
        adjust_relationship(s.world, name, delta)  # 관계(영구)
    # ★ soft-floor(no-stuck 보강) — progress-gated 비트에서 정체(새 발견 0·비전진) 연속 시 가속.
    #   단조 유지(progress 증가만). 정체가 아니면 카운터 리셋.
    if s.beat in BEAT_THRESHOLD:
        skey = f"stall_{key}"
        stalled = (not eff.newly_discovered) and eff.progress_delta < _POLICY.advance
        if stalled:
            n = int(s.run_flags.get(skey, "0")) + 1
            if n >= _POLICY.stall_after:
                s.scene_progress[key] += _POLICY.stall_bump  # 막다른 길 0 — 끌개로 가속
                n = 0
            s.run_flags[skey] = str(n)
        else:
            s.run_flags[skey] = "0"
    s.run_flags["scene_progress"] = str(s.scene_progress[key])  # 가시화(가속 반영 후)
    return list(eff.confirmed_lines), bool(eff.inventory_add)


def _kaira_confirmed_line(s: _GMSession) -> str | None:
    """직전 카이라 성향 반응을 GM 서술용 확정 라인으로(comply/adapt/refuse가 서술에 닿게)."""
    r = s.last_reaction
    if r is None or not r.speech:
        return None
    return f"{s.kaira.name}({r.reaction.value}): {r.speech}"


def _weapon_from_text(text: str) -> str | None:
    """자유 텍스트에서 성인식 무기 명명 인식(A3.2 — choice_id 외 자유 입력도 무기 확정 허용)."""
    for w in COMING_OF_AGE_WEAPONS:
        if w.label in text:
            return w.label
    if "도끼" in text:
        return "양손도끼"
    if "망치" in text:
        return "양손망치"
    if "대검" in text or "검을" in text or "검을 든" in text:
        return "대검"
    return None


def _resolve_weapon(s: _GMSession, req: ActRequest, action: str) -> None:
    """성인식 무기 확정(코드 권위) — 선택지 id 또는 자유 텍스트 명명. 이미 확정이면 무시."""
    if s.beat is not Beat.COMING_OF_AGE or s.weapon:
        return
    if req.choice_id:
        weapon = next((w for w in COMING_OF_AGE_WEAPONS if w.id == req.choice_id), None)
        if weapon is not None:
            s.weapon = weapon.label
    elif req.free_text.strip():
        wl = _weapon_from_text(action)
        if wl is not None:
            s.weapon = wl  # ★ 자유 텍스트 무기 명명 허용(A3.2)


def _scene_turn(
    s: _GMSession, req: ActRequest
) -> tuple[str, list[str], list[str], bool, str | None]:
    """비전투 한 턴 — (action, confirmed, discovered_texts, suppress_gm_inventory, pull).

    행동 확정(무기) → 코드 효과 적용(현 비트) → 누적 끌개 전환(A3.2) → 카이라 성향 반응 →
    confirmed(효과+카이라). 플레이어 행동을 history에 누적(coherence). GM은 호출자가 _run_beat.
    """
    action = _action_text(s, req)
    _resolve_weapon(s, req, action)  # ★ 무기는 코드 확정(GM 아님), 선택지·자유 텍스트 둘 다
    intent = _interpret(action, is_free=bool(req.free_text.strip()))
    if req.choice_id in _CHOICE_INTENT:  # 코드 선택지 → 효과 결정적 매핑(라벨 NL 의존 제거)
        intent = IntentMatch(
            matched_action=_CHOICE_INTENT[req.choice_id], confidence=0.99, reason="choice"
        )
    prior = set(s.discovered.get(s.beat.value, []))  # 이번 턴 공개분 제외용 스냅샷
    confirmed, gave_item = _apply_scene_effect(s, action, intent)  # 현 비트 효과(코드 파생)
    just = set(s.discovered.get(s.beat.value, [])) - prior  # 이번 턴 공개(confirmed에 이미 있음)
    _advance_if_done(s, action, intent)  # ★ A3.2 누적 progress 끌개 전환(이벤트 게이트 OR 임계)
    pull = pull_flavor(s.beat, s.scene_progress.get(s.beat.value, 0))  # 전환 후 비트의 견인 강도
    _kaira_react(s, action)  # 카이라 성향 반응(전환 후 비트 기준 — 합류 즉시 반응)
    kline = _kaira_confirmed_line(s)
    if kline is not None:
        confirmed.append(kline)  # GM이 카이라 반응을 '이미 한 말'로 서술
    s.history.append(f"> {action}")  # ★ 플레이어 행동 누적(현재 GM narration만 → 맥락 보강)
    s.history[:] = s.history[-_HISTORY_MAX:]
    return action, confirmed, _discovered_texts(s, exclude=just), gave_item, pull


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
    action_text = _action_text(s, req)
    combat = s.beat is Beat.FIRST_ENCOUNTER and s.foe is not None and s.foe.alive
    # 첫 조우 + 생존 적 → 내러티브 전투 라운드(코드 판정 + GM 서술). 단, 회피/도주는 대안 exit.
    if combat and not _is_flee(action_text):
        return _combat_round(s, req.session_id, action_text)
    if combat:  # 회피/도주 — 전투를 피해 마무리로 전진(막다른 길 0, A3.2)
        s.run_flags["encounter_avoided"] = "true"
        s.foe = None
    # 일반 비트 — 코드 효과 적용·누적 끌개 전환·카이라 반응 → GM이 확정 효과를 서술
    action, confirmed, discovered, gave_item, pull = _scene_turn(s, req)
    _run_beat(
        s,
        action=action,
        confirmed=confirmed or None,
        discovered=discovered or None,
        pull=pull,
        suppress_inventory=gave_item,
    )
    return _render(req.session_id, s)


@router.post("/session/act/stream")
async def act_stream(req: ActRequest) -> StreamingResponse:
    """★ narration 스트리밍 플레이 경로(/gm 페이지) — 체감 지연 완화.

    narration을 정제해 SSE ``data:{narration}``로 흘리고, 종료 후 파싱해 상태 반영한 최종
    렌더를 ``event: done``으로 보낸다. 전투면 코드 판정(권위) 먼저 → GM은 확정 결과 서술.
    비전투면 카이라 성향 반응을 GM 스트림과 병렬(지연 완화). 신뢰 파싱 경로는 비스트림 /act.
    """
    s = _get(req.session_id)
    action_text = _action_text(s, req)
    foe_live = s.beat is Beat.FIRST_ENCOUNTER and s.foe is not None and s.foe.alive
    combat = foe_live and not _is_flee(action_text)
    if foe_live and not combat:  # 회피/도주 — 전투를 피해 마무리로 전진(A3.2)
        s.run_flags["encounter_avoided"] = "true"
        s.foe = None
    # 비전투는 _scene_turn에서 효과 적용·전환·카이라 반응을 마치고 confirmed/discovered를 얻는다
    # (카이라 반응이 confirmed로 GM 서술에 닿게 — 스트림에서도 일관). 전투는 _gen에서 코드 판정.
    pull: str | None = None
    if combat:
        action = action_text
        scene_confirmed: list[str] = []
        discovered: list[str] = []
        gave_item = False
    else:
        action, scene_confirmed, discovered, gave_item, pull = _scene_turn(s, req)

    async def _gen() -> AsyncIterator[str]:
        confirmed: list[str] | None = scene_confirmed or None
        illust_fallback: str | None = None
        if combat:
            rr = await asyncio.to_thread(_apply_combat, s, action)  # 코드 판정(+카이라)
            confirmed, illust_fallback = rr.lines, rr.illustration

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
            discovered=discovered or None,
            pull=pull,
        ):
            buf.append(token)
            narr = extract_narration("".join(buf))
            if narr is not None and len(narr) > len(emitted):
                chunk = json.dumps({"narration": narr[len(emitted):]}, ensure_ascii=False)
                yield f"data: {chunk}\n\n"
                emitted = narr
        try:
            result = parse_beat_text("".join(buf))
        except (ValueError, json.JSONDecodeError):
            yield f"event: error\ndata: {json.dumps({'detail': '파싱 실패'})}\n\n"
            return
        if combat:
            _absorb_narration(s, result, illust_fallback or "ui_combat_bjorn_action")
        else:
            _apply_delta(s, result, suppress_inventory=gave_item)
        final = _render(req.session_id, s).model_dump()
        yield f"event: done\ndata: {json.dumps(final, ensure_ascii=False)}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/session/{sid}", response_model=GMRender)
async def get_state(sid: str) -> GMRender:
    """현재 서사 렌더."""
    return _render(sid, _get(sid))
