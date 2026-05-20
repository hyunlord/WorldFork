"""Phase D step 6a — Enemy dataclass + serialize."""

from __future__ import annotations

from dataclasses import dataclass, field


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

    return Enemy(
        name=str(d.get("name", "이름 모를 적")),
        hp=_to_int(d.get("hp"), 30),
        max_hp=_to_int(d.get("max_hp"), 30),
        attack=_to_int(d.get("attack"), 8),
        defense=_to_int(d.get("defense"), 3),
        grade=grade,
        race=race,
        abilities=_to_str_list(d.get("abilities")),
        weakness_races=_to_str_list(d.get("weakness_races")),
        weakness_types=_to_str_list(d.get("weakness_types")),
        essence_drop=essence_drop,
        is_hostile=is_hostile,
    )
