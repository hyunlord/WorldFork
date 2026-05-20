"""Phase D — 27B free-form fallback handler + combat narrative.

Phase D step 5: entity context inject (canon_facts keyword match).
Phase D step 6b: compose_combat_narrative (sync, asyncio.to_thread 래핑 권장).
intent classifier confidence < threshold 시 호출.
async router에서 asyncio.to_thread로 wrap (sync).
"""

from __future__ import annotations

from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import get_qwen36_27b_q3
from service.api.schemas.freeform_action import ExtractedEntities, StateDelta
from service.canon.context import get_entity_index
from service.canon.entity_index import EntityRef
from service.sim.combat import CombatTurnLog

FREEFORM_SYSTEM_TEMPLATE = (
    "한국 web novel '게임 속 바바리안으로 살아남기' 정합 DM. "
    "자유 행동을 본문 어조 narrative(격식체 ~다/~니다)로 생성. "
    "{canon_context}"
    "state_delta는 minimal."
)

FREEFORM_USER_TEMPLATE = """\
행동: {user_input}
{rationale_block}
JSON 출력:"""

FREEFORM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narrative": {"type": "string", "minLength": 10, "maxLength": 2000},
        "state_delta": {
            "type": "object",
            "properties": {
                "hp_change": {"type": "integer", "minimum": -100, "maximum": 100},
                "inventory_add": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 100},
                    "maxItems": 10,
                },
                "inventory_remove": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 100},
                    "maxItems": 10,
                },
                "location": {"type": ["string", "null"], "maxLength": 100},
                "time_advance": {"type": "integer", "minimum": 0, "maximum": 24},
                "affinity_changes": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                },
            },
            "required": [
                "hp_change",
                "inventory_add",
                "inventory_remove",
                "location",
                "time_advance",
                "affinity_changes",
            ],
            "additionalProperties": False,
        },
    },
    "required": ["narrative", "state_delta"],
    "additionalProperties": False,
}


def _build_canon_context(refs: list[EntityRef]) -> str:
    if not refs:
        return ""
    lines = ["본문 정합 정보:"]
    for ref in refs:
        lines.append(f"- {ref.summary}")
    return "\n".join(lines) + "\n"


def _collect_entity_refs(
    user_input: str,
    extracted: ExtractedEntities | None,
) -> list[EntityRef]:
    """entity_index에서 관련 entity를 최대 5개 수집."""
    index = get_entity_index()
    if index is None:
        return []

    refs: list[EntityRef] = []
    seen: set[str] = set()

    def _add(ref: EntityRef | None) -> None:
        if ref is None:
            return
        key = f"{ref.entity_type}:{ref.name}"
        if key not in seen:
            seen.add(key)
            refs.append(ref)

    if extracted:
        for name in [extracted.actor, extracted.location, extracted.item]:
            if name:
                _add(index.lookup_by_name(name))

    for ref in index.keyword_match(user_input, limit=5):
        _add(ref)

    return refs[:5]


def freeform_action(
    user_input: str,
    rationale: str | None,
    extracted_entities: ExtractedEntities | None = None,
) -> tuple[str, StateDelta]:
    """27B sync 호출. (narrative, state_delta) 반환."""
    client = get_qwen36_27b_q3()

    refs = _collect_entity_refs(user_input, extracted_entities)
    canon_context = _build_canon_context(refs)

    system = FREEFORM_SYSTEM_TEMPLATE.format(canon_context=canon_context)
    rationale_block = f"의도: {rationale}\n" if rationale else ""

    prompt = Prompt(
        system=system,
        user=FREEFORM_USER_TEMPLATE.format(
            user_input=user_input,
            rationale_block=rationale_block,
        ),
    )
    response = client.generate_json(
        prompt,
        schema=FREEFORM_SCHEMA,
        max_tokens=1500,
        temperature=0.7,
    )
    parsed = response.parsed
    narrative = str(parsed["narrative"])
    delta = StateDelta.model_validate(parsed["state_delta"])
    return (narrative, delta)


# ─── combat narrative ──────────────────────────────────────────────────────────

_COMBAT_NARRATIVE_SYSTEM = (
    "한국 web novel '게임 속 바바리안으로 살아남기' 본문 어조 DM. "
    "전투 turn flow를 본문 어조 격식체(~다/~니다) narrative로 통합. "
    "RULE: turn flow 자연스럽게 연결, 4-6 문장 분량."
)

_COMBAT_NARRATIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narrative": {"type": "string", "minLength": 30, "maxLength": 1500},
    },
    "required": ["narrative"],
    "additionalProperties": False,
}


def compose_combat_narrative(
    player_log: CombatTurnLog,
    enemy_logs: list[CombatTurnLog],
    essence_drops: list[str],
) -> str:
    """27B 전투 narrative 생성 (sync). 실패 시 빈 문자열 반환."""
    try:
        client = get_qwen36_27b_q3()
        flow_lines: list[str] = []
        flow_lines.append(
            f"비요른 ({player_log.action_name}) → "
            f"{player_log.target_name} {player_log.damage_dealt} damage"
        )
        if player_log.enemy_resolved:
            flow_lines.append(f"{player_log.target_name} 쓰러짐")
        for log in enemy_logs:
            if log.damage_received > 0:
                line = f"{log.actor} ({log.action_name}) → 비요른 {log.damage_received} damage"
            else:
                line = f"{log.actor} ({log.action_name}) → {log.notes}"
            if log.status_applied:
                line += f" + {', '.join(log.status_applied)}"
            flow_lines.append(line)
        if essence_drops:
            flow_lines.append(f"drop: {', '.join(essence_drops)}")

        prompt = Prompt(
            system=_COMBAT_NARRATIVE_SYSTEM,
            user="전투 turn flow:\n" + "\n".join(flow_lines) + "\n\nnarrative 통합:",
        )
        response = client.generate_json(
            prompt,
            schema=_COMBAT_NARRATIVE_SCHEMA,
            max_tokens=600,
            temperature=0.7,
        )
        result = str(response.parsed.get("narrative", ""))
        return result if len(result) >= 30 else ""
    except Exception:
        return ""
