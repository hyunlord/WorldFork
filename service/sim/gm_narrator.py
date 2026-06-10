"""GM LLM 내러티브 — 누적 맥락으로 행동 결과를 진전시켜 묘사.

게임 진행 엔진 재설계 1단계 (★ 04 아키텍처 / 03 프롬프트 정합):
- Rule Engine(handler)은 하드 상태(수치) 변경, GM은 서술만 담당.
- 같은 행동도 누적 히스토리에 따라 다르게 전개 — intent template 반복 해소.

계약형 프롬프트 (Role/Canon/State/Output Contract)로 메타 발화·상태 임의
변경을 차단한다. 실패 시 빈 문자열 → 호출자가 handler template로 fallback.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from core.llm.client import Prompt
from core.llm.local_client import (
    LocalLLMClient,
    get_gemma4_12b,
    get_qwen35_4b_gm,
    get_qwen36_27b_q3,
)
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

# ─── 서빙 3단계 — 하이브리드 9B/27B 라우팅 ───
#   단순 서사(탐색/이동/저강도)는 9B(~18 t/s, 4초)로 실 단축, pivotal(성년식
#   단계·전투·적대 조우)은 27B로 품질 보장. '애매하면 27B' 안전 기본값 —
#   라우팅 오분류로 중대 순간이 9B로 새지 않게(품질 우선).

# pivotal 스토리 단계 — 성년식 첫인상(선언/무기 선택)은 27B 품질.
PIVOTAL_PHASES: frozenset[str] = frozenset({"declaration", "weapon_choice"})

# pivotal action — 전투는 27B 품질(중대 순간).
PIVOTAL_ACTIONS: frozenset[PlayerActionType] = frozenset(
    {PlayerActionType.ATTACK, PlayerActionType.FLEE}
)


def is_pivotal_gm(
    action_type: PlayerActionType,
    story_phase: str,
    has_hostile: bool,
) -> bool:
    """27B(품질)로 보낼 pivotal 순간인지 — 아니면 9B(단순·빠름).

    ★ '애매하면 27B' — 성년식 단계 / 전투 action / 적대 조우 중이면 27B.
      순수 비전투 단순 행동(탐색·이동·대화·휴식)만 9B로 라우팅.
    """
    if story_phase in PIVOTAL_PHASES:
        return True
    if action_type in PIVOTAL_ACTIONS:
        return True
    if has_hostile:
        return True
    return False


# pivotal GM 모델 — Gemma 4 12B(기본, ~15 t/s·서사 우위) ↔ 27B(폴백).
#   GEMMA_GM=0 으로 즉시 27B 되돌림(서빙 문제 시 안전). 단순 경로는 9B 유지.
def _use_gemma_pivotal() -> bool:
    return os.environ.get("GEMMA_GM", "1") != "0"


def gm_model_label(pivotal: bool) -> str:
    """라우팅 관측 라벨 — 응답 gm_model 필드용."""
    if not pivotal:
        return "4b"
    return "gemma" if _use_gemma_pivotal() else "27b"


def _gm_client(pivotal: bool) -> LocalLLMClient:
    """pivotal → Gemma 4 12B(기본·품질·~15 t/s) 또는 27B(GEMMA_GM=0 폴백) /
    단순 → Qwen3.5-4B Q8 GM-LoRA(빠른 tier·~28 t/s·고증 유지). 파인튜닝 best 배선
    (a6e6650): GM 문체 학습본이 raw 9B보다 단순 서사 적합. 모두 thinking off·스트리밍·schema."""
    if not pivotal:
        return get_qwen35_4b_gm()
    return get_gemma4_12b() if _use_gemma_pivotal() else get_qwen36_27b_q3()


# GM 서사 temperature — 27B/9B는 0.8. Gemma 4는 공식 권장 1.0으로 변주를 높여
#   짧은 constrained 프롬프트(예: 부족장 대화)에서 반복 narration을 줄인다
#   (산문 품질 무손상 — 디코딩 eval 확인). 게임 서사 다양성에도 기여.
_GM_TEMPERATURE = 0.8
_GEMMA_GM_TEMPERATURE = 1.0


def _gm_temperature(pivotal: bool) -> float:
    if pivotal and _use_gemma_pivotal():
        return _GEMMA_GM_TEMPERATURE
    return _GM_TEMPERATURE


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

# ★ 서빙 4단계 — GM 길이 튜닝: 3-4문장 서사는 80-160토큰이면 충분. 상한을 500에서
#   160으로 낮춰 출력 길이 비례 벽시계를 단축(9B/27B 공통). 보스/챔버는 별도(유지).
GM_MAX_TOKENS = 160


# 비요른 persona 앵커 — canon_facts는 원작 주인공(한스 계열)이라 게임 플레이어
# 비요른(흑곰족)을 직접 담지 않는다. 무기/persona 일관을 위해 고정 앵커를 canon
# Contract 앞에 둔다. 무기는 호출자가 현재 장비를 넘기면 함께 고정.
_PERSONA_ANCHOR = (
    "주인공 비요른은 흑곰족 출신의 거구 바바리안 전사이며, "
    "현대인 '이한수'의 영혼이 깃들어 있다. 성년식에서 고른 무기를 일관되게 쓴다."
)

# 키워드 정합으로 주입할 canon 타입 — 세계 사물만. character/skill/facility/mechanism은
# 부분일치 노이즈(원작 주인공 '한수', '궁수' skill, '방' 시설 등)라 배제.
_WORLD_FACT_TYPES: frozenset[str] = frozenset({"essence", "race", "location"})


def build_gm_canon(
    user_input: str,
    location: str,
    surroundings: str,
    hostiles: list[str] | None = None,
    weapon: str = "",
    *,
    max_facts: int = 5,
) -> str:
    """현재 턴 맥락에 정합한 canon 고증 + persona/무기 앵커를 Canon Contract 문자열로.

    전역 EntityIndex(canon_facts)에서 위치·적·입력 키워드에 걸리는 fact만 압축 주입해
    환각(근거 없는 고유명사/설정)을 차단한다. 전체 canon 주입(토큰 낭비)은 피한다.
    인덱스 미적재 시 persona 앵커만 반환(고증 없이도 무기/persona 일관은 보강).
    """
    from service.canon.context import get_entity_index

    persona = _PERSONA_ANCHOR
    if weapon:
        persona += f" 현재 무기: {weapon}."

    idx = get_entity_index()
    if idx is None:
        return persona

    lines: list[str] = []
    seen: set[str] = set()

    def _add(name: str, summary: str) -> None:
        if name in seen or not summary.strip():
            return
        seen.add(name)
        lines.append(f"- {name}: {summary.strip()[:140]}")

    # 위치 고증 (현재 location)
    if location:
        raw = idx.get_raw_location(location)
        if raw is not None:
            _add(location, str(raw.get("description") or ""))
        else:
            ref = idx.fuzzy_lookup(location)
            if ref is not None and ref.entity_type == "location":
                _add(ref.name, ref.summary)

    # 적 고증 (등급/출몰/정수 — 현재 적대 대상)
    for name in (hostiles or [])[:3]:
        ref = idx.lookup_by_name(name) or idx.fuzzy_lookup(name)
        if ref is not None:
            _add(ref.name, ref.summary)

    # 입력/주변 키워드 정합 (그 외 등장 엔티티) — 세계 사물만(_WORLD_FACT_TYPES).
    #   이미 담은 name의 부분문자열도 제외(중복/노이즈 회피).
    for ref in idx.keyword_match(f"{user_input} {surroundings}", limit=max_facts * 2):
        if ref.entity_type not in _WORLD_FACT_TYPES:
            continue
        # 1글자 name('방'⊂'방향' 등)은 부분일치 노이즈라 제외.
        if len(ref.name) < 2:
            continue
        if any(ref.name in kept for kept in seen):
            continue
        _add(ref.name, ref.summary)
        if len(lines) >= max_facts:
            break

    if not lines:
        return persona
    return persona + "\n" + "\n".join(lines[:max_facts])


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
    pivotal: bool = True,
) -> str:
    """누적 맥락 GM narrative 생성 (sync). 실패 시 빈 문자열 반환.

    recent_turns — (user_input, narrative) 시간순. 최근 8턴만 사용.
    mechanical_fact — handler가 확정한 결과(수치/사실). GM은 이를 서술만 한다.
    story_phase — 현재 스토리 단계 라벨(읽기 전용 맥락, State Contract).
    pivotal — True면 27B(품질·기본값), False면 9B(단순·빠름). 라우팅 3단계.
    """
    try:
        client = _gm_client(pivotal)
        prompt = _build_gm_prompt(
            user_input, mechanical_fact, location, surroundings,
            recent_turns, canon, story_phase,
        )
        response = client.generate_json(
            prompt,
            schema=_GM_SCHEMA,
            max_tokens=GM_MAX_TOKENS,
            temperature=_gm_temperature(pivotal),
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
    pivotal: bool = True,
) -> AsyncIterator[str]:
    """누적 맥락 GM narrative 토큰 스트리밍 (평문). 실패 시 무출력.

    compose_gm_narrative와 동일 프롬프트(동일 맥락)이되 평문으로 점진 생성한다.
    JSON 래핑을 빼 토큰을 즉시 노출 — 호출자가 누적해 최종 narrative로 쓴다.
    스트림 시작/도중 오류는 삼켜 무출력으로 끝낸다(호출자가 handler로 fallback).
    pivotal — True면 27B(품질·기본값), False면 9B(단순·빠름). 라우팅 3단계.
    """
    try:
        client = _gm_client(pivotal)
        prompt = _build_gm_prompt(
            user_input, mechanical_fact, location, surroundings,
            recent_turns, canon, story_phase,
        )
        agen = client.astream(
            prompt, max_tokens=GM_MAX_TOKENS, temperature=_gm_temperature(pivotal)
        )
    except Exception:
        return
    try:
        async for piece in agen:
            yield piece
    except Exception:
        return
