"""Phase D step 6a/6c — canon location → enemy spawn table."""

from __future__ import annotations

import random
from collections import defaultdict
from copy import deepcopy

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

_GRADE_NAME_HINTS: tuple[tuple[str, int], ...] = (
    ("9등급", 9), ("8등급", 8), ("7등급", 7), ("6등급", 6),
    ("5등급", 5), ("4등급", 4), ("3등급", 3), ("2등급", 2), ("1등급", 1),
    ("군주", 7), ("보스", 6), ("대장", 5), ("변이종", 4),
)

# race → dungeon floor keyword mapping (6a 보존)
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

# ── 6c: location-type spawn configuration ────────────────────────────────────

LOCATION_SPAWN_RATE: dict[str, float] = {
    "city": 0.0,
    "district": 0.0,
    "facility": 0.0,
    "dungeon": 0.30,
    "rift": 0.60,
    "wilderness": 0.20,
}

HIGH_GRADE_KEYWORDS: tuple[str, ...] = (
    "심층", "균열", "최심부", "마지막", "9층", "8층", "보스", "코어",
)
MID_GRADE_KEYWORDS: tuple[str, ...] = (
    "중층", "중간", "5층", "6층", "7층", "내부",
)
LOW_GRADE_KEYWORDS: tuple[str, ...] = (
    "입구", "1층", "2층", "초입", "외부", "표층",
)

# race description keyword → location type
RACE_LOCATION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dungeon": ("굴", "지하", "동굴", "유적", "탑", "성", "심층", "층", "구역", "탑실"),
    "wilderness": (
        "숲", "산", "들", "초원", "사막", "황무지", "평야", "강", "바다", "해변", "협곡",
    ),
    "rift": ("균열", "차원", "이세계", "어둠"),
}


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
    return Enemy(
        name=c.name,
        hp=base_hp, max_hp=base_hp,
        attack=5 + grade * 3,
        defense=2 + grade,
        grade=grade,
        race=c.race,
        abilities=list(c.skills[:5]),
    )


def _race_to_enemy(r: object) -> Enemy:
    from service.canon.schema import Race
    assert isinstance(r, Race)
    return Enemy(
        name=r.name,
        hp=25, max_hp=25,
        attack=6, defense=2,
        grade=1, race=r.name,
        abilities=list(r.abilities[:3]),
    )


def estimate_location_grade(name: str, description: str | None = None) -> int:
    """location name/description 기반 grade 추정 (1–9)."""
    text = (name + " " + (description or "")).lower()
    for kw in HIGH_GRADE_KEYWORDS:
        if kw in text:
            return 7
    for kw in MID_GRADE_KEYWORDS:
        if kw in text:
            return 4
    for kw in LOW_GRADE_KEYWORDS:
        if kw in text:
            return 1
    return 3


def spawn_count_for_grade(grade: int) -> tuple[int, int]:
    """grade → (min, max) spawn count."""
    if grade >= 7:
        return (2, 4)
    if grade >= 4:
        return (1, 2)
    return (1, 1)


def extract_race_habitat(description: str | None) -> list[str]:
    """race description에서 location type 목록 추출."""
    if not description:
        return []
    habitats: set[str] = set()
    for loc_type, keywords in RACE_LOCATION_KEYWORDS.items():
        for kw in keywords:
            if kw in description:
                habitats.add(loc_type)
                break
    return list(habitats)


class SpawnTable:
    """canon location → enemy template mapping."""

    def __init__(self, facts: CanonFacts) -> None:
        self._by_floor: dict[str, list[Enemy]] = defaultdict(list)
        self._by_location_type: dict[str, list[Enemy]] = defaultdict(list)
        self._location_grades: dict[str, int] = {}
        self._default: list[Enemy] = [_FALLBACK_ENEMY]
        self._build(facts)

    def _build(self, facts: CanonFacts) -> None:
        for loc in facts.locations:
            self._location_grades[loc.name] = estimate_location_grade(
                loc.name, loc.description
            )

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
                for floor in ("1층", "2층"):
                    self._by_floor[floor].append(template)

            race_obj = next((r for r in facts.races if r.name == race), None)
            if race_obj:
                for habitat in extract_race_habitat(race_obj.description):
                    self._by_location_type[habitat].append(template)

        for r in facts.races:
            habitats = extract_race_habitat(r.description)
            if not habitats:
                continue
            enemy = _race_to_enemy(r)
            for habitat in habitats:
                self._by_location_type[habitat].append(enemy)

    def spawn_for_location(
        self,
        location_name: str,
        location_type: str = "",
        n: int = 1,
    ) -> list[Enemy]:
        """location 기반 enemy spawn — deep copy 반환.

        location_type 없으면 floor 키워드 매칭 (6a 동작 보존).
        """
        if not location_type:
            for floor_key, enemies in self._by_floor.items():
                if floor_key in location_name:
                    if enemies:
                        return self._pick(enemies, n)
            return self._pick(self._default, n)

        if location_type in self._by_location_type:
            pool = self._by_location_type[location_type]
            if pool:
                return self._pick(pool, n)

        for floor_key, enemies in self._by_floor.items():
            if floor_key in location_name:
                if enemies:
                    return self._pick(enemies, n)

        return self._pick(self._default, n)

    def _pick(self, pool: list[Enemy], n: int) -> list[Enemy]:
        if len(pool) <= n:
            return [deepcopy(e) for e in pool]
        return [deepcopy(e) for e in random.sample(pool, n)]

    def get_location_grade(self, location_name: str) -> int:
        """location name → grade (exact → partial → default 3)."""
        if location_name in self._location_grades:
            return self._location_grades[location_name]
        for name, grade in self._location_grades.items():
            if name in location_name or location_name in name:
                return grade
        return 3

    def size(self) -> int:
        return sum(len(v) for v in self._by_floor.values())
