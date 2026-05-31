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


# 감응도 element keyword → element (★ canon: "속성 위력 보정" 공격 계수 — 저항 X)
_SENSITIVITY_ELEMENT: Final[list[tuple[str, str]]] = [
    ("화염", "불"), ("불", "불"),
    ("냉기", "냉기"), ("서리", "냉기"), ("빙", "냉기"),
    ("전격", "전격"), ("번개", "전격"),
    ("신성", "신성력"),
    ("빛", "빛"), ("태양", "빛"),
    ("독", "독"),
]


def classify_ability(name: str) -> tuple[str, str | None]:
    """ability name → (category, type).

    category: "attack" | "dex" | "resistance" | "sensitivity" | "etc"
    type: resistance/sensitivity 시 element ("독"/"냉기"/..), 그 외 None

    ★ 감응도(canon "속성 위력 보정" 공격 계수)는 resistance보다 우선 —
      "냉기 감응도"가 resistance(냉기)로 오분류되지 않도록.
    """
    s = name.strip()
    if not s:
        return ("etc", None)
    # 감응도 우선 (★ 공격 element 계수 — 저항과 구분)
    if "감응" in s:
        for kw, element in _SENSITIVITY_ELEMENT:
            if kw in s:
                return ("sensitivity", element)
        return ("sensitivity", "")  # element 미상 (예: 모든 속성)
    # 저항 (가장 specific, 긴 keyword 먼저 — list 순서 정합)
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


# source_monster 이름 keyword → 공격 element (★ weakness vocabulary 정합).
# 정밀 keyword — 오탐 회피: '불행'→불 / '고뇌'→뇌 / '광대'→광 차단.
# 13deef0 weakness(신성력/불/전격/빛) + 냉기/독 정합.
_SOURCE_ELEMENT_KEYWORDS: Final[list[tuple[tuple[str, ...], str]]] = [
    (("화염", "불꽃", "용암", "마그마", "작열", "화룡", "염화"), "불"),
    (("서리", "얼음", "빙결", "냉기", "한기", "설원", "동결"), "냉기"),
    (("전격", "번개", "낙뢰", "뇌전", "감전", "벼락"), "전격"),
    (("신성", "성스러", "성광", "성수", "성기사"), "신성력"),
    (("빛", "광휘", "태양", "여명"), "빛"),
    (("맹독", "독액", "독성", "산성", "마비독", "맹독성"), "독"),
]


def get_essence_attack_element(source_monster: str | None) -> str | None:
    """정수 source_monster(★ bbad9ab) 이름 → 공격 element.

    흡수 시 monster의 속성을 공격 element로 획득 (★ 불 정수 → 불 공격 → undead 약점).
    매칭 X 시 None (물리 기본은 무기 element가 담당).
    """
    if not source_monster or not source_monster.strip():
        return None
    name = source_monster.strip()
    for keywords, element in _SOURCE_ELEMENT_KEYWORDS:
        if any(kw in name for kw in keywords):
            return element
    return None


# rule bullet element 단어 → 표준 element (★ 13deef0 vocabulary 정합).
_RULE_ELEMENT_NORM: Final[dict[str, str]] = {
    "화염": "불", "불꽃": "불", "불": "불", "용암": "불", "작열": "불",
    "냉기": "냉기", "서리": "냉기", "얼음": "냉기", "빙결": "냉기", "한기": "냉기",
    "전격": "전격", "번개": "전격", "뇌전": "전격", "감전": "전격",
    "신성력": "신성력", "신성": "신성력", "성스러운": "신성력",
    "빛": "빛", "광휘": "빛", "태양": "빛", "여명": "빛",
    "맹독": "독", "독성": "독", "독": "독",
}
# "속성" 문맥 없이 단독 매칭 허용 — 다의어('빛'/'불'/'독') 제외로 오탐 차단.
_ELEMENT_STANDALONE: Final[tuple[str, ...]] = (
    "화염", "냉기", "전격", "신성력", "맹독", "독성", "빙결", "용암",
)
_RULE_ELEMENT_RE: Final[re.Pattern[str]] = re.compile(r"([가-힣]+)\s*속성")


def get_mechanism_element(mechanism: dict[str, object]) -> str:
    """mechanism rules의 element bullet → 공격 element (★ 22de63d rules game 연결).

    1순위 "X 속성" 명시 bullet, 2순위 명백한 element 명사 단독.
    일반 문장('빛을 꺼트림')·미지원 element('땅/혼돈/수')는 빈 문자열 — 오탐 차단.
    """
    rules = mechanism.get("rules")
    if not isinstance(rules, list):
        return ""
    for rule in rules:
        if not isinstance(rule, str):
            continue
        match = _RULE_ELEMENT_RE.search(rule)
        if match:
            word = match.group(1)
            for key in sorted(_RULE_ELEMENT_NORM, key=len, reverse=True):
                if key in word:
                    return _RULE_ELEMENT_NORM[key]
        for key in _ELEMENT_STANDALONE:
            if key in rule:
                return _RULE_ELEMENT_NORM[key]
    return ""


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
        elif category == "sensitivity":
            continue  # ★ 감응도는 parse_sensitivities에서 별도 처리 (중복 방지)
        else:
            etc_logs.append(f"{name}({tier})")

    return stat_bundle, resistances, etc_logs


def parse_sensitivities(parsed: list[dict[str, object]]) -> dict[str, int]:
    """parsed list → element 감응도 dict (★ 공격 element 위력 보정).

    canon: "감응도 스탯 — 속성 위력 보정" / "냉기 피해 계수인 냉기 감응도".
    element 미상(모든 속성)은 제외 — combat은 특정 element 매칭 필요.
    """
    sensitivities: dict[str, int] = {}
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        name_raw = entry.get("name")
        tier_raw = entry.get("tier")
        if not isinstance(name_raw, str) or not name_raw.strip():
            continue
        tier = str(tier_raw) if isinstance(tier_raw, str) else "중"
        category, element = classify_ability(name_raw)
        if category == "sensitivity" and element:
            sensitivities[element] = sensitivities.get(element, 0) + TIER_VALUE.get(tier, 2)
    return sensitivities


_REGEN_TIER: Final[dict[str, int]] = {"최상": 4, "상": 3, "중": 2, "하": 1}


def extract_regen_per_turn(parsed: list[dict[str, object]]) -> int:
    """parsed abilities → passive HP 재생량 (★ '자연 재생력' tier 최대값).

    매 턴 회복 HP — 최상4/상3/중2/하1. tier 미상 시 1. '재생' 미포함 ability 무시.
    중복 재생 능력은 최댓값 (합산 아님 — 과회복 방지).
    """
    best = 0
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        if "재생" not in str(entry.get("name", "")):
            continue
        tier = str(entry.get("tier", ""))
        best = max(best, _REGEN_TIER.get(tier, 1))
    return best


_REFLECT_TIER: Final[dict[str, float]] = {
    "최상": 0.25, "상": 0.20, "중": 0.15, "하": 0.10,
}


def extract_reflect_ratio(parsed: list[dict[str, object]]) -> float:
    """parsed abilities → 피해 반사율 (★ '확률적 보복'/'반사' tier 최댓값).

    enemy 공격 시 받은 피해의 일부를 반사 — 최상0.25/상0.20/중0.15/하0.10.
    tier 미상 0.10. '반사'/'보복' 미포함 ability 무시. 중복은 최댓값.
    """
    best = 0.0
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", ""))
        if "반사" not in name and "보복" not in name:
            continue
        tier = str(entry.get("tier", ""))
        best = max(best, _REFLECT_TIER.get(tier, 0.10))
    return best


def extract_conditional_heal(mechanism: dict[str, object]) -> float:
    """회복 mechanism rules → max_hp 대비 회복 비율 (★ enemy 조건부 회복 강도).

    enemy_ai HP<30% 회복 우선(select_ability) 시 combat 회복량 정밀화에 사용.
    완전 회복 1.0 / 최상급·대폭·빠르게 0.5 / 중 0.3 / 기본 0.2 / 회복 무관 0.0.
    """
    rules = mechanism.get("rules")
    name = str(mechanism.get("name", ""))
    parts = rules if isinstance(rules, list) else []
    text = " ".join(str(r) for r in parts) + " " + name
    if not any(k in text for k in ("회복", "재생", "복원")):
        return 0.0
    if "완전" in text:
        return 1.0
    if "최상" in text or "대폭" in text or "빠르게" in text:
        return 0.5
    if "(중)" in text or "중간" in text:
        return 0.3
    return 0.2


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


def essence_to_slot(
    essence_data: dict[str, object],
    extra_attack_elements: list[str] | None = None,
) -> EssenceSlot:
    """canon essence dict → EssenceSlot (ep_0337/0556 정합).

    abilities text → stat bonus (positive).
    abilities parsed → stat_bundle + resistances + etc_abilities (★ I-G1).
    side_effects text → stat delta (may be negative).
    skills_granted → skills list.
    extra_attack_elements → source_monster 매칭 외 보강 element (★ mechanism rules).
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

    # ★ 정수 공격 element — source_monster 속성 (불/냉기/전격/신성력/빛/독)
    source_raw = essence_data.get("source_monster")
    attack_elements: list[str] = []
    if isinstance(source_raw, str):
        element = get_essence_attack_element(source_raw)
        if element:
            attack_elements.append(element)
    # ★ mechanism element rules 보강 — 이름 keyword가 놓친 element (22de63d 연결)
    if extra_attack_elements:
        for el in extra_attack_elements:
            if el and el not in attack_elements:
                attack_elements.append(el)

    # ★ 감응도 — element 위력 보정 (parsed "X 감응도")
    sensitivities: dict[str, int] = {}
    regen_per_turn = 0
    reflect_ratio = 0.0
    if isinstance(abilities_raw, dict):
        parsed_s = abilities_raw.get("parsed")
        if isinstance(parsed_s, list) and parsed_s:
            sensitivities = parse_sensitivities(parsed_s)
            regen_per_turn = extract_regen_per_turn(parsed_s)  # ★ passive HP 재생
            reflect_ratio = extract_reflect_ratio(parsed_s)  # ★ 피해 반사

    name_raw = essence_data.get("name", "")
    return EssenceSlot(
        essence_name=str(name_raw),
        stat_bundle=stat_bundle,
        skills=skills,
        grade=slot_grade,
        resistances=resistances,
        etc_abilities=etc_abilities,
        attack_elements=attack_elements,
        sensitivities=sensitivities,
        regen_per_turn=regen_per_turn,
        reflect_ratio=reflect_ratio,
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
