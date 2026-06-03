"""일반 적 조우 등장 라인 (★ 서빙 2단계 — 던전 GM 사각지대 해소).

진단 A: 보스만 27B 연출(boss_narrative_gm), 일반 적은 _post_apply_spawn이
encounters를 채우기만 해 '조용한 출현' — "적을 마주했다" 부재.

이 모듈은 0-토큰 mechanical 라인으로 등장 서사를 즉시 제공한다(CLAUDE.md 원칙 5
'Mechanical 우선'). 매 스폰마다 27B를 다시 부르면 서빙 트랙이 줄이려던 지연이
배가되므로, 일반 조우는 타입별 분위기 라인으로 변주하고(같은 적도 다른 문장),
풍부한 27B 서사는 보스에 한정한다. 하이브리드 9B(3단계)에서 더 다듬을 여지.
"""

from __future__ import annotations

from typing import Any

# enemy_type(value) → 등장 분위기 opener 변주 ('{name}' 치환).
#   타입 약점/성격 정합 어조 — UNDEAD 음산, SPIRIT 서늘, COLD_BEAST 냉기 등.
_TYPE_OPENERS: dict[str, tuple[str, ...]] = {
    "undead": (
        "어둠 속에서 {name}{josa} 모습을 드러낸다",
        "썩은 흙냄새와 함께 {name}{josa} 천천히 일어선다",
    ),
    "spirit": (
        "서늘한 공기를 가르며 {name}{josa} 스며 나온다",
        "허공이 일그러지더니 {name}{josa} 형체를 갖춘다",
    ),
    "cold_beast": (
        "냉기를 흩뿌리며 {name}{josa} 거리를 좁혀 온다",
        "하얀 입김 너머로 {name}{josa} 송곳니를 드러낸다",
    ),
    "dark": (
        "그림자가 일렁이더니 {name}{josa} 솟아난다",
        "빛이 닿지 않는 구석에서 {name}{josa} 미끄러져 나온다",
    ),
    "psionic": (
        "기이한 압박감과 함께 {name}{josa} 나타난다",
        "공기가 무겁게 가라앉으며 {name}{josa} 시선을 고정한다",
    ),
    "physical": (
        "{name}{josa} 앞을 가로막는다",
        "거친 숨소리와 함께 {name}{josa} 달려든다",
    ),
}

# opener 뒤 호흡 — 전투 직전 긴장. 변주로 같은 적도 다른 마무리.
_TAILS: tuple[str, ...] = (
    "나는 자세를 낮추고 무기를 고쳐 쥔다.",
    "적의를 숨기지 않은 채, 한 발 더 다가온다.",
    "한 호흡 — 싸움을 피할 길은 보이지 않는다.",
)


def _i_ga(word: str) -> str:
    """주격 조사 — 받침 有 '이', 無 '가'. 빈 문자열은 '가'."""
    if not word:
        return "가"
    last = word[-1]
    if not ("가" <= last <= "힣"):
        return "가"
    return "이" if (ord(last) - 0xAC00) % 28 != 0 else "가"


def compose_encounter_line(enemy: dict[str, Any], turn_count: int) -> str:
    """일반 적 조우 등장 라인 (0-토큰, 타입별 변주).

    turn_count로 opener/tail을 회전 — 같은 적이 또 나와도 다른 문장(결정적이라
    테스트 가능). 보스(별도 27B 연출)와 비적대 NPC는 호출자가 제외한다.
    """
    name = str(enemy.get("name") or "적")
    etype = str(enemy.get("enemy_type") or "physical")
    openers = _TYPE_OPENERS.get(etype, _TYPE_OPENERS["physical"])
    opener = openers[turn_count % len(openers)]
    tail = _TAILS[turn_count % len(_TAILS)]
    josa = _i_ga(name)
    return f"{opener.format(name=name, josa=josa)}. {tail}"
