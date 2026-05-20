"""Phase D step 6a — canon location → enemy spawn table."""

from __future__ import annotations

from collections import defaultdict

from service.canon.schema import CanonFacts
from service.sim.enemy import Enemy

# ── hostile role keywords ─────────────────────────────────────────────────────
_HOSTILE_ROLE_KEYWORDS: tuple[str, ...] = (
    "적",
    "몬스터",
    "괴물",
    "마물",
    "도적",
    "악역",
    "보스",
    "변이종",
    "약탈자",
    "적대",
)

# grade infer from name patterns (canon 본 grade=None 보완)
_GRADE_NAME_HINTS: tuple[tuple[str, int], ...] = (
    ("9등급", 9), ("8등급", 8), ("7등급", 7), ("6등급", 6),
    ("5등급", 5), ("4등급", 4), ("3등급", 3), ("2등급", 2), ("1등급", 1),
    ("군주", 7), ("보스", 6), ("대장", 5), ("변이종", 4),
)

# race → dungeon floor keyword mapping
_RACE_TO_FLOOR: dict[str, list[str]] = {
    "고블린": ["1층", "2층"],
    "오크": ["2층", "3층"],
    "드래곤": ["5층", "6층", "7층"],
    "뱀파이어": ["4층", "5층"],
    "몬스터": ["1층", "2층", "3층"],
}

_FALLBACK_ENEMY = Enemy(
    name="이름 모를 적",
    hp=30, max_hp=30,
    attack=8, defense=3,
    grade=1,
)


def _infer_grade(name: str, explicit: int | None) -> int:
    if explicit is not None:
        return max(1, min(9, explicit))
    for hint_str, grade in _GRADE_NAME_HINTS:
        if hint_str in name:
            return grade
    return 1


def _is_hostile(role: str | None) -> bool:
    if not role:
        return False
    return any(kw in role for kw in _HOSTILE_ROLE_KEYWORDS)


def _character_to_enemy(c: object) -> Enemy:
    from service.canon.schema import Character
    assert isinstance(c, Character)

    grade = _infer_grade(c.name, c.grade)
    base_hp = 20 + grade * 10
    base_attack = 5 + grade * 3
    base_defense = 2 + grade

    return Enemy(
        name=c.name,
        hp=base_hp, max_hp=base_hp,
        attack=base_attack,
        defense=base_defense,
        grade=grade,
        race=c.race,
        abilities=list(c.skills[:5]),
    )


class SpawnTable:
    """canon location substring → enemy template list."""

    def __init__(self, facts: CanonFacts) -> None:
        # floor keyword → [Enemy template]
        self._by_floor: dict[str, list[Enemy]] = defaultdict(list)
        # fallback
        self._default: list[Enemy] = [_FALLBACK_ENEMY]
        self._build(facts)

    def _build(self, facts: CanonFacts) -> None:
        for c in facts.characters:
            if not _is_hostile(c.role):
                continue
            template = _character_to_enemy(c)
            race = c.race or ""
            floors = _RACE_TO_FLOOR.get(race, [])
            if floors:
                for floor in floors:
                    self._by_floor[floor].append(template)
            else:
                # 기본 던전 floors
                for floor in ("1층", "2층"):
                    self._by_floor[floor].append(template)

    def spawn_for_location(self, location: str, n: int = 1) -> list[Enemy]:
        """location substring 매칭 → enemy template (최대 n개).

        매칭 없으면 fallback enemy 반환.
        """
        for floor_key, enemies in self._by_floor.items():
            if floor_key in location:
                if enemies:
                    return enemies[:n]
        return self._default[:n]

    def size(self) -> int:
        return sum(len(v) for v in self._by_floor.values())
