"""Phase D step 5 — Entity keyword index (in-memory).

8,180 entity를 name + alias 기준으로 O(1) lookup.
keyword_match 는 substring 검색 + longest-name-first 우선순위.
fuzzy_lookup_by_name: 조사 제거 + partial match (audit-step4-2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from service.canon.schema import (
    CanonFacts,
    Character,
    Essence,
    Location,
    Mechanism,
    Race,
)

# ── 한국어 조사 목록 (긴 것 우선 정렬) ──────────────────────────────────────
_PARTICLES: tuple[str, ...] = (
    "에서", "으로", "의", "을", "를", "이", "가", "은", "는", "에", "로",
)

# entity name 내부에 나타나는 조사 ("의" 등) 제거용 pattern
_INNER_PARTICLE_RE = re.compile(r"의")


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
        self._norm_by_name: dict[str, EntityRef] = {}   # space 제거
        self._deep_by_name: dict[str, EntityRef] = {}   # space + "의" 제거
        self._source_monster_map: dict[str, list[dict[str, object]]] = {}
        self._role_map: dict[str, list[dict[str, object]]] = {}
        self._race_ability_map: dict[str, dict[str, object]] = {}
        self._build(facts)

    def _build(self, facts: CanonFacts) -> None:
        for e in facts.essences:
            ref = EntityRef("essence", e.name, _summarize_essence(e))
            self._by_name[e.name] = ref
            raw = e.model_dump()
            self._raw_essences[e.name] = raw
            self._norm_by_name[_normalize(e.name)] = ref
            self._deep_by_name[_normalize_deep(e.name)] = ref
            if e.source_monster:
                self._source_monster_map.setdefault(e.source_monster, []).append(raw)

        for c in facts.characters:
            ref = EntityRef("character", c.name, _summarize_character(c))
            self._by_name[c.name] = ref
            raw = c.model_dump()
            self._raw_characters[c.name] = raw
            self._norm_by_name[_normalize(c.name)] = ref
            self._deep_by_name[_normalize_deep(c.name)] = ref
            for alias in c.aliases:
                self._by_name[alias] = ref
                self._raw_characters[alias] = raw
                self._norm_by_name[_normalize(alias)] = ref
                self._deep_by_name[_normalize_deep(alias)] = ref
            if c.role:
                self._role_map.setdefault(c.role, []).append(raw)

        for loc in facts.locations:
            ref = EntityRef("location", loc.name, _summarize_location(loc))
            self._by_name[loc.name] = ref
            self._raw_locations[loc.name] = loc.model_dump()
            self._norm_by_name[_normalize(loc.name)] = ref
            self._deep_by_name[_normalize_deep(loc.name)] = ref

        for r in facts.races:
            ref = EntityRef("race", r.name, _summarize_race(r))
            self._by_name[r.name] = ref
            self._norm_by_name[_normalize(r.name)] = ref
            self._deep_by_name[_normalize_deep(r.name)] = ref
            at = r.ability_tiers
            if at.text:
                self._race_ability_map[r.name] = at.model_dump()

        for m in facts.mechanisms:
            ref = EntityRef("mechanism", m.name, _summarize_mechanism(m))
            self._by_name[m.name] = ref
            self._norm_by_name[_normalize(m.name)] = ref
            self._deep_by_name[_normalize_deep(m.name)] = ref

    def lookup_by_name(self, name: str) -> EntityRef | None:
        return self._by_name.get(name)

    def fuzzy_lookup(self, query: str) -> EntityRef | None:
        """fuzzy lookup — exact → normalized → deep-normalized → partial.

        1. exact: lookup_by_name(query)
        2. normalized (공백 제거): norm_by_name lookup
        3. deep-normalized (공백 + "의" 제거): deep_by_name lookup
        4. partial: deep-normalized query ↔ deep-normalized entity name
        """
        if not query:
            return None
        # 1. exact
        ref = self._by_name.get(query)
        if ref is not None:
            return ref
        # 2. normalized (공백 제거)
        norm_q = _normalize(query)
        if not norm_q:
            return None
        ref = self._norm_by_name.get(norm_q)
        if ref is not None:
            return ref
        # 3. deep-normalized ("의" 추가 제거)
        deep_q = _normalize_deep(query)
        ref = self._deep_by_name.get(deep_q)
        if ref is not None:
            return ref
        # 4. partial — 가장 긴 entity name 우선
        best: tuple[int, EntityRef] | None = None
        for deep_name, cand in self._deep_by_name.items():
            if deep_q in deep_name or deep_name in deep_q:
                length = len(deep_name)
                if best is None or length > best[0]:
                    best = (length, cand)
        return best[1] if best else None

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

    def get_essences_by_source_monster(self, monster_name: str) -> list[dict[str, object]]:
        """source_monster 정합 essence raw dict list 반환."""
        return list(self._source_monster_map.get(monster_name, []))

    def get_characters_by_role(self, role: str) -> list[dict[str, object]]:
        """taxonomy role 정합 character raw dict list 반환.

        ex: "주인공" → 비요른 / 투르윈 등, "동료" → 에르웬 / 아이나르 등.
        """
        if not role or not role.strip():
            return []
        return list(self._role_map.get(role.strip(), []))

    def get_role_for_character(self, character_name: str) -> str | None:
        """character name / alias / fuzzy lookup → role.

        exact → normalized → deep-normalized → partial 순.
        """
        if not character_name:
            return None
        # 1. exact + alias (raw_characters는 alias key 포함)
        raw = self._raw_characters.get(character_name)
        if raw is None:
            # 2. fuzzy — character entity_type만 채택
            ref = self.fuzzy_lookup(character_name)
            if ref is None or ref.entity_type != "character":
                return None
            raw = self._raw_characters.get(ref.name)
        if raw is None:
            return None
        role_val = raw.get("role")
        return str(role_val) if isinstance(role_val, str) and role_val else None

    def get_race_ability_tiers(self, race_name: str) -> dict[str, object] | None:
        """race name 정합 ability_tiers (★ 46243d5).

        return: {"text": str, "parsed": [...]} 또는 None.
        exact → fuzzy(race entity) 순.
        """
        if not race_name or not race_name.strip():
            return None
        s = race_name.strip()
        at = self._race_ability_map.get(s)
        if at is not None:
            return at
        # fuzzy — race entity_type만 채택
        ref = self.fuzzy_lookup(s)
        if ref is not None and ref.entity_type == "race":
            return self._race_ability_map.get(ref.name)
        return None

    def get_primary_essence_for_monster(self, monster_name: str) -> dict[str, object] | None:
        """source_monster 정합 essence 중 대표 1개 반환.

        우선순위: 'X 정수' 명칭 보유 → 최고 grade → 첫 등록 순.
        """
        candidates = self._source_monster_map.get(monster_name, [])
        if not candidates:
            return None
        preferred = [c for c in candidates if "정수" in str(c.get("name", ""))]
        pool = preferred if preferred else candidates

        def _grade(c: dict[str, object]) -> int:
            g = c.get("grade")
            return int(g) if isinstance(g, int) else 0

        return max(pool, key=_grade)

    def size(self) -> int:
        return len(self._by_name)


# ── normalization ─────────────────────────────────────────────────────────────


def _normalize(text: str) -> str:
    """공백 제거 + 소문자화 + 끝 조사 제거.

    ex) "고블린의 정수" → "고블린의정수"
        "정수를" → "정수"
    """
    normalized = re.sub(r"\s+", "", text.strip().lower())
    for particle in _PARTICLES:
        if normalized.endswith(particle):
            normalized = normalized[: -len(particle)]
            break
    return normalized


def _normalize_deep(text: str) -> str:
    """공백 + 내부 '의' + 끝 조사 제거.

    ex) "고블린의 정수" → "고블린정수"
        "고블린 정수" → "고블린정수"
    """
    normalized = re.sub(r"\s+", "", text.strip().lower())
    normalized = _INNER_PARTICLE_RE.sub("", normalized)
    for particle in _PARTICLES:
        if normalized.endswith(particle):
            normalized = normalized[: -len(particle)]
            break
    return normalized


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
