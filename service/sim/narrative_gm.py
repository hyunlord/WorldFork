"""구조화 서사 GM — narration / choices / state_delta (NARRATIVE_DESIGN §6·§8).

★ freeform 금지: GM은 캐논 앵커(opening_canon) + 현 상태에 고정되고, 매 출력에
state_delta(실제 상태를 구동)와 선택지 2~4개를 낸다. 모델은 pivotal_gm_client()
(현 라우팅 = Gemma) 재사용 — 포트 하드코딩 없음. 출력은 변환명(화면 unmask는 프론트).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import LocalLLMClient, pivotal_gm_client
from service.sim.opening_canon import Beat, build_anchor_prompt

_GM_SYSTEM = (
    "# 역할\n"
    "당신은 한국 web novel '게임 속 바바리안으로 살아남기' 세계의 게임 마스터(GM)다. "
    "장면을 1인칭('나는') 문어체 한국어로 펼치고, 플레이어의 선택을 받아 진전시킨다. "
    "메타·시스템·규칙 설명·AI 자칭·사과는 금지한다.\n\n"
    "# 톤\n"
    "냉소·실리주의 + 생존 긴장 + 바바리안 위장 코미디(우직한 야만인을 연기하나 속은 계산적). "
    "시스템 고지는 낫표 「」 합쇼체로 쓴다(예: 「성인식이 시작됩니다.」).\n\n"
    "# 캐논 고정\n"
    "아래 앵커만 근거로 삼는다. 근거 없는 새 고유명사·설정 확정은 금지.\n{anchor}\n\n"
    "# 끌개\n"
    "[목표]를 향해 부드럽게 견인하되 강제하지 않는다. 플레이어가 다른 길을 택하면 막지 말고 "
    "자연스럽게 이어 가되, 적절한 때 [목표]가 다른 형태로 다시 다가오게 한다.\n"
    "★ 플레이어가 무언가를 확정·획득·결정하면(예: 무기 선택, 처치, 합의) 그 변화를 반드시 "
    "state_delta(flags/inventory_add/relationship_delta)에 싣는다. 그리고 이 비트의 [목표]가 "
    "달성되면 scene_transition으로 다음 비트를 연다 — 같은 자리를 맴돌지 않는다.\n\n"
    "# 출력 계약 (엄수)\n"
    "- narration: 장면 서술(2~5문장, 전투·중대 장면은 더 길게 허용).\n"
    "- choices: 서로 결과가 다른 선택지 2~4개(겉만 다른 선택 금지). 각 {{id, label}}.\n"
    "- state_delta: 이 장면이 실제로 바꾸는 상태. flags(키:값 문자열), hp_change(정수), "
    "relationship_delta(이름:정수), inventory_add(문자열 배열), scene_transition(다음 비트로 "
    "넘어갈 때만 그 비트명). ★ 장식 금지 — 실제 변화가 있을 때만 채운다.\n"
    "- speaker: 핵심 화자 이름(포트레이트용, 없으면 생략)."
)

_GM_USER = (
    "## 최근 흐름\n{history}\n\n"
    "## 현재 상태\n"
    "HP {hp}/{max_hp} · 무기 {weapon} · 소지금 {stones} 스톤 · flags {flags}\n\n"
    "## 플레이어 행동\n{action}\n\n"
    "현 비트의 목표를 향해 장면을 진전시키고, 출력 계약대로 JSON을 낸다."
)

_GM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narration": {"type": "string", "minLength": 20, "maxLength": 1600},
        "choices": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["id", "label"],
            },
        },
        "state_delta": {
            "type": "object",
            "properties": {
                "flags": {"type": "object"},
                "hp_change": {"type": "integer"},
                "relationship_delta": {"type": "object"},
                "inventory_add": {"type": "array", "items": {"type": "string"}},
                "scene_transition": {"type": "string"},
            },
        },
        "speaker": {"type": "string"},
    },
    "required": ["narration", "choices", "state_delta"],
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
class GMChoice:
    """선택지 — 서로 결과가 다른 행동."""

    id: str
    label: str


@dataclass
class GMStateDelta:
    """이 비트가 구동하는 실제 상태 변화(장식 아님)."""

    flags: dict[str, str] = field(default_factory=dict)
    hp_change: int = 0
    relationship_delta: dict[str, int] = field(default_factory=dict)
    inventory_add: list[str] = field(default_factory=list)
    scene_transition: str | None = None


@dataclass
class GMBeatResult:
    """GM 한 비트 출력 — 서술 + 선택지 + 상태 변화(+화자)."""

    narration: str
    choices: list[GMChoice]
    state_delta: GMStateDelta
    speaker: str | None = None


def _coerce_int(value: object, default: int = 0) -> int:
    return int(value) if isinstance(value, (int, float)) else default


def parse_beat_result(parsed: dict[str, Any]) -> GMBeatResult:
    """GM JSON → 타입드 결과. 누락·이상치는 안전 기본값으로 좁힌다(freeform 방지)."""
    raw_delta = parsed.get("state_delta") or {}
    delta = GMStateDelta(
        flags={
            str(k): str(v) for k, v in (raw_delta.get("flags") or {}).items()
        },
        hp_change=_coerce_int(raw_delta.get("hp_change")),
        relationship_delta={
            str(k): _coerce_int(v)
            for k, v in (raw_delta.get("relationship_delta") or {}).items()
        },
        inventory_add=[str(x) for x in (raw_delta.get("inventory_add") or [])],
        scene_transition=(
            str(raw_delta["scene_transition"])
            if raw_delta.get("scene_transition")
            else None
        ),
    )
    choices = [
        GMChoice(str(c["id"]), str(c["label"]))
        for c in (parsed.get("choices") or [])
        if isinstance(c, dict) and c.get("id") and c.get("label")
    ]
    return GMBeatResult(
        narration=str(parsed.get("narration", "")).strip(),
        choices=choices,
        state_delta=delta,
        speaker=str(parsed["speaker"]) if parsed.get("speaker") else None,
    )


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
    client: LocalLLMClient | None = None,
) -> GMBeatResult:
    """현 비트를 한 번 진전 — 캐논 앵커 고정 + 상태 주입 → 구조화 출력.

    client 미지정 시 pivotal_gm_client()(현 라우팅 = Gemma). 포트 하드코딩 없음.
    """
    cli = client or pivotal_gm_client()
    prompt = Prompt(
        system=_GM_SYSTEM.format(anchor=build_anchor_prompt(beat, weapon=weapon)),
        user=_GM_USER.format(
            history=history or "(시작)",
            hp=hp,
            max_hp=max_hp,
            weapon=weapon or "맨손",
            stones=stones,
            flags=flags or {},
            action=action or "(장면을 연다)",
        ),
    )
    resp = cli.generate_json(
        prompt, schema=_GM_SCHEMA, max_tokens=_max_tokens(beat), temperature=0.8
    )
    return parse_beat_result(resp.parsed)
