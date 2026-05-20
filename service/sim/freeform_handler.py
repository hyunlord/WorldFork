"""Phase D — 27B free-form fallback handler.

★ intent classifier 본 confidence < threshold 시 호출.
★ 27B narrative + state_delta json_schema 강제 생성.
"""

from __future__ import annotations

from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import get_qwen36_27b_q3
from service.api.schemas.freeform_action import StateDelta

FREEFORM_SYSTEM = (
    "한국 web novel '게임 속 바바리안으로 살아남기' 정합 DM. "
    "본인 자유 행동 본 본문 어조 narrative (★ 격식체 ~다 / ~니다) 본 생성. "
    "state_delta 본 minimal (★ Phase D base, 후속 phase 확장)."
)

FREEFORM_USER_TEMPLATE = """\
본인 행동: {user_input}
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


def freeform_action(
    user_input: str, rationale: str | None
) -> tuple[str, StateDelta]:
    """27B 본 sync 호출. (narrative, state_delta) 반환.

    async router 본 asyncio.to_thread 로 wrap.
    """
    client = get_qwen36_27b_q3()
    rationale_block = f"본인 의도: {rationale}\n" if rationale else ""
    prompt = Prompt(
        system=FREEFORM_SYSTEM,
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
