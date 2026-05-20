"""Phase D — 9B intent classifier (★ 자연어 → PlayerActionType match).

본 input 본 score 0.0-1.0 + matched_action (★ PlayerActionType value 또는
None). threshold 0.8 이상 intent path, 미만 free-form fallback.

★ LocalLLMClient.generate_json 는 sync. async router 본 asyncio.to_thread
로 wrap 호출.
"""

from __future__ import annotations

from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import get_qwen35_9b_q3
from service.api.schemas.freeform_action import IntentMatch
from service.sim.types import PlayerActionType

# 본 PlayerActionType 의 한국어 설명 (★ classifier prompt 본 사용).
_ACTION_DESCRIPTIONS: dict[PlayerActionType, str] = {
    PlayerActionType.ACTIVATE_LIGHT: "횃불 / 정령 빛 활성화",
    PlayerActionType.MOVE: "sub_area 이동",
    PlayerActionType.EXPLORE: "본 위치 탐색",
    PlayerActionType.ATTACK: "전투 / 적 공격",
    PlayerActionType.ABSORB_ESSENCE: "정수 흡수 (★ 핵심)",
    PlayerActionType.USE_ITEM: "inventory 아이템 사용",
    PlayerActionType.OFFER_TO_STONE: "비석 공물 (균열 진입 준비)",
    PlayerActionType.ENTER_RIFT: "균열 포탈 진입",
    PlayerActionType.EXIT_RIFT: "균열 탈출",
    PlayerActionType.REST: "본 자리 휴식 / HP 회복 시도",
    PlayerActionType.WAIT: "시간 흐름 (★ 행동 없음)",
    PlayerActionType.COMMUNICATE: "메시지 스톤 통신",
    PlayerActionType.FLEE: "전투 도주",
    PlayerActionType.ENTER_NEXT_FLOOR: "현재 층 → 다음 층 진행",
    PlayerActionType.EXIT_TO_PREV_FLOOR: "이전 층 복귀",
    PlayerActionType.EXCHANGE_MAGE_STONES: "마석 거래",
    PlayerActionType.WAIT_IN_VILLAGE: "마을 1일 대기 (HP/SP 회복)",
    PlayerActionType.ENTER_DUNGEON: "1층 재진입 (★ 매월 자정)",
    PlayerActionType.HEAL_AT_TEMPLE: "신전 치유",
    PlayerActionType.DIALOGUE: "NPC / 동료 대화",
    PlayerActionType.LIBRARY_SEARCH: "도서관 정보 조회",
    PlayerActionType.RECRUIT_FROM_GUILD: "길드 동료 영입",
    PlayerActionType.REJECT_DIALOGUE: "대화 거절",
    PlayerActionType.SHOP_SELL: "상점 판매",
    PlayerActionType.SHOP_BUY: "상점 구매",
    PlayerActionType.FORM_NIGHT_COMPANION: "야영 동료 결성",
    PlayerActionType.DISBAND_NIGHT_COMPANION: "야영 동료 해체",
    PlayerActionType.ENGAGE_BANDIT: "약탈자 교전",
    PlayerActionType.REST_AND_NIGHT_WATCH: "야영 + 야간 경계",
}


def build_action_list_text() -> str:
    return "\n".join(
        f"- {k.value}: {v}" for k, v in _ACTION_DESCRIPTIONS.items()
    )


INTENT_CLASSIFY_SYSTEM = (
    "한국어 게임 자연어 input 본 best-match action 분류 expert. "
    "본 입력 본 의도가 분명히 본 action 본 정합 시 confidence ≥ 0.85. "
    "본 입력 본 자유 행동 (★ 본 list 의 어떤 action 도 아닌 자유 행동) 본 "
    "matched_action=null + confidence < 0.5."
)

INTENT_CLASSIFY_USER_TEMPLATE = """\
본 PlayerActionType:
{action_list}

본 input: {user_input}

JSON 출력 (★ matched_action 본 본 list 의 value 또는 null):"""

INTENT_CLASSIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "matched_action": {"type": ["string", "null"], "maxLength": 80},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string", "maxLength": 200},
    },
    "required": ["matched_action", "confidence", "reason"],
    "additionalProperties": False,
}


def classify_intent(user_input: str) -> IntentMatch:
    """9B 본 sync 호출 (★ async router 본 asyncio.to_thread)."""
    client = get_qwen35_9b_q3()
    prompt = Prompt(
        system=INTENT_CLASSIFY_SYSTEM,
        user=INTENT_CLASSIFY_USER_TEMPLATE.format(
            action_list=build_action_list_text(),
            user_input=user_input,
        ),
    )
    response = client.generate_json(
        prompt,
        schema=INTENT_CLASSIFY_SCHEMA,
        max_tokens=300,
        temperature=0.2,
    )
    parsed = response.parsed
    matched = parsed.get("matched_action")
    # null / 본 PlayerActionType value 검증
    if matched is not None:
        try:
            PlayerActionType(matched)
        except ValueError:
            matched = None  # LLM 본 invalid value 본 → free-form 으로 분류
    return IntentMatch(
        matched_action=matched,
        confidence=float(parsed["confidence"]),
        reason=str(parsed.get("reason", ""))[:200],
    )
