"""V3 Phase 1 — 지시 해석 (LLM 얹기, 비전 정수).

DESIGN_disposition_engine.md 3장. Phase 0 코드 토대(disposition.py) 위에서, 플레이어의
자연어 지시를 동료의 성향으로 해석해 순응(comply)/변형(adapt)/거부(refuse) 중 하나로
반응한다. ★ LLM은 '개입(지시) 시만' 호출 — 평소 틱은 Phase 0 코드(0토큰). 비용 설계.

변덕(whimsy) 축은 Phase 0에서 예약했던 것을 여기서 살린다 — 판정 temperature로 매핑해
예측 불가성을 준다(변덕↑ = 가끔 뜻밖). LLM 실패 시 결정적 성향 기반 폴백(크래시 금지).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from core.llm.client import LLMError, Prompt
from core.llm.local_client import LocalLLMClient, pivotal_gm_client
from service.sim.disposition import Companion, DispoAction

_HIGH = 60
_LOW = 40
# 위험 신호 — 결정적 폴백이 '거부' 근거로 쓰는 키워드(좁은 틈/함정/단독 진입 류).
_RISK_WORDS = ("틈", "함정", "혼자", "단독", "먼저 들어", "좁은", "독", "벼랑", "함부로")


class CommandReaction(StrEnum):
    """지시에 대한 성향 반응 (DESIGN 3장)."""

    COMPLY = "comply"  # 순응 — 지시대로
    ADAPT = "adapt"  # 변형 — 더 나은 방법
    REFUSE = "refuse"  # 거부 — 위험/성향 충돌


@dataclass
class CommandResponse:
    """지시 해석 결과 — 코드 반영용 행동 + 납득용 근거/발화."""

    reaction: CommandReaction
    action: DispoAction  # 코드 반영(틱 루프 order). 거부 시 follow(자기 판단).
    reason: str  # 성향 근거 한 줄("나는 신중하니…")
    speech: str  # 동료 1인칭 발화


_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reaction": {"type": "string", "enum": ["comply", "adapt", "refuse"]},
        "action": {
            "type": "string",
            "enum": ["charge", "ranged", "scout", "rescue", "follow", "hold"],
        },
        "reason": {"type": "string", "minLength": 2, "maxLength": 80},
        "speech": {"type": "string", "minLength": 2, "maxLength": 140},
    },
    "required": ["reaction", "action", "reason", "speech"],
    "additionalProperties": False,
}

_SYSTEM = (
    "너는 RPG 파티원의 '성향 판단'이다. 플레이어 지시를 동료의 성향으로 해석해 "
    "순응(comply)/변형(adapt)/거부(refuse) 중 하나로 반응한다.\n"
    "규칙: 충성 높거나 위험 낮으면 순응. 지혜 높아 더 나은 방법이 있으면 변형. "
    "지혜로 명백한 위험을 간파했고 충성이 낮거나, 성향과 정면 충돌하면 거부.\n"
    "action은 실제 취할 행동(charge 돌격 / ranged 원거리 / scout 정찰 / rescue 구원 / "
    "follow 곁 / hold 대기). 거부면 보통 follow(지시 무시·자기 판단).\n"
    "reason은 성향 근거 한 줄('나는 신중하니…'). speech는 1인칭 한국어 발화. "
    "거부·변형은 버그가 아니라 '성격'이다 — 근거가 납득되게."
)


def whimsy_temperature(whimsy: int) -> float:
    """변덕 축 → 판정 temperature. 낮으면 일관(0.3), 높으면 예측 불가(0.95)."""
    return round(0.3 + max(0, min(100, whimsy)) / 100 * 0.65, 3)


def _brief(comp: Companion) -> str:
    d = comp.disposition
    return (
        f"{comp.name} — 충성 {d.loyalty}, 저돌 {d.aggression}, 지혜 {d.wisdom}, "
        f"변덕 {d.whimsy}, 유대 {d.bond}. 배경: {d.background or '없음'}"
    )


def _fallback(comp: Companion, command: str) -> CommandResponse:
    """LLM 실패 시 결정적 성향 기반 폴백 — 크래시 금지(평소 코드 정신)."""
    d = comp.disposition
    risky = any(w in command for w in _RISK_WORDS)
    if risky and d.wisdom >= _HIGH and d.loyalty < 50:
        return CommandResponse(
            CommandReaction.REFUSE,
            DispoAction.FOLLOW,
            "위험을 직감해 따르지 않는다",
            "그 길은 냄새가 좋지 않소. 다른 수를 찾겠소.",
        )
    if d.wisdom >= _HIGH and d.loyalty < _HIGH:
        return CommandResponse(
            CommandReaction.ADAPT,
            DispoAction.SCOUT,
            "더 안전한 방법을 택한다",
            "그대로는 위험하오. 먼저 살펴보고 움직이겠소.",
        )
    return CommandResponse(
        CommandReaction.COMPLY,
        DispoAction.FOLLOW,
        "지시를 따른다",
        "알겠소. 그리하겠소.",
    )


def interpret_command(
    comp: Companion,
    command: str,
    situation: str,
    *,
    client: LocalLLMClient | None = None,
) -> CommandResponse:
    """자연어 지시 → 성향 통과 → 순응/변형/거부 (★ LLM, 개입 시만).

    client 미지정 시 pivotal_gm_client(Gemma). 변덕 축으로 temperature를 조절해
    예측 불가성을 준다. LLM/파싱 실패는 결정적 폴백으로 흡수(턴 진행 보장).
    """
    llm = client if client is not None else pivotal_gm_client()
    user = (
        f"# 동료\n{_brief(comp)}\n"
        f"# 상황\n{situation}\n"
        f"# 플레이어 지시\n{command}\n"
        "JSON으로 반응을 출력:"
    )
    try:
        resp = llm.generate_json(
            Prompt(system=_SYSTEM, user=user),
            schema=_SCHEMA,
            max_tokens=200,
            temperature=whimsy_temperature(comp.disposition.whimsy),
        )
        p = resp.parsed
        return CommandResponse(
            reaction=CommandReaction(str(p["reaction"])),
            action=DispoAction(str(p["action"])),
            reason=str(p["reason"]),
            speech=str(p["speech"]),
        )
    except (LLMError, KeyError, ValueError):
        return _fallback(comp, command)


def apply_order(comp: Companion, response: CommandResponse) -> None:
    """해석 결과를 동료에 반영 — 순응/변형은 order로 코드 틱 반영, 거부는 자율 유지."""
    if response.reaction is CommandReaction.REFUSE:
        comp.current_order = None  # 지시 무시 → 성향 자율(default_action)
    else:
        comp.current_order = response.action
