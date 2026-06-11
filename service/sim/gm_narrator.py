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
    get_qwen35_9b_q3,
    pivotal_gm_client,
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


# pivotal GM 모델 — ★ 측정 정정(2026-06): 27B Q2는 6축 품질↑(4.93 vs 4.62)이나 decode
#   9.3 t/s로 Gemma 12B Q4(16.8)보다 1.8x 느림(앞선 '19' 오측 정정). 속도 우선 → 기본 Gemma.
#   PIVOTAL=27b_q2 로 품질 모드 선택(가역). 단순 경로는 9B.
_PIVOTAL_LABEL: dict[str, str] = {"gemma": "gemma", "27b_q3": "27b", "27b_q2": "27b-q2"}


def gm_model_label(pivotal: bool) -> str:
    """라우팅 관측 라벨 — 응답 gm_model 필드용."""
    if not pivotal:
        return "9b"
    return _PIVOTAL_LABEL.get(os.environ.get("PIVOTAL", "gemma"), "27b-q2")


def _gm_client(pivotal: bool) -> LocalLLMClient:
    """pivotal → Gemma 12B Q4(기본·속도 16.8 t/s, PIVOTAL=27b_q2로 품질 모드) / 단순 → 9B.
    ★ 27B Q2는 6축↑이나 1.8x 느려 기본 Gemma(속도 우선). 단순 tier는 검증된 원본 9B.
    모두 thinking off·스트리밍·schema."""
    if not pivotal:
        return get_qwen35_9b_q3()
    return pivotal_gm_client()


# GM 서사 temperature — Gemma 4는 공식 권장 1.0. 단순 tier(9B)는 0.9로 변주를 높여
#   같은 행동 반복(예: 부족장 대화 2회)에서 동일 narration을 줄인다(meaningful_progression
#   flaky 완화 — history 주입은 되나 9B 저변주가 우연히 유사 서사 산출). 품질 무손상 범위.
_GM_TEMPERATURE = 0.9
_GEMMA_GM_TEMPERATURE = 1.0


def _gm_temperature(pivotal: bool) -> float:
    # Gemma 명시 선택 시만 공식 권장 1.0. 기본 27B Q2·9B = 0.9(6축 eval 검증).
    if pivotal and os.environ.get("PIVOTAL", "gemma") == "gemma":
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
    "★ 2-3 문장으로 간결하게 진전시킨다 — 군더더기·중복 없이. 짧고 임팩트 있게.\n"
    "# Style Contract (★ 간결+구체)\n"
    "추상적 형용('기괴한', '거대한')에 머물지 말고 행동·타격·감각의 구체 디테일을 딱 한 가지만 "
    "골라 또렷이 넣는다 — 무엇이 어디를 어떻게(예: '도끼날이 늑대의 어깨뼈를 가르며 둔탁한 소리가 "
    "울렸다'). 확정 결과의 「」 판정·수치는 그대로 보존해 자연스럽게 녹인다."
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

# ★ 출력 길이 최적화: 측정상 2-3문장 간결 프롬프트 = 평균 60토큰(현행 103) + 6축↑
#   (4.33→5.00, 군더더기↓=임팩트↑) + 생성 1.7x 단축(6.2→3.6s). 캡도 128로(rambling 차단).
#   모든 경로(intent/예측/free-form) 동시 단축 — 예측 빨라져 경합↓·확대 가능(곱셈).
GM_MAX_TOKENS = 128
# ★ 장면별 적응 길이(외부 재평가 반영): 사교(대화/통신)는 색채·뉘앙스가 자산이라 여유를
#   준다. 액션·묘사(전투/탐험/이동)는 단축이 win-win(임팩트). 흥정은 handler 자체 서사라
#   이 경로와 무관(GM_MAX_TOKENS 영향 X). intent 기반으로 캡만 달리해 프롬프트는 공유.
_GM_MAX_TOKENS_SOCIAL = 192
_SOCIAL_GM_ACTIONS: frozenset[PlayerActionType] = frozenset(
    {PlayerActionType.DIALOGUE, PlayerActionType.COMMUNICATE}
)


def gm_max_tokens(action_type: PlayerActionType | None) -> int:
    """장면별 GM 서사 캡 — 사교(대화/통신)는 길게, 그 외는 단축."""
    if action_type in _SOCIAL_GM_ACTIONS:
        return _GM_MAX_TOKENS_SOCIAL
    return GM_MAX_TOKENS


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
    max_tokens: int = GM_MAX_TOKENS,
) -> AsyncIterator[str]:
    """누적 맥락 GM narrative 토큰 스트리밍 (평문). 실패 시 무출력.

    compose_gm_narrative와 동일 프롬프트(동일 맥락)이되 평문으로 점진 생성한다.
    JSON 래핑을 빼 토큰을 즉시 노출 — 호출자가 누적해 최종 narrative로 쓴다.
    스트림 시작/도중 오류는 삼켜 무출력으로 끝낸다(호출자가 handler로 fallback).
    pivotal — True면 27B(품질·기본값), False면 9B(단순·빠름). 라우팅 3단계.
    max_tokens — 장면별 적응 캡(gm_max_tokens). 사교는 길게, 액션은 단축.
    """
    try:
        client = _gm_client(pivotal)
        prompt = _build_gm_prompt(
            user_input, mechanical_fact, location, surroundings,
            recent_turns, canon, story_phase,
        )
        agen = client.astream(
            prompt, max_tokens=max_tokens, temperature=_gm_temperature(pivotal)
        )
    except Exception:
        return
    try:
        async for piece in agen:
            yield piece
    except Exception:
        return
