"""Phase D — 9B intent classifier (자연어 → PlayerActionType + entity 추출).

Phase D step 5: entities (actor / location / item) 추출 추가.
confidence < 0.8 → free-form fallback.
async router에서 asyncio.to_thread 로 wrap 호출 (sync).
"""

from __future__ import annotations

import re
from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import get_qwen35_9b_q3
from service.api.schemas.freeform_action import ExtractedEntities, IntentMatch
from service.sim.llm_helpers import strip_thinking_tags
from service.sim.types import PlayerActionType

# ─── Mechanical 사전분류 (★ 원칙 #5: 0토큰 게이트) ────────────────────────────────
# 명백한 고빈도 행동은 6s LLM classify를 건너뛴다. 모호하면 None → LLM fall-through.
# 오탐 방지: 방위는 '쪽/으로/편' 접미(동료·동굴·서재 등 배제) + 이동 동사 동시 충족만.
_DIR_PATTERNS: tuple[tuple[str, str], ...] = (
    ("north", r"북(?:쪽|으로|편|녘|방)"),
    ("south", r"남(?:쪽|으로|편|녘|방)"),
    ("east", r"동(?:쪽|으로|편|녘|방)"),
    ("west", r"서(?:쪽|으로|편|녘|방)"),
)
_MOVE_VERB = re.compile(r"간다|가다|가자|이동|향해|향한|움직|걸어|걷는|나아간|들어간")
_REST_RE = re.compile(r"휴식|쉰다|쉬다|쉬어|쉬자|잠을 자|잔다|눕는다|드러눕")
# 공격 — 명확한 타격 동사만(handle_attack이 encounters+user_input으로 대상 결정, entity 불필요).
_ATTACK_RE = re.compile(
    r"공격|때리|때려|때린|벤다|베어|베고|찌르|찔러|찌른|휘두|휘둘|"
    r"내리치|내리친|내려치|내려친|짓밟|도끼로|주먹으로"
)
# 방어/회피/도주 맥락이면 공격 아님(오탐 차단 — flee/dodge는 별도 핸들러).
_NOT_ATTACK_RE = re.compile(r"피하|피한|막아|막은|방어|도망|달아|물러|숨어|숨는")
# 탐색 — 추천 버튼 다수("주변을 둘러본다/살핀다/탐색"). handle_explore는 entity 불필요.
_EXPLORE_RE = re.compile(r"둘러본|둘러보|살핀다|살펴본|살펴보|탐색|훑어본|훑어보|주위를 본")
# 대화 — "X에게 말을 건다/대화". handle_dialogue가 actor 없으면 현재 NPC 기본 선택.
_DIALOGUE_RE = re.compile(r"말을 건|말을 걸|말을 붙|대화를 시도|대화한다|대화를 건|이야기를 나눈")


def mechanical_classify(user_input: str) -> IntentMatch | None:
    """규칙 기반 0토큰 분류 — 명백한 행동만. 모호하면 None(LLM fall-through).

    ★ 도그푸딩 속도: classify_intent(9B JSON, ~6s prefill 바운드)가 매 턴 병목.
      방위 이동·휴식 등 패턴이 명확한 고빈도 행동을 LLM 없이 즉시 분류한다.
    """
    text = user_input.strip()
    # 방위 이동 — 방위 접미 + 이동 동사 동시. (동료/동굴 등은 '동쪽/동으로'와 불일치)
    if _MOVE_VERB.search(text):
        for direction, pat in _DIR_PATTERNS:
            if re.search(pat, text):
                return IntentMatch(
                    matched_action=PlayerActionType.MOVE.value,
                    confidence=0.95,
                    reason="기계 분류: 방위 이동",
                    entities=ExtractedEntities(direction=direction),
                )
    # 휴식 — entity 불필요, 패턴 명확.
    if _REST_RE.search(text):
        return IntentMatch(
            matched_action=PlayerActionType.REST.value,
            confidence=0.95,
            reason="기계 분류: 휴식",
        )
    # 공격 — 타격 동사 & 방어/회피 맥락 아님. 대상은 handle_attack이 결정(entity 불필요).
    if _ATTACK_RE.search(text) and not _NOT_ATTACK_RE.search(text):
        return IntentMatch(
            matched_action=PlayerActionType.ATTACK.value,
            confidence=0.95,
            reason="기계 분류: 공격",
        )
    # 대화 — 추천 버튼("X에게 말을 건다"). 공격 다음(전투 우선). actor 없으면 핸들러가 NPC 선택.
    if _DIALOGUE_RE.search(text):
        return IntentMatch(
            matched_action=PlayerActionType.DIALOGUE.value,
            confidence=0.9,
            reason="기계 분류: 대화",
        )
    # 탐색 — 추천 버튼("주변을 둘러본다/살핀다"). handle_explore는 entity 불필요.
    if _EXPLORE_RE.search(text):
        return IntentMatch(
            matched_action=PlayerActionType.EXPLORE.value,
            confidence=0.9,
            reason="기계 분류: 탐색",
        )
    return None

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
    PlayerActionType.ENTER_DUNGEON: (
        "미궁(던전) 1층 진입 — 성인식 후 첫 진입 또는 매월 자정 재진입"
        " ('미궁으로 들어간다/향한다', '던전 입장')"
    ),
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
    PlayerActionType.EQUIP: "장비 착용 (무기/방어구/장신구 슬롯에 장착)",
    PlayerActionType.UNEQUIP: "장비 해제 (착용 중인 장비 분리)",
    PlayerActionType.REMOVE_ESSENCE: "흡수한 정수 슬롯 제거 (비우기)",
    PlayerActionType.EXAMINE_STATS: "본인 능력치 / 레벨 / XP 확인",
    PlayerActionType.MOVE_CHAMBER: "균열 내 챔버 이동 (★ 다음 구역 / 보스룸 진입)",
}


def build_action_list_text() -> str:
    return "\n".join(
        f"- {k.value}: {v}" for k, v in _ACTION_DESCRIPTIONS.items()
    )


INTENT_CLASSIFY_SYSTEM = (
    "/no_think\n"
    "한국어 게임 자연어 input의 best-match action 분류 + entity 추출 전문가. "
    "입력 의도가 action과 분명히 매칭 시 confidence ≥ 0.85. "
    "자유 행동(list의 어떤 action도 아님) 시 matched_action=null + confidence < 0.5. "
    "entities: actor(캐릭터/NPC name), location(장소 name), item(아이템/정수 name), "
    "direction(이동 방향 — north/south/east/west 중 하나 또는 null) 추출."
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
                "direction": {
                    "type": ["string", "null"],
                    "enum": ["north", "south", "east", "west", None],
                },
            },
            "required": ["actor", "location", "item", "direction"],
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
    # Fallback strip: local_client 단계 strip 이후에도 잔존 시 재파싱
    clean_text = strip_thinking_tags(response.text)
    if clean_text != response.text:
        import json as _json
        try:
            parsed: dict[str, Any] = _json.loads(clean_text)
        except _json.JSONDecodeError:
            parsed = response.parsed
    else:
        parsed = response.parsed
    matched = parsed.get("matched_action")
    if matched is not None:
        try:
            PlayerActionType(matched)
        except ValueError:
            matched = None

    raw_entities = parsed.get("entities") or {}
    raw_dir = raw_entities.get("direction") or None
    direction: str | None = (
        raw_dir if raw_dir in ("north", "south", "east", "west") else None
    )
    entities = ExtractedEntities(
        actor=raw_entities.get("actor") or None,
        location=raw_entities.get("location") or None,
        item=raw_entities.get("item") or None,
        direction=direction,
    )

    return IntentMatch(
        matched_action=matched,
        confidence=float(parsed["confidence"]),
        reason=str(parsed.get("reason", ""))[:200],
        entities=entities,
    )
