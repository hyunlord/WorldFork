"""Phase D — 27B free-form fallback handler.

Phase D step 5: entity context inject (canon_facts keyword match).
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
