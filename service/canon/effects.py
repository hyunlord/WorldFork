"""Phase D step 6a/6d — canon abilities text parse + skill 분류 + EssenceSlot 변환.

★ I-G1 parsed ability 통합 (★ ee5d7d7 정합):
- parsed list 보유 시 classify_ability / apply_parsed_abilities 본 stat_bundle + resistances 적용
- parsed가 있으면 기존 text-based parse skip (★ double counting 방지)
"""

from __future__ import annotations

import re
from typing import Final

from service.sim.player_state import EssenceSlot

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

# ── I-G1 parsed ability classification ────────────────────────────────────────

TIER_VALUE: Final[dict[str, int]] = {
    "상": 3,
    "중": 2,
    "하": 1,
}

# 저항 keyword → resistance type — substring 매칭, 긴 keyword 우선
_RESISTANCE_KEYWORDS: Final[list[tuple[str, str]]] = [
    ("냉기 감응도", "냉기"),
    ("냉기응축", "냉기"),
    ("냉기 내성", "냉기"),
    ("독 내성", "독"),
    ("독내성", "독"),
    ("고통 내성", "고통"),
    ("고통내성", "고통"),
    ("정신 내성", "정신"),
    ("물리 내성", "물리"),
    ("화염 내성", "화염"),
    ("열 내성", "화염"),
    ("대지 저항", "대지"),
    ("산성 내성", "산성"),
    ("산성", "산성"),
    ("오한", "냉기"),
    ("화염", "화염"),
    ("독", "독"),
    ("내성", "기타"),
]

_ATTACK_KEYWORDS: Final[frozenset[str]] = frozenset([
    "근력", "완력", "절삭력", "골강도", "파괴력", "강타",
    "공격력", "타격", "위력", "각력",
])

_DEX_KEYWORDS: Final[frozenset[str]] = frozenset([
    "민첩", "직감", "기민", "반응", "유연성", "기동",
])


def classify_ability(name: str) -> tuple[str, str | None]:
    """ability name → (category, resistance_type).

    category: "attack" | "dex" | "resistance" | "etc"
    resistance_type: 저항 시 "독"/"냉기"/.., 그 외 None
    """
    s = name.strip()
    if not s:
        return ("etc", None)
    # 저항 우선 (가장 specific, 긴 keyword 먼저 — list 순서 정합)
    for kw, rtype in _RESISTANCE_KEYWORDS:
        if kw in s:
            return ("resistance", rtype)
    for kw in _ATTACK_KEYWORDS:
        if kw in s:
            return ("attack", None)
    for kw in _DEX_KEYWORDS:
        if kw in s:
            return ("dex", None)
    return ("etc", None)


# EnemyType(.value, lowercase) → player resistances dict key 정합 element
# resistances key: 독/냉기/화염/고통/정신/물리/대지/산성/기타
ENEMY_ELEMENT_MAP: Final[dict[str, str]] = {
    "psionic": "정신",     # 이능계 — 정신 공격
    "spirit": "정신",      # 영체류 — 정신 공격
    "physical": "물리",    # 육체 — 물리
    "undead": "물리",      # 언데드 — 물리 (어둠 resistance key 부재)
    "cold_beast": "냉기",  # 냉기/짐승
    "dark": "정신",        # 어둠 — 정신 (어둠 resistance key 부재)
}


def get_enemy_attack_element(enemy_type: str) -> str:
    """EnemyType(.value) → attack element (★ default 물리).

    resistances dict key 정합 element 반환.
    """
    return ENEMY_ELEMENT_MAP.get(enemy_type.strip().lower(), "물리")


def apply_resistance(
    damage: int,
    element: str,
    resistances: dict[str, int],
) -> tuple[int, int]:
    """player resistance 정합 damage flat 감산.

    공식: damage_taken = max(1, damage - resistance[element])
    최소 1 보장 (★ 완전 면역 방지).

    return: (damage_taken, reduced_amount)
    """
    if damage <= 0:
        return 0, 0
    resist_value = resistances.get(element, 0)
    if resist_value <= 0:
        return damage, 0
    damage_taken = max(1, damage - resist_value)
    reduced = damage - damage_taken
    return damage_taken, reduced


def apply_parsed_abilities(
    parsed: list[dict[str, object]],
) -> tuple[dict[str, int], dict[str, int], list[str]]:
    """parsed list → (stat_bundle, resistances, etc_logs).

    - attack → stat_bundle["attack_bonus"] += tier
    - dex → stat_bundle["agility"] += tier
    - resistance → resistances[type] += tier
    - etc → log list 누적
    """
    stat_bundle: dict[str, int] = {}
    resistances: dict[str, int] = {}
    etc_logs: list[str] = []

    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        name_raw = entry.get("name")
        tier_raw = entry.get("tier")
        name = str(name_raw).strip() if isinstance(name_raw, str) else ""
        tier = str(tier_raw) if isinstance(tier_raw, str) else "중"
        value = TIER_VALUE.get(tier, 2)
        if not name:
            continue

        category, rtype = classify_ability(name)

        if category == "attack":
            stat_bundle["attack_bonus"] = stat_bundle.get("attack_bonus", 0) + value
        elif category == "dex":
            stat_bundle["agility"] = stat_bundle.get("agility", 0) + value
        elif category == "resistance" and rtype:
            resistances[rtype] = resistances.get(rtype, 0) + value
        else:
            etc_logs.append(f"{name}({tier})")

    return stat_bundle, resistances, etc_logs


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


def essence_to_slot(essence_data: dict[str, object]) -> EssenceSlot:
    """canon essence dict → EssenceSlot (ep_0337/0556 정합).

    abilities text → stat bonus (positive).
    abilities parsed → stat_bundle + resistances + etc_abilities (★ I-G1).
    side_effects text → stat delta (may be negative).
    skills_granted → skills list.
    """
    abilities_raw = essence_data.get("abilities", {})
    stat_bundle: dict[str, int] = {}
    resistances: dict[str, int] = {}
    etc_abilities: list[str] = []

    if isinstance(abilities_raw, dict):
        # ★ parsed 우선 — double counting 방지 정합
        parsed = abilities_raw.get("parsed")
        if isinstance(parsed, list) and parsed:
            p_stats, p_res, p_etc = apply_parsed_abilities(parsed)
            for k, v in p_stats.items():
                stat_bundle[k] = stat_bundle.get(k, 0) + v
            for k, v in p_res.items():
                resistances[k] = resistances.get(k, 0) + v
            etc_abilities.extend(p_etc)
        else:
            # fallback — 기존 text-based parse
            stat_bundle = parse_essence_abilities(abilities_raw)
    elif isinstance(abilities_raw, str):
        stat_bundle = parse_ability_text(abilities_raw)

    side_effects_raw = essence_data.get("side_effects")
    if isinstance(side_effects_raw, list):
        for entry in side_effects_raw:
            if not isinstance(entry, str):
                continue
            side_stats = parse_ability_text(entry)
            for stat, delta in side_stats.items():
                stat_bundle[stat] = stat_bundle.get(stat, 0) + delta

    skills_raw = essence_data.get("skills_granted")
    skills: list[str] = []
    if isinstance(skills_raw, list):
        skills = [str(s) for s in skills_raw if isinstance(s, str)]

    grade_raw = essence_data.get("grade")
    slot_grade = int(grade_raw) if isinstance(grade_raw, int) else None

    name_raw = essence_data.get("name", "")
    return EssenceSlot(
        essence_name=str(name_raw),
        stat_bundle=stat_bundle,
        skills=skills,
        grade=slot_grade,
        resistances=resistances,
        etc_abilities=etc_abilities,
    )


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
