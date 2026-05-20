"""Phase D — 9B intent classifier (자연어 → PlayerActionType + entity 추출).

Phase D step 5: entities (actor / location / item) 추출 추가.
confidence < 0.8 → free-form fallback.
async router에서 asyncio.to_thread 로 wrap 호출 (sync).
"""

from __future__ import annotations

from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import get_qwen35_9b_q3
from service.api.schemas.freeform_action import ExtractedEntities, IntentMatch
from service.sim.types import PlayerActionType

_ACTION_DESCRIPTIONS: dict[PlayerActionType, str] = {
    PlayerActionType.ACTIVATE_LIGHT: "횃불 / 정령 빛 활성화",
    PlayerActionType.MOVE: "sub_area 이동",
    PlayerActionType.EXPLORE: "현 위치 탐색",
    PlayerActionType.ATTACK: "전투 / 적 공격",
    PlayerActionType.ABSORB_ESSENCE: "정수 흡수 (★ 핵심)",
    PlayerActionType.USE_ITEM: "inventory 아이템 사용",
    PlayerActionType.OFFER_TO_STONE: "비석 공물 (균열 진입 준비)",
    PlayerActionType.ENTER_RIFT: "균열 포탈 진입",
    PlayerActionType.EXIT_RIFT: "균열 탈출",
    PlayerActionType.REST: "휴식 / HP 회복 시도",
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
    "한국어 게임 자연어 input의 best-match action 분류 + entity 추출 전문가. "
    "입력 의도가 action과 분명히 매칭 시 confidence ≥ 0.85. "
    "자유 행동(list의 어떤 action도 아님) 시 matched_action=null + confidence < 0.5. "
    "entities: actor(캐릭터/NPC name), location(장소 name), item(아이템/정수 name) 추출."
)

INTENT_CLASSIFY_USER_TEMPLATE = """\
PlayerActionType:
{action_list}

input: {user_input}

JSON 출력 (matched_action: list value 또는 null):"""

INTENT_CLASSIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "matched_action": {"type": ["string", "null"], "maxLength": 80},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string", "maxLength": 200},
        "entities": {
            "type": "object",
            "properties": {
                "actor": {"type": ["string", "null"], "maxLength": 100},
                "location": {"type": ["string", "null"], "maxLength": 100},
                "item": {"type": ["string", "null"], "maxLength": 100},
            },
            "required": ["actor", "location", "item"],
            "additionalProperties": False,
        },
    },
    "required": ["matched_action", "confidence", "reason", "entities"],
    "additionalProperties": False,
}


def classify_intent(user_input: str) -> IntentMatch:
    """9B sync 호출 (async router에서 asyncio.to_thread wrap)."""
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
        max_tokens=400,
        temperature=0.2,
    )
    parsed = response.parsed
    matched = parsed.get("matched_action")
    if matched is not None:
        try:
            PlayerActionType(matched)
        except ValueError:
            matched = None

    raw_entities = parsed.get("entities") or {}
    entities = ExtractedEntities(
        actor=raw_entities.get("actor") or None,
        location=raw_entities.get("location") or None,
        item=raw_entities.get("item") or None,
    )

    return IntentMatch(
        matched_action=matched,
        confidence=float(parsed["confidence"]),
        reason=str(parsed.get("reason", ""))[:200],
        entities=entities,
    )
