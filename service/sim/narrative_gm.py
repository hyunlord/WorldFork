"""구조화 서사 GM — narration / choices / state_delta (NARRATIVE_DESIGN §6·§8).

★ freeform 금지: GM은 캐논 앵커(opening_canon) + 현 상태에 고정되고, 매 출력에
state_delta(실제 상태를 구동)와 선택지 2~4개를 낸다. 모델은 pivotal_gm_client()
(현 라우팅 = Gemma) 재사용 — 포트 하드코딩 없음. 출력은 변환명(화면 unmask는 프론트).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import LocalLLMClient, pivotal_gm_client
from service.engine.content_pack import require_active_pack
from service.sim.opening_canon import Beat, anchor_for, build_anchor_prompt
from service.sim.rag_retrieval import get_grounding


def _grounding_enabled() -> bool:
    """RAG grounding on/off 토글 — env GM_GROUNDING=0이면 OFF(비교·안전용). 기본 ON."""
    return os.environ.get("GM_GROUNDING", "1") != "0"

# ★ A1.2: GM 시스템 프롬프트(페르소나+출력계약)·일러스트 화이트리스트는 콘텐츠팩 소유
#   (service/content/worldfork/pack.py). 엔진은 require_active_pack()으로 소비 — 원본 리터럴 제거.

_GM_USER = (
    "## 최근 흐름\n{history}\n\n"
    "## 현재 상태\n"
    "HP {hp}/{max_hp} · 무기 {weapon} · 소지금 {stones} 스톤 · flags {flags}\n\n"
    "{pull}"
    "{discovered}"
    "{confirmed}"
    "## 플레이어 행동\n{action}\n\n"
    "현 비트의 목표를 향해 장면을 진전시키고, 출력 계약대로 JSON을 낸다."
)

# A3.1 — 이미 공개된 장면 디테일(반복 방지 coherence). 있으면 '다음으로 진전' 지시.
_DISCOVERED_TEMPLATE = (
    "## 이미 드러난 것 (★ 다시 묘사하지 말고 다음으로 진전시켜라)\n{lines}\n\n"
)

# A3.2 — 끌개 견인 힌트(progress 차오를수록 강해짐). 서술에 녹여라(★ 수치·시스템 언급 금지).
_PULL_TEMPLATE = "## 끌림 (배경으로 녹여라 — 수치 언급 금지)\n{pull}\n\n"

# 전투 라운드 등 코드가 확정한 결과를 GM에 넘길 때의 블록(서술만, 새 수치 금지).
_CONFIRMED_TEMPLATE = (
    "## 확정 결과 (★ 이미 일어났다 — 그대로 서술만, 새 수치·아이템·결과를 만들지 마라)\n"
    "{lines}\n\n"
)

# A2.3 — RAG 원작 참조 주입 블록(passages 있을 때만). 캐논 앵커와 함께 배경·디테일 일관성용.
_GROUNDING_TEMPLATE = (
    "# 원작 참조 (배경·톤·디테일 일관성용 — ★ 복붙 금지, 새 고유명사 날조 금지)\n"
    "아래는 원작의 관련 대목이다. 세계·분위기·구체 디테일을 일관되게 하는 참고로만 쓰고, "
    "반드시 네 말로 새로 서술하라. ★ 현재 상태(플레이어 선택으로 갈린)와 충돌하면 현재 상태가 "
    "우선 — 참조는 배경·디테일에만 쓴다.\n{refs}\n\n"
)

# 원작 검색 범위·예산은 콘텐츠팩 소유(grounding_*) — A1.2 require_active_pack()으로 소비.
# 청크 보일러플레이트(URL·회차 헤더) 제거는 엔진 청소 메커니즘.
_URL_RE = re.compile(r"https?://\S+")
_WORK_HEADER_RE = re.compile(r"게임 속 .{0,24}?살아남기\s*-?\s*\d*\s*화?")
_CHAPTER_HEADER_RE = re.compile(r"\d+\s*화\s*[^\n]{0,30}?\(\d+\)")


def _clean_passage(text: str) -> str:
    """검색 passage 청소 — 사이트 URL·작품 회차 헤더·메타 제거(서술 노이즈 차단)."""
    text = _URL_RE.sub("", text)
    text = _WORK_HEADER_RE.sub("", text)
    text = _CHAPTER_HEADER_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _grounding_block(beat: Beat, action: str) -> str:
    """현 장면 컨텍스트로 RAG 검색 → 청소·예산 절단 → '# 원작 참조' 블록(없으면 빈 문자열).

    ★ get_grounding의 정식 소비처(GM). passages는 이미 마스킹(변환명) — prompt/로그 원작명 0.
    GM_GROUNDING=0이면 빈 블록(ungrounded — 비교·안전용).
    """
    if not _grounding_enabled():
        return ""
    pack = require_active_pack()
    budget = pack.grounding_char_budget
    scene = anchor_for(beat).scene
    query = f"{scene} {action}".strip()
    passages = get_grounding(
        query, episode_range=pack.grounding_episode_range, top_k=pack.grounding_top_k
    )
    refs: list[str] = []
    total = 0
    for p in passages:
        cleaned = _clean_passage(p.text)
        if len(cleaned) < 10:
            continue
        if total + len(cleaned) > budget:
            cleaned = cleaned[: max(0, budget - total)]
        if not cleaned:
            break
        refs.append(f"- {cleaned}")
        total += len(cleaned)
        if total >= budget:
            break
    return _GROUNDING_TEMPLATE.format(refs="\n".join(refs)) if refs else ""

_GM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narration": {"type": "string", "minLength": 20, "maxLength": 1600},
        "state_delta": {
            "type": "object",
            "properties": {
                "relationship_delta": {"type": "object"},
                "inventory_add": {"type": "array", "items": {"type": "string"}},
            },
        },
        "speaker": {"type": "string"},
        "illustration": {"type": "string"},
    },
    "required": ["narration"],
}

# 비트별 토큰 캡 — 구조화 출력(narration+choices+state_delta JSON 봉투)은 평문 서술보다
# 토큰이 더 든다. 캡이 낮으면 JSON이 잘려 파싱 실패 → 넉넉히. 전투·중대 장면은 더 길게.
_BEAT_MAX_TOKENS: dict[Beat, int] = {
    Beat.COMING_OF_AGE: 640,
    Beat.DUNGEON_ENTRY: 640,
    Beat.FIRST_ENCOUNTER: 896,
    Beat.AFTERMATH: 640,
}


def _max_tokens(beat: Beat) -> int:
    return _BEAT_MAX_TOKENS.get(beat, 320)


@dataclass
class GMStateDelta:
    """GM이 줄 수 있는 서사 변화 — 관계·서사 아이템만(★ flags·hp·무기는 코드 소관)."""

    relationship_delta: dict[str, int] = field(default_factory=dict)
    inventory_add: list[str] = field(default_factory=list)


@dataclass
class GMBeatResult:
    """GM 한 비트 출력 — 서술(+관계/아이템 델타·화자·일러스트). 선택지·진행은 코드."""

    narration: str
    state_delta: GMStateDelta
    speaker: str | None = None
    illustration: str | None = None  # 띄울 스틸 키(_ILLUSTRATIONS 검증 통과만)


def _coerce_int(value: object, default: int = 0) -> int:
    return int(value) if isinstance(value, (int, float)) else default


def parse_beat_result(parsed: dict[str, Any]) -> GMBeatResult:
    """GM JSON → 타입드 결과. 누락·이상치는 안전 기본값으로 좁힌다(freeform 방지)."""
    raw_delta = parsed.get("state_delta") or {}
    delta = GMStateDelta(
        relationship_delta={
            str(k): _coerce_int(v)
            for k, v in (raw_delta.get("relationship_delta") or {}).items()
        },
        inventory_add=[str(x) for x in (raw_delta.get("inventory_add") or [])],
    )
    raw_illust = parsed.get("illustration")
    keys = require_active_pack().illustration_keys  # 팩 소유 화이트리스트(환각 차단)
    illustration = str(raw_illust) if raw_illust and str(raw_illust) in keys else None
    return GMBeatResult(
        narration=str(parsed.get("narration", "")).strip(),
        state_delta=delta,
        speaker=str(parsed["speaker"]) if parsed.get("speaker") else None,
        illustration=illustration,
    )


def build_gm_prompt(
    beat: Beat,
    *,
    hp: int,
    max_hp: int,
    weapon: str,
    stones: int,
    flags: dict[str, str],
    history: str,
    action: str,
    confirmed: list[str] | None = None,
    discovered: list[str] | None = None,
    pull: str | None = None,
) -> Prompt:
    """캐논 앵커 고정 + 상태 주입 GM 프롬프트(비스트리밍/스트리밍 공용).

    confirmed: 코드가 확정한 결과(전투·자유 행동 효과) — 있으면 '서술만, 새 수치 금지'로 주입.
    discovered: 이미 공개된 장면 디테일(A3.1) — 있으면 '반복 말고 진전' 지시(coherence).
    pull: 끌개 견인 힌트(A3.2) — progress 차오를수록 [목표]가 강하게 다가오게 서술시킨다.
    """
    confirmed_block = (
        _CONFIRMED_TEMPLATE.format(lines="\n".join(f"- {ln}" for ln in confirmed))
        if confirmed
        else ""
    )
    discovered_block = (
        _DISCOVERED_TEMPLATE.format(lines="\n".join(f"- {ln}" for ln in discovered))
        if discovered
        else ""
    )
    pull_block = _PULL_TEMPLATE.format(pull=pull) if pull else ""
    pack = require_active_pack()  # GM 페르소나·일러스트 화이트리스트는 팩 소유(A1.2)
    return Prompt(
        system=pack.gm_system_persona.format(
            anchor=build_anchor_prompt(beat, weapon=weapon),
            grounding=_grounding_block(beat, action),  # ★ A2.3 RAG 원작 참조
            illustrations=", ".join(sorted(pack.illustration_keys)),
        ),
        user=_GM_USER.format(
            history=history or "(시작)",
            hp=hp,
            max_hp=max_hp,
            weapon=weapon or "맨손",
            stones=stones,
            flags=flags or {},
            pull=pull_block,
            discovered=discovered_block,
            confirmed=confirmed_block,
            action=action or "(장면을 연다)",
        ),
    )


def extract_narration(text: str) -> str | None:
    """누적 JSON에서 narration 값을 현재까지 디코드(스트리밍 점진 표시용).

    아직 닫히지 않은 문자열도 best-effort로 돌려준다(최종 정본은 parse_beat_text). 화면에
    narration이 흐르게 하는 용도 — 미완 escape는 잘라낸다.
    """
    key = text.find('"narration"')
    if key < 0:
        return None
    colon = text.find(":", key + len('"narration"'))
    if colon < 0:
        return None
    open_q = text.find('"', colon + 1)
    if open_q < 0:
        return None
    out: list[str] = []
    i = open_q + 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            if i + 1 >= n:
                break  # 미완 escape — 여기서 끊김
            nxt = text[i + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, nxt))
            i += 2
            continue
        if ch == '"':
            break  # 문자열 종료
        out.append(ch)
        i += 1
    return "".join(out)


def parse_beat_text(text: str) -> GMBeatResult:
    """누적 텍스트에서 JSON 본문을 관대하게 추출·파싱(스트리밍 종료 후 파싱용).

    스트리밍(astream)은 schema 가드가 없어 앞뒤 잡소리가 섞일 수 있다 — 첫 '{'~마지막 '}'만 파싱.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"JSON 본문 없음: {text[:120]}")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("JSON 객체 아님")
    return parse_beat_result(parsed)


def gm_beat(
    beat: Beat,
    *,
    hp: int,
    max_hp: int,
    weapon: str,
    stones: int,
    flags: dict[str, str],
    history: str,
    action: str,
    confirmed: list[str] | None = None,
    discovered: list[str] | None = None,
    pull: str | None = None,
    client: LocalLLMClient | None = None,
) -> GMBeatResult:
    """현 비트를 한 번 진전 — 구조화 출력(guided JSON, 신뢰 경로).

    confirmed: 전투·자유 행동 코드 확정 결과(서술만). discovered: 이미 공개된 디테일(반복 방지).
    pull: 끌개 견인 힌트(A3.2). client 미지정 시 pivotal_gm_client()(현 라우팅 = Gemma).
    """
    cli = client or pivotal_gm_client()
    prompt = build_gm_prompt(
        beat, hp=hp, max_hp=max_hp, weapon=weapon, stones=stones,
        flags=flags, history=history, action=action, confirmed=confirmed,
        discovered=discovered, pull=pull,
    )
    resp = cli.generate_json(
        prompt, schema=_GM_SCHEMA, max_tokens=_max_tokens(beat), temperature=0.8
    )
    return parse_beat_result(resp.parsed)


async def astream_gm_beat(
    beat: Beat,
    *,
    hp: int,
    max_hp: int,
    weapon: str,
    stones: int,
    flags: dict[str, str],
    history: str,
    action: str,
    confirmed: list[str] | None = None,
    discovered: list[str] | None = None,
    pull: str | None = None,
    client: LocalLLMClient | None = None,
) -> AsyncIterator[str]:
    """현 비트를 토큰 스트리밍(체감 지연 완화) — 원시 토큰을 그대로 yield.

    구조화 파싱은 스트림 종료 후 parse_beat_text(누적)로 한다(스키마 가드 없음 — 신뢰 경로는
    gm_beat). 호출자가 토큰을 누적해 narration을 점진 표시(extract_narration)하고 끝에 파싱한다.
    confirmed: 코드 확정 결과(서술만). discovered: 이미 공개된 디테일. pull: 끌개 견인 힌트.
    """
    cli = client or pivotal_gm_client()
    prompt = build_gm_prompt(
        beat, hp=hp, max_hp=max_hp, weapon=weapon, stones=stones,
        flags=flags, history=history, action=action, confirmed=confirmed,
        discovered=discovered, pull=pull,
    )
    async for token in cli.astream(
        prompt, schema=_GM_SCHEMA, max_tokens=_max_tokens(beat), temperature=0.8
    ):
        yield token
