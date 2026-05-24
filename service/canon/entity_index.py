"""Phase D step 5 — Entity keyword index (in-memory).

8,180 entity를 name + alias 기준으로 O(1) lookup.
keyword_match 는 substring 검색 + longest-name-first 우선순위.
"""

from __future__ import annotations

from dataclasses import dataclass

from service.canon.schema import (
    CanonFacts,
    Character,
    Essence,
    Location,
    Mechanism,
    Race,
)


@dataclass(frozen=True)
class EntityRef:
    """단일 entity 참조 — type + name + 요약."""

    entity_type: str  # essence / character / location / race / mechanism
    name: str
    summary: str  # max 300 chars


class EntityIndex:
    """name / alias 기준 O(1) entity lookup."""

    def __init__(self, facts: CanonFacts) -> None:
        self._by_name: dict[str, EntityRef] = {}
        self._raw_essences: dict[str, dict[str, object]] = {}
        self._raw_characters: dict[str, dict[str, object]] = {}
        self._raw_locations: dict[str, dict[str, object]] = {}
        self._build(facts)

    def _build(self, facts: CanonFacts) -> None:
        for e in facts.essences:
            ref = EntityRef("essence", e.name, _summarize_essence(e))
            self._by_name[e.name] = ref
            self._raw_essences[e.name] = e.model_dump()

        for c in facts.characters:
            ref = EntityRef("character", c.name, _summarize_character(c))
            self._by_name[c.name] = ref
            raw = c.model_dump()
            self._raw_characters[c.name] = raw
            for alias in c.aliases:
                self._by_name[alias] = ref
                self._raw_characters[alias] = raw

        for loc in facts.locations:
            ref = EntityRef("location", loc.name, _summarize_location(loc))
            self._by_name[loc.name] = ref
            self._raw_locations[loc.name] = loc.model_dump()

        for r in facts.races:
            ref = EntityRef("race", r.name, _summarize_race(r))
            self._by_name[r.name] = ref

        for m in facts.mechanisms:
            ref = EntityRef("mechanism", m.name, _summarize_mechanism(m))
            self._by_name[m.name] = ref

    def lookup_by_name(self, name: str) -> EntityRef | None:
        return self._by_name.get(name)

    def lookup_many(self, names: list[str]) -> list[EntityRef]:
        return [ref for name in names if (ref := self.lookup_by_name(name))]

    def keyword_match(self, text: str, limit: int = 5) -> list[EntityRef]:
        """text 내 entity name substring 매칭. 긴 name 우선."""
        hits: list[tuple[int, EntityRef]] = []
        for name, ref in self._by_name.items():
            if name in text:
                hits.append((len(name), ref))
        hits.sort(key=lambda x: -x[0])
        seen: set[str] = set()
        result: list[EntityRef] = []
        for _, ref in hits:
            key = f"{ref.entity_type}:{ref.name}"
            if key not in seen:
                seen.add(key)
                result.append(ref)
            if len(result) >= limit:
                break
        return result

    def get_raw_essence(self, name: str) -> dict[str, object] | None:
        """essence name → raw dict (abilities parse용)."""
        return self._raw_essences.get(name)

    def get_raw_character(self, name: str) -> dict[str, object] | None:
        """character name/alias → raw dict (role/background 활용)."""
        return self._raw_characters.get(name)

    def get_raw_location(self, name: str) -> dict[str, object] | None:
        """location name → raw dict (description/sub_locations 활용)."""
        return self._raw_locations.get(name)

    def size(self) -> int:
        return len(self._by_name)


# ── summary helpers ───────────────────────────────────────────────────────────


def _summarize_essence(e: Essence) -> str:
    parts = [f"정수 {e.name}"]
    if e.grade is not None:
        parts.append(f"{e.grade}등급")
    if e.skills_granted:
        parts.append(f"스킬: {', '.join(e.skills_granted[:3])}")
    if e.absorption_mechanism:
        parts.append(e.absorption_mechanism[:100])
    return " · ".join(parts)[:300]


def _summarize_character(c: Character) -> str:
    parts = [f"캐릭터 {c.name}"]
    if c.role:
        parts.append(c.role)
    if c.race:
        parts.append(c.race)
    if c.grade is not None:
        parts.append(f"{c.grade}등급")
    if c.background:
        parts.append(c.background[:100])
    return " · ".join(parts)[:300]


def _summarize_location(loc: Location) -> str:
    parts = [f"{loc.location_type} {loc.name}"]
    if loc.description:
        parts.append(loc.description[:150])
    return " · ".join(parts)[:300]


def _summarize_race(r: Race) -> str:
    parts = [f"종족 {r.name}"]
    if r.description:
        parts.append(r.description[:150])
    return " · ".join(parts)[:300]


def _summarize_mechanism(m: Mechanism) -> str:
    return f"{m.category} {m.name} · {m.description[:200]}"[:300]
