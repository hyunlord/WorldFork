"""한국어 조사(particle) 헬퍼 — 받침 여부로 을/를, 이/가, 은/는 결정."""

from __future__ import annotations

_HANGUL_BASE = 0xAC00
_HANGUL_END = 0xD7A3
_JONGSEONG_COUNT = 28  # 종성 자리 수 (0 = 종성 없음)


def has_final_consonant(name: str) -> bool:
    """마지막 글자에 받침이 있으면 True."""
    if not name:
        return False
    ch = name.rstrip('"\'').rstrip()[-1]
    code = ord(ch)
    if _HANGUL_BASE <= code <= _HANGUL_END:
        return (code - _HANGUL_BASE) % _JONGSEONG_COUNT != 0
    return False


def eul_reul(name: str) -> str:
    """을/를 — 받침 있으면 '을', 없으면 '를'."""
    return "을" if has_final_consonant(name) else "를"


def i_ga(name: str) -> str:
    """이/가 — 받침 있으면 '이', 없으면 '가'."""
    return "이" if has_final_consonant(name) else "가"


def eun_neun(name: str) -> str:
    """은/는 — 받침 있으면 '은', 없으면 '는'."""
    return "은" if has_final_consonant(name) else "는"


def eu_reul(name: str) -> str:
    """으로/로 — 받침 있으면 '으로', 없으면 '로' (받침 ㄹ 포함 '로')."""
    if not name:
        return "으로"
    ch = name.rstrip('"\'').rstrip()[-1]
    code = ord(ch)
    if _HANGUL_BASE <= code <= _HANGUL_END:
        jongseong = (code - _HANGUL_BASE) % _JONGSEONG_COUNT
        if jongseong == 0:
            return "로"
        if jongseong == 8:  # ㄹ 종성
            return "로"
        return "으로"
    return "으로"
