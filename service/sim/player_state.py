"""Phase D step 6d — EssenceSlot + stat accumulation (ep_0337/0556 정합).

정수 흡수 시 stat_bundle 전부 ADD, 제거 시 전부 SUBTRACT (SUM 누적).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class EssenceSlot:
    """흡수한 단일 정수 기록 (ep_0337/0556 정합)."""

    essence_name: str
    stat_bundle: dict[str, int] = field(default_factory=dict)
    skills: list[str] = field(default_factory=list)
    grade: int | None = None


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
    return EssenceSlot(
        essence_name=str(d.get("essence_name", "")),
        stat_bundle=stats,
        skills=skills,
        grade=grade,
    )


def compute_total_stats(slots: list[EssenceSlot]) -> dict[str, int]:
    """흡수 정수들의 stat_bundle 합산 (SUM — ep_0337 정합)."""
    total: dict[str, int] = {}
    for slot in slots:
        for stat, delta in slot.stat_bundle.items():
            total[stat] = total.get(stat, 0) + delta
    return total


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
