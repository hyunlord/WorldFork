"""Phase D — 27B free-form fallback handler + combat narrative.

Phase D step 5: entity context inject (canon_facts keyword match).
Phase D step 6b: compose_combat_narrative (sync, asyncio.to_thread 래핑 권장).
intent classifier confidence < threshold 시 호출.
async router에서 asyncio.to_thread로 wrap (sync).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import LocalLLMClient, get_qwen35_9b_q3, pivotal_gm_client
from service.api.schemas.freeform_action import ExtractedEntities, StateDelta
from service.canon.context import get_entity_index
from service.canon.entity_index import EntityRef
from service.sim.combat import CombatTurnLog


def _freeform_client(pivotal: bool) -> LocalLLMClient:
    """기동 모델 라우팅 — 단순(자유 입력)=9B 빠름 / pivotal(전투 통합)=측정 우위 pivotal.

    ★ pivotal은 공유 pivotal_gm_client(기본 27B Q2, PIVOTAL env로 가역). 자유 입력
      fallback은 속도 우선 9B. (종전 미기동 27B :8081 호출 버그는 이미 해소.)
    """
    if pivotal:
        return pivotal_gm_client()
    return get_qwen35_9b_q3()


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


_NARRATIVE_ONLY_SYSTEM = (
    "한국 web novel '게임 속 바바리안으로 살아남기' 본문 어조 narrative 생성. "
    "1인칭('나는'/'내가'), 문어체 어미(~다/~었다, ~니다 금지), 화자 prefix 금지. "
    "{canon_context}행동을 ★ 2-3 문장으로 간결히 in-world 서사로만 묘사 — 군더더기 없이 "
    "감각 디테일 1가지만 또렷이(분석·설명 금지)."
)


def freeform_action(
    user_input: str,
    rationale: str | None,
    extracted_entities: ExtractedEntities | None = None,
) -> tuple[str, StateDelta]:
    """기동 모델(9B 빠름) sync 호출. (narrative, state_delta) 반환.

    ★ 도그푸딩 속도+견고화: 종전 strict-JSON(narrative+state_delta) 문법 제약은 9B Q3
      에서 느리고(16s+) 간헐 HTTP 500/truncation. free-form은 '분류 안 된 flavor 행동'
      이라 mechanical delta가 거의 불필요(의미 있는 효과는 분류된 intent 핸들러가 처리).
      → 문법 제약 없는 자유 서사 1회(빠름 ~4-5s·견고) + 최소 delta(시간만 진행).
      모델 불응이어도 502 없이 안전 서사로 턴 진행.
    """
    client = _freeform_client(pivotal=False)

    refs = _collect_entity_refs(user_input, extracted_entities)
    canon_context = _build_canon_context(refs)
    system = _NARRATIVE_ONLY_SYSTEM.format(canon_context=canon_context)
    rationale_block = f"의도: {rationale}\n" if rationale else ""

    try:
        text_resp = client.generate(
            Prompt(
                system=system,
                user=f"{rationale_block}행동: {user_input}\n서사:",
            ),
            max_tokens=160,  # ★ 출력 단축(간결 프롬프트 ~60-80토큰, 캡 여유)
            temperature=0.7,
        )
        narrative = text_resp.text.strip()
        if len(narrative) >= 10:
            return (narrative, StateDelta(time_advance=1))
    except Exception:  # noqa: BLE001 — 모델 flake → 안전 서사(502 금지)
        pass

    return (
        f"나는 {user_input.strip()}. 그러나 뚜렷한 변화는 일어나지 않았다.",
        StateDelta(time_advance=1),
    )


async def stream_freeform_narrative(
    user_input: str,
    rationale: str | None,
    extracted_entities: ExtractedEntities | None = None,
) -> AsyncIterator[str]:
    """free-form narrative 토큰 스트리밍(평문). 실패 시 무출력(호출자 sync 폴백).

    ★ 도그푸딩 속도: 메인 분류 경로(stream_gm_narrative)와 동일하게 첫 토큰을 즉시
      노출해 체감 지연을 ~1s로. 호출자가 토큰을 누적해 최종 narrative로 쓴다.
    """
    try:
        client = _freeform_client(pivotal=False)
        refs = _collect_entity_refs(user_input, extracted_entities)
        canon_context = _build_canon_context(refs)
        system = _NARRATIVE_ONLY_SYSTEM.format(canon_context=canon_context)
        rationale_block = f"의도: {rationale}\n" if rationale else ""
        agen = client.astream(
            Prompt(system=system, user=f"{rationale_block}행동: {user_input}\n서사:"),
            max_tokens=160,  # ★ 출력 단축(간결 프롬프트 ~60-80토큰, 캡 여유)
            temperature=0.7,
        )
    except Exception:  # noqa: BLE001 — 시작 실패 → 무출력(호출자 폴백)
        return
    try:
        async for piece in agen:
            yield piece
    except Exception:  # noqa: BLE001 — 도중 오류 → 부분 출력으로 종료
        return


# ─── combat narrative ──────────────────────────────────────────────────────────

_COMBAT_NARRATIVE_SYSTEM = (
    "한국 web novel '게임 속 바바리안으로 살아남기' 본문 어조 narrative 통합. "
    "서사 규칙: 1인칭('나는'/'내가'), 문어체 어미(~다/~었다, ~니다 금지), "
    "시스템 메시지만 「...」 안에 합쇼체 허용. "
    "전투 turn flow를 자연스럽게 연결, 4-6 문장 분량."
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
    """기동 모델(12B pivotal) 전투 narrative 생성 (sync). 실패 시 빈 문자열 반환."""
    try:
        client = _freeform_client(pivotal=True)
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
            max_tokens=400,  # ★ 속도: 600→400 (4-6 문장 통합 충분)
            temperature=0.7,
        )
        result = str(response.parsed.get("narrative", ""))
        return result if len(result) >= 30 else ""
    except Exception:
        return ""
