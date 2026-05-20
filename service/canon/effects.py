"""Phase D step 6a — canon abilities text parse + skill 분류."""

from __future__ import annotations

import re

# ── stat keyword mapping ──────────────────────────────────────────────────────
# canon abilities text 키워드 → stat 이름
ABILITY_KEYWORD_TO_STAT: dict[str, str] = {
    "근력": "strength",
    "근력계":  "strength",
    "절삭력": "attack_bonus",
    "타격력": "attack_bonus",
    "공격력": "attack_bonus",
    "명중률": "attack_bonus",
    "방어력": "defense_bonus",
    "골밀도": "defense_bonus",
    "체력": "max_hp_bonus",
    "생명력": "max_hp_bonus",
    "지구력": "max_hp_bonus",
    "민첩성": "agility",
    "민첩": "agility",
    "유연성": "agility",
    "도약력": "agility",
    "각력": "agility",
    "감각": "perception",
    "지각": "perception",
    "후각": "perception",
    "시각": "perception",
    "인지력": "perception",
    "마력": "magic",
    "마법력": "magic",
    "정신력": "mental",
    "집중력": "mental",
    "내성": "resistance",
    "독 내성": "resistance",
    "물리 내성": "defense_bonus",
    "항마력": "resistance",
}

# 등급 → 수치 (abilities text의 (하)/(중)/(상)/(최상) 표기)
_GRADE_TO_DELTA: dict[str, int] = {
    "하": 1,
    "중": 2,
    "상": 3,
    "최상": 4,
}

# ── regex patterns ────────────────────────────────────────────────────────────
# "민첩성+15" / "유연성-7" 형태
_NUMERIC_PAT = re.compile(r"([가-힣\s]+?)([+-])(\d+)")
# "민첩성(중)" / "후각(하)" 형태
_GRADE_PAT = re.compile(r"([가-힣\s]+?)\((최상|하|중|상)\)")


def parse_ability_text(text: str) -> dict[str, int]:
    """canon abilities text → stat bonus dict.

    예:
      "절삭력+12, 민첩성+15, 유연성-7"
        → {'attack_bonus': 12, 'agility': 8}
      "민첩성(중), 후각(하)"
        → {'agility': 2, 'perception': 1}
    """
    if not text:
        return {}

    result: dict[str, int] = {}

    # 1) numeric pattern
    for m in _NUMERIC_PAT.finditer(text):
        keyword = m.group(1).strip()
        sign = m.group(2)
        num = int(m.group(3))
        delta = num if sign == "+" else -num
        stat = _keyword_to_stat(keyword)
        if stat:
            result[stat] = result.get(stat, 0) + delta

    # 2) grade pattern (numeric pattern이 덮지 못한 키워드)
    for m in _GRADE_PAT.finditer(text):
        keyword = m.group(1).strip()
        grade_str = m.group(2)
        delta = _GRADE_TO_DELTA.get(grade_str, 1)
        stat = _keyword_to_stat(keyword)
        if stat:
            result[stat] = result.get(stat, 0) + delta

    return result


def parse_essence_abilities(abilities: dict[str, object]) -> dict[str, int]:
    """Essence abilities dict → stat bonus dict.

    canon_facts.json의 abilities 형태:
      {} — empty
      {'text': '...'} — description text
    """
    text = str(abilities.get("text", ""))
    return parse_ability_text(text)


def classify_skill(skill_name: str) -> str:
    """skill name → 'active' | 'passive' | 'unknown'.

    canon_facts의 skills_granted 형태:
      '독화살 (P)' / '(P) 방부제: ...' — passive
      '도둑걸음 (A)' / '(A) 생기 흡수: ...' — active
    """
    upper = skill_name.upper()
    if "(A)" in upper or "(A " in upper:
        return "active"
    if "(P)" in upper or "(P " in upper:
        return "passive"
    return "unknown"


# ── internal ──────────────────────────────────────────────────────────────────


def _keyword_to_stat(keyword: str) -> str | None:
    """keyword substring 매칭 — 가장 긴 key 우선."""
    best: str | None = None
    best_len = 0
    kw_stripped = keyword.strip()
    for k, stat in ABILITY_KEYWORD_TO_STAT.items():
        if k in kw_stripped and len(k) > best_len:
            best = stat
            best_len = len(k)
    return best
