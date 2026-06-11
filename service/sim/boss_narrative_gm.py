"""균열 보스 등장 + chamber 진입 27B narrative 생성 (audit-3-3).

27B (qwen36_27b_q3) sync 호출 — asyncio.to_thread로 래핑 권장.
LLM 실패 시 호출자가 fallback 담당.
"""

from __future__ import annotations

from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import LocalLLMClient, get_qwen35_9b_q3, pivotal_gm_client
from service.canon.boss_narrative import (
    RIFT_NAMES,
    BossNarrativeContext,
    build_visual_clues,
    format_system_message,
)

_BOSS_NARRATIVE_SYSTEM = (
    "한국 web novel '게임 속 바바리안으로 살아남기' 본문 어조 narrative 생성. "
    "서사 규칙: 1인칭('나는'/'내가'), 문어체 어미(~다/~었다, ~니다 금지), "
    "시스템 메시지만 「...」 안에 합쇼체 허용. "
    "tier별 어조 지침:\n"
    "NORMAL — 효율 중심, 패턴 인지, '예상한 대로' 톤.\n"
    "VARIANT — 평소와 다름 인지, 상위 변이종 표현.\n"
    "HIDDEN — 전례 없는 어조, '9년 차 고인물인 나조차 한 번도 만나 보지 못했던', "
    "극악의 확률, 외형 단서 묘사.\n"
    "3-5 문장 + 마지막에 시스템 메시지 「...」 한 줄."
)

_BOSS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narrative": {"type": "string", "minLength": 50, "maxLength": 1500},
    },
    "required": ["narrative"],
    "additionalProperties": False,
}

_CHAMBER_SYSTEM = (
    "한국 web novel '게임 속 바바리안으로 살아남기' 본문 어조 narrative 생성. "
    "서사 규칙: 1인칭('나는'/'내가'), 문어체 어미(~다/~었다, ~니다 금지), "
    "시스템 메시지만 「...」 안에 합쇼체 허용. "
    "균열 내부 chamber 진입 시점. 2-4 문장. 분위기 위주."
)

_CHAMBER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narrative": {"type": "string", "minLength": 20, "maxLength": 800},
    },
    "required": ["narrative"],
    "additionalProperties": False,
}


def _running_client(pivotal: bool) -> LocalLLMClient:
    """기동 모델 라우팅 — 보스 등장(pivotal)=측정 우위 pivotal / chamber 진입(빈번)=9B 빠름.

    ★ pivotal은 공유 pivotal_gm_client(기본 27B Q2, PIVOTAL env로 가역).
    """
    if pivotal:
        return pivotal_gm_client()
    return get_qwen35_9b_q3()


def compose_boss_encounter_narrative_sync(ctx: BossNarrativeContext) -> str:
    """기동 모델(12B) 동기 호출 — tier별 보스 등장 narrative."""
    client = _running_client(pivotal=True)

    sys_msg = format_system_message(ctx.tier, ctx.rift_name, ctx.boss_name)
    grade_str = f"{ctx.boss_grade}등급" if ctx.boss_grade else "등급 미상"

    user_lines = [
        f"균열: {ctx.rift_name}",
        f"보스: {ctx.boss_name} ({grade_str})",
        f"tier: {ctx.tier.value}",
        f"변종 균열: {'YES' if ctx.is_variant_rift else 'NO'}",
    ]
    if ctx.visual_clues:
        user_lines.append("외형 단서:")
        for clue in ctx.visual_clues:
            user_lines.append(f"  - {clue}")
    user_lines.append(f"\n보스 조우 narrative + 마지막에 시스템 메시지: {sys_msg}")

    prompt = Prompt(system=_BOSS_NARRATIVE_SYSTEM, user="\n".join(user_lines))
    response = client.generate_json(
        prompt,
        schema=_BOSS_SCHEMA,
        max_tokens=600,
        temperature=0.7,
    )
    return str(response.parsed["narrative"])


def compose_chamber_entry_narrative_sync(
    rift_id: str,
    sub_area_id: str,
    sub_area_name: str,
    is_variant_rift: bool,
) -> str:
    """기동 모델(9B 빠름) 동기 호출 — chamber 진입 narrative."""
    client = _running_client(pivotal=False)

    rift_name = RIFT_NAMES.get(rift_id, rift_id)
    clues = build_visual_clues(rift_id, is_variant_rift)
    display_name = sub_area_name or sub_area_id

    user_lines = [
        f"균열: {rift_name}",
        f"챔버: {display_name} ({sub_area_id})",
        f"변종: {'YES' if is_variant_rift else 'NO'}",
    ]
    if clues:
        user_lines.append("외형 단서:")
        for c in clues:
            user_lines.append(f"  - {c}")
    user_lines.append("\n이 chamber 진입 시점 narrative (1인칭 문어체, 2-4 문장).")

    prompt = Prompt(system=_CHAMBER_SYSTEM, user="\n".join(user_lines))
    response = client.generate_json(
        prompt,
        schema=_CHAMBER_SCHEMA,
        max_tokens=400,
        temperature=0.7,
    )
    return str(response.parsed["narrative"])
