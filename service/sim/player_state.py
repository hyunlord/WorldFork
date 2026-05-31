"""Phase D step 6d — EssenceSlot + stat accumulation (ep_0337/0556 정합).

정수 흡수 시 stat_bundle 전부 ADD, 제거 시 전부 SUBTRACT (SUM 누적).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class EssenceSlot:
    """흡수한 단일 정수 기록 (ep_0337/0556 정합).

    ★ I-G1 — resistances: 저항 type별 누적 (★ ee5d7d7 parsed)
    ★ I-G1 — etc_abilities: 미분류 ability log (★ stat 영향 X)
    ★ attack_elements: source_monster 속성 공격 element (★ 불/냉기/전격 등)
    """

    essence_name: str
    stat_bundle: dict[str, int] = field(default_factory=dict)
    skills: list[str] = field(default_factory=list)
    grade: int | None = None
    resistances: dict[str, int] = field(default_factory=dict)
    etc_abilities: list[str] = field(default_factory=list)
    attack_elements: list[str] = field(default_factory=list)
    sensitivities: dict[str, int] = field(default_factory=dict)
    regen_per_turn: int = 0   # ★ 자연 재생력 tier → 매 턴 HP 재생 (passive)


def slot_to_dict(s: EssenceSlot) -> dict[str, object]:
    return asdict(s)


def slot_from_dict(d: dict[str, object]) -> EssenceSlot:
    stat_raw = d.get("stat_bundle", {})
    stats: dict[str, int] = {}
    if isinstance(stat_raw, dict):
        for k, v in stat_raw.items():
            if isinstance(k, str) and isinstance(v, int):
                stats[k] = v
    skills_raw = d.get("skills", [])
    skills = [str(s) for s in skills_raw] if isinstance(skills_raw, list) else []
    grade_raw = d.get("grade")
    grade = int(grade_raw) if isinstance(grade_raw, int) else None

    # ★ I-G1 — resistances 역직렬화 (기존 dict 미보유 시 빈 dict)
    res_raw = d.get("resistances", {})
    resistances: dict[str, int] = {}
    if isinstance(res_raw, dict):
        for k, v in res_raw.items():
            if isinstance(k, str) and isinstance(v, int):
                resistances[k] = v

    etc_raw = d.get("etc_abilities", [])
    etc_list = [str(s) for s in etc_raw] if isinstance(etc_raw, list) else []

    ae_raw = d.get("attack_elements", [])
    attack_elements = [str(s) for s in ae_raw] if isinstance(ae_raw, list) else []

    sens_raw = d.get("sensitivities", {})
    sensitivities: dict[str, int] = {}
    if isinstance(sens_raw, dict):
        for k, v in sens_raw.items():
            if isinstance(k, str) and isinstance(v, int):
                sensitivities[k] = v

    regen_raw = d.get("regen_per_turn", 0)
    regen_per_turn = int(regen_raw) if isinstance(regen_raw, (int, float)) else 0

    return EssenceSlot(
        essence_name=str(d.get("essence_name", "")),
        stat_bundle=stats,
        skills=skills,
        grade=grade,
        resistances=resistances,
        etc_abilities=etc_list,
        attack_elements=attack_elements,
        sensitivities=sensitivities,
        regen_per_turn=regen_per_turn,
    )


def compute_total_stats(slots: list[EssenceSlot]) -> dict[str, int]:
    """흡수 정수들의 stat_bundle 합산 (SUM — ep_0337 정합)."""
    total: dict[str, int] = {}
    for slot in slots:
        for stat, delta in slot.stat_bundle.items():
            total[stat] = total.get(stat, 0) + delta
    return total


def compute_total_resistances(slots: list[EssenceSlot]) -> dict[str, int]:
    """흡수 정수들의 resistances 합산 (★ I-G1)."""
    total: dict[str, int] = {}
    for slot in slots:
        for rtype, value in slot.resistances.items():
            total[rtype] = total.get(rtype, 0) + value
    return total


def compute_total_sensitivities(slots: list[EssenceSlot]) -> dict[str, int]:
    """흡수 정수들의 element 감응도 합산 (★ 공격 element 위력 보정)."""
    total: dict[str, int] = {}
    for slot in slots:
        for element, value in slot.sensitivities.items():
            total[element] = total.get(element, 0) + value
    return total


def compute_total_attack_elements(slots: list[EssenceSlot]) -> list[str]:
    """흡수 정수들의 attack_elements 합집합 (★ 순서 유지 dedup)."""
    elements: list[str] = []
    seen: set[str] = set()
    for slot in slots:
        for el in slot.attack_elements:
            if el not in seen:
                seen.add(el)
                elements.append(el)
    return elements


def compute_total_regen(slots: list[EssenceSlot]) -> int:
    """흡수 정수들의 passive HP 재생량 합산 (★ 매 턴 회복)."""
    return sum(slot.regen_per_turn for slot in slots)


def compute_total_skills(slots: list[EssenceSlot]) -> list[str]:
    """흡수 정수들의 skill 합집합."""
    skills: list[str] = []
    seen: set[str] = set()
    for slot in slots:
        for sk in slot.skills:
            if sk not in seen:
                seen.add(sk)
                skills.append(sk)
    return skills
