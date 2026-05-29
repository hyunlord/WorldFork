"""Phase D step 6a — Enemy dataclass + serialize."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EnemyType(StrEnum):
    """본문 정합 enemy type (★ wiki 009).

    PSIONIC  이능계  — 파괴적 액티브 스킬 보유
    SPIRIT   영체류  — 물리 피해 면역 (★ Fix 5)
    PHYSICAL 육체   — default, 육탄 능력 강
    UNDEAD   언데드  — 신성력 / 불 약점, 코어=실제 HP
    COLD_BEAST 냉기/짐승 — 전격 약점
    DARK     어둠   — 태양 / 빛 약점
    """

    PSIONIC = "psionic"
    SPIRIT = "spirit"
    PHYSICAL = "physical"
    UNDEAD = "undead"
    COLD_BEAST = "cold_beast"
    DARK = "dark"


# 이름 keyword → EnemyType (부분 매칭 — name에 keyword 포함 시)
NAME_KEYWORD_TO_TYPE: dict[str, EnemyType] = {
    # 영체류 — 물리 면역
    "유령": EnemyType.SPIRIT,
    "원혼": EnemyType.SPIRIT,
    "레이스": EnemyType.SPIRIT,
    "벤시": EnemyType.SPIRIT,
    "영혼": EnemyType.SPIRIT,
    # 언데드 — 신성력/불 약점
    "구울": EnemyType.UNDEAD,
    "스켈레톤": EnemyType.UNDEAD,
    "좀비": EnemyType.UNDEAD,
    "데드맨": EnemyType.UNDEAD,
    "시체골렘": EnemyType.UNDEAD,
    "데스나이트": EnemyType.UNDEAD,
    "뱀파이어": EnemyType.UNDEAD,
    "본 나이트": EnemyType.UNDEAD,
    "스컬": EnemyType.UNDEAD,
    "리치": EnemyType.UNDEAD,
    # 냉기/짐승 — 전격 약점
    "예티": EnemyType.COLD_BEAST,
    "서리": EnemyType.COLD_BEAST,
    "기가울프": EnemyType.COLD_BEAST,
    # 어둠 — 태양/빛 약점
    "그림자": EnemyType.DARK,
    # 이능계 — 파괴적 스킬
    "바포메트": EnemyType.PSIONIC,
    "도플갱어": EnemyType.PSIONIC,
}

# EnemyType → default weakness_types 목록 (★ wiki 009)
WEAKNESS_BY_TYPE: dict[EnemyType, list[str]] = {
    EnemyType.UNDEAD: ["신성력", "불"],
    EnemyType.COLD_BEAST: ["전격"],
    EnemyType.DARK: ["태양", "빛"],
    EnemyType.SPIRIT: [],
    EnemyType.PHYSICAL: [],
    EnemyType.PSIONIC: [],
}


def infer_enemy_type(
    race: str | None = None,
    name: str | None = None,
) -> EnemyType:
    """race 또는 name keyword로 EnemyType 추론.

    race 완전 매칭 우선, 이후 name keyword 부분 매칭.
    미매칭 시 default PHYSICAL.
    """
    if race and race in NAME_KEYWORD_TO_TYPE:
        return NAME_KEYWORD_TO_TYPE[race]
    if name:
        for keyword, etype in NAME_KEYWORD_TO_TYPE.items():
            if keyword in name:
                return etype
    return EnemyType.PHYSICAL


@dataclass
class Enemy:
    """단일 encounter enemy."""

    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    grade: int | None = None  # 1-9
    race: str | None = None
    abilities: list[str] = field(default_factory=list)  # canon skill names
    weakness_races: list[str] = field(default_factory=list)
    weakness_types: list[str] = field(default_factory=list)
    essence_drop: str | None = None
    is_hostile: bool = True
    enemy_type: EnemyType = EnemyType.PHYSICAL


def enemy_to_dict(e: Enemy) -> dict[str, object]:
    """Enemy → JSON-serializable dict (encounters list 호환)."""
    return {
        "name": e.name,
        "hp": e.hp,
        "max_hp": e.max_hp,
        "attack": e.attack,
        "defense": e.defense,
        "grade": e.grade,
        "race": e.race,
        "abilities": list(e.abilities),
        "weakness_races": list(e.weakness_races),
        "weakness_types": list(e.weakness_types),
        "essence_drop": e.essence_drop,
        # ★ get_first_enemy 호환: hostile 키 True 보장
        "hostile": e.is_hostile,
        "is_hostile": e.is_hostile,
        "enemy_type": e.enemy_type.value,
    }


def _to_int(val: object, default: int) -> int:
    if isinstance(val, int):
        return val
    if isinstance(val, (float, str)):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default
    return default


def _to_str_list(val: object) -> list[str]:
    if isinstance(val, list):
        return [str(item) for item in val]
    return []


def enemy_from_dict(d: dict[str, object]) -> Enemy:
    """dict → Enemy (encounters list 역직렬화)."""
    grade_raw = d.get("grade")
    grade = _to_int(grade_raw, 0) if grade_raw is not None else None

    race_raw = d.get("race")
    race = str(race_raw) if race_raw is not None else None

    essence_raw = d.get("essence_drop")
    essence_drop = str(essence_raw) if essence_raw is not None else None

    hostile_raw = d.get("is_hostile", d.get("hostile", True))
    is_hostile = bool(hostile_raw)

    raw_etype = d.get("enemy_type")
    try:
        enemy_type = EnemyType(str(raw_etype)) if raw_etype is not None else EnemyType.PHYSICAL
    except ValueError:
        enemy_type = EnemyType.PHYSICAL

    name_val = str(d.get("name", "이름 모를 적"))
    if enemy_type == EnemyType.PHYSICAL:
        enemy_type = infer_enemy_type(race, name_val)

    # ★ weakness_types 미지정 시 enemy_type 정합 default 유도 (wiki 009)
    # 언데드→신성력/불, 냉기짐승→전격, 어둠→태양/빛 약점이 combat 1.5x에 반영
    weakness_types = _to_str_list(d.get("weakness_types"))
    if not weakness_types:
        weakness_types = list(WEAKNESS_BY_TYPE.get(enemy_type, []))

    return Enemy(
        name=name_val,
        hp=_to_int(d.get("hp"), 30),
        max_hp=_to_int(d.get("max_hp"), 30),
        attack=_to_int(d.get("attack"), 8),
        defense=_to_int(d.get("defense"), 3),
        grade=grade,
        race=race,
        abilities=_to_str_list(d.get("abilities")),
        weakness_races=_to_str_list(d.get("weakness_races")),
        weakness_types=weakness_types,
        essence_drop=essence_drop,
        is_hostile=is_hostile,
        enemy_type=enemy_type,
    )
