"""27B NPC dialogue narrative 생성 (sync, asyncio.to_thread 래핑 권장)."""

from __future__ import annotations

from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import get_qwen36_27b_q3

_DIALOGUE_SYSTEM = (
    "한국 web novel '게임 속 바바리안으로 살아남기' 본문 어조 narrative 생성. "
    "서사 규칙: 1인칭 시점('나는'/'내가' 사용), 문어체 어미(~다/~었다, ~니다/~습니다 금지), "
    "시스템 메시지만 「...」 안에 합쇼체 허용, 화자 prefix 금지. "
    "NPC 발화는 큰따옴표(\"...\")로 표기. "
    "NPC personality와 background를 반영한 3-5 문장 대화 narrative 생성."
)

_DIALOGUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narrative": {"type": "string", "minLength": 50, "maxLength": 800},
    },
    "required": ["narrative"],
    "additionalProperties": False,
}


def compose_dialogue_narrative(
    npc_name: str,
    npc_role: str | None,
    npc_background: str | None,
    user_input: str,
    role_tone_hint: str = "",
    race_ability_hint: str = "",
) -> str:
    """27B NPC 대화 narrative 생성 (sync). 실패 시 빈 문자열 반환.

    role_tone_hint — taxonomy role 정합 어조 (★ I-E2 정합).
    race_ability_hint — 종족 ability_tiers 특성 (★ I-G1 정합).
    """
    try:
        client = get_qwen36_27b_q3()
        info_lines = [f"NPC: {npc_name}"]
        if npc_role:
            info_lines.append(f"역할: {npc_role}")
        if role_tone_hint:
            info_lines.append(f"어조: {role_tone_hint}")
        if race_ability_hint:
            info_lines.append(f"종족 특성: {race_ability_hint}")
        if npc_background:
            info_lines.append(f"배경: {npc_background[:200]}")

        user_prompt = (
            "\n".join(info_lines)
            + f"\n\n플레이어 발화/행동: {user_input}\n\n대화 narrative:"
        )

        prompt = Prompt(system=_DIALOGUE_SYSTEM, user=user_prompt)
        response = client.generate_json(
            prompt,
            schema=_DIALOGUE_SCHEMA,
            max_tokens=400,
            temperature=0.7,
        )
        result = str(response.parsed.get("narrative", ""))
        return result if len(result) >= 50 else ""
    except Exception:
        return ""
