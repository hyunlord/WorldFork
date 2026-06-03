"""GM LLM 내러티브 — 누적 맥락으로 행동 결과를 진전시켜 묘사.

게임 진행 엔진 재설계 1단계 (★ 04 아키텍처 / 03 프롬프트 정합):
- Rule Engine(handler)은 하드 상태(수치) 변경, GM은 서술만 담당.
- 같은 행동도 누적 히스토리에 따라 다르게 전개 — intent template 반복 해소.

계약형 프롬프트 (Role/Canon/State/Output Contract)로 메타 발화·상태 임의
변경을 차단한다. 실패 시 빈 문자열 → 호출자가 handler template로 fallback.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import get_qwen36_27b_q3
from service.sim.types import PlayerActionType

# 서사형 action — GM이 narrative 주도. 수치/전투(ATTACK/EQUIP/SHOP/ABSORB 등)는
# 기존 handler narrative 유지(전투는 별도 compose_combat_narrative). 1단계는
# 같은 응답 반복이 두드러지던 탐색·대화·대기 계열부터 GM으로 전환.
GM_NARRATE_ACTIONS: frozenset[PlayerActionType] = frozenset(
    {
        PlayerActionType.EXPLORE,
        PlayerActionType.DIALOGUE,
        PlayerActionType.WAIT,
        PlayerActionType.REST,
        PlayerActionType.COMMUNICATE,
        PlayerActionType.MOVE,
        PlayerActionType.LIBRARY_SEARCH,
        PlayerActionType.WAIT_IN_VILLAGE,
        PlayerActionType.REST_AND_NIGHT_WATCH,
        # ★ 5단계 — 전투도 GM 주도. 수치(데미지/HP/치명타/약점)는 handle_attack이
        #   확정하고, GM이 그 결과를 누적 맥락으로 묘사(같은 공격도 다른 서사).
        PlayerActionType.ATTACK,
        PlayerActionType.FLEE,
        # ★ 서빙 2단계 — 던전 진입도 GM 주도. handle_enter_dungeon의 고정 한 줄
        #   ('자정이 지났다...')을 mechanical fact로 받아, GM이 입성 전환을 서술
        #   (포탈/통로/분위기). floor 수치 변경은 핸들러 — 마을/던전 단절 해소.
        PlayerActionType.ENTER_DUNGEON,
    }
)

_GM_SYSTEM = (
    "# Role Contract\n"
    "당신은 한국 web novel '게임 속 바바리안으로 살아남기' 세계의 게임 마스터(GM)다. "
    "플레이어의 행동을 받아 그 결과를 1인칭('나는')·문어체 한국어로 진전시켜 묘사한다. "
    "메타·시스템·규칙 설명, AI 자칭, 사과는 금지한다. "
    "같은 행동도 아래 '최근 흐름'의 맥락에 따라 다르게 전개하라 — 똑같은 문장 반복 금지.\n\n"
    "# Canon Contract\n"
    "아래 세계 정보만 근거로 삼는다. 근거 없는 새 고유명사·설정 확정은 금지.\n"
    "{canon}\n\n"
    "# State Contract\n"
    "하드 상태(HP·위치·소지품·시간)는 읽기 전용이다. 새 보상·수치 변화·아이템 획득을 "
    "선언하지 않는다. 아래 '확정 결과'만 자연스럽게 녹여 서술한다.\n\n"
    "# Output Contract\n"
    "2-4문장으로 상황을 진전시켜 묘사하고, 다음에 할 만한 행동의 여지를 남긴다."
)

_GM_USER = (
    "## 최근 흐름\n{history}\n\n"
    "## 현재\n단계: {phase}\n위치: {location}\n주변: {surroundings}\n\n"
    "## 확정 결과 (이미 적용됨 — 서술만)\n{fact}\n\n"
    "## 플레이어 행동\n{action}\n\n"
    "위 행동의 결과를 현재 단계와 누적 맥락에 맞게 진전시켜 묘사하라."
)

_GM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narrative": {"type": "string", "minLength": 20, "maxLength": 1200},
    },
    "required": ["narrative"],
}


def _build_gm_prompt(
    user_input: str,
    mechanical_fact: str,
    location: str,
    surroundings: str,
    recent_turns: list[tuple[str, str]],
    canon: str = "",
    story_phase: str = "",
) -> Prompt:
    """계약형 GM 프롬프트 구성 (compose/stream 공용 — 동일 맥락 보장)."""
    recent = recent_turns[-8:]
    history = (
        "\n".join(f"- 행동: {u}\n  결과: {n}" for u, n in recent)
        if recent
        else "(없음 — 첫 행동)"
    )
    system = _GM_SYSTEM.format(canon=canon or "(추가 세계 정보 없음)")
    user = _GM_USER.format(
        history=history,
        phase=story_phase or "(진행 중)",
        location=location or "알 수 없는 곳",
        surroundings=surroundings or "특이사항 없음",
        fact=mechanical_fact or "(특별한 변화 없음)",
        action=user_input,
    )
    return Prompt(system=system, user=user)


def compose_gm_narrative(
    user_input: str,
    mechanical_fact: str,
    location: str,
    surroundings: str,
    recent_turns: list[tuple[str, str]],
    canon: str = "",
    story_phase: str = "",
) -> str:
    """누적 맥락 GM narrative 생성 (sync). 실패 시 빈 문자열 반환.

    recent_turns — (user_input, narrative) 시간순. 최근 8턴만 사용.
    mechanical_fact — handler가 확정한 결과(수치/사실). GM은 이를 서술만 한다.
    story_phase — 현재 스토리 단계 라벨(읽기 전용 맥락, State Contract).
    """
    try:
        client = get_qwen36_27b_q3()
        prompt = _build_gm_prompt(
            user_input, mechanical_fact, location, surroundings,
            recent_turns, canon, story_phase,
        )
        response = client.generate_json(
            prompt,
            schema=_GM_SCHEMA,
            max_tokens=500,
            temperature=0.8,
        )
        result = str(response.parsed.get("narrative", ""))
        return result if len(result) >= 20 else ""
    except Exception:
        return ""


async def stream_gm_narrative(
    user_input: str,
    mechanical_fact: str,
    location: str,
    surroundings: str,
    recent_turns: list[tuple[str, str]],
    canon: str = "",
    story_phase: str = "",
) -> AsyncIterator[str]:
    """누적 맥락 GM narrative 토큰 스트리밍 (평문). 실패 시 무출력.

    compose_gm_narrative와 동일 프롬프트(동일 맥락)이되 평문으로 점진 생성한다.
    JSON 래핑을 빼 토큰을 즉시 노출 — 호출자가 누적해 최종 narrative로 쓴다.
    스트림 시작/도중 오류는 삼켜 무출력으로 끝낸다(호출자가 handler로 fallback).
    """
    try:
        client = get_qwen36_27b_q3()
        prompt = _build_gm_prompt(
            user_input, mechanical_fact, location, surroundings,
            recent_turns, canon, story_phase,
        )
        agen = client.astream(prompt, max_tokens=500, temperature=0.8)
    except Exception:
        return
    try:
        async for piece in agen:
            yield piece
    except Exception:
        return
