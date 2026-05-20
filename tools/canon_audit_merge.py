"""Phase C — wiki + episode extraction 통합.

★ 두 raw extraction 본 entity name 본 group → merge.
★ source priority (★ canon > inferred > wiki > dc > guess) 본 citation sort.
★ field 본 canon override wiki (★ 본문 명시 본 우선).
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from service.canon.schema import (
    SOURCE_PRIORITY,
    CanonFacts,
    Character,
    Citation,
    Confidence,
    Essence,
    Location,
    Mechanism,
    Race,
    Source,
    citation_priority,
)


def _merge_citations(
    primary: list[Citation], extra: list[Citation]
) -> list[Citation]:
    seen: set[tuple[str, str, int | None, str | None, str | None]] = set()
    out: list[Citation] = []
    for c in [*primary, *extra]:
        key = (c.source, c.confidence, c.ep_number, c.wiki_page, c.dc_post_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    out.sort(key=citation_priority, reverse=True)
    return out


def _has_canon(citations: list[Citation]) -> bool:
    return any(c.source == Source.CANON for c in citations)


def _merge_essence(into: Essence, other: Essence) -> None:
    # grade — canon 본 우선
    other_canon = _has_canon(other.citations)
    if other.grade is not None and (into.grade is None or other_canon):
        into.grade = other.grade
    for k, v in other.abilities.items():
        if k not in into.abilities or other_canon:
            into.abilities[k] = v
    into.skills_granted = sorted(set(into.skills_granted + other.skills_granted))
    into.side_effects = sorted(set(into.side_effects + other.side_effects))
    if other.absorption_mechanism and (
        not into.absorption_mechanism or other_canon
    ):
        into.absorption_mechanism = other.absorption_mechanism
    into.citations = _merge_citations(into.citations, other.citations)


def _merge_character(into: Character, other: Character) -> None:
    other_canon = _has_canon(other.citations)
    into.aliases = sorted(set(into.aliases + other.aliases))
    if other.role and (not into.role or other_canon):
        into.role = other.role
    if other.grade is not None and (into.grade is None or other_canon):
        into.grade = other.grade
    if other.race and (not into.race or other_canon):
        into.race = other.race
    into.skills = sorted(set(into.skills + other.skills))
    into.essences_absorbed = sorted(
        set(into.essences_absorbed + other.essences_absorbed)
    )
    if other.background and (not into.background or other_canon):
        into.background = other.background
    into.citations = _merge_citations(into.citations, other.citations)


def _merge_location(into: Location, other: Location) -> None:
    other_canon = _has_canon(other.citations)
    into.sub_locations = sorted(set(into.sub_locations + other.sub_locations))
    if other.description and (not into.description or other_canon):
        into.description = other.description
    into.citations = _merge_citations(into.citations, other.citations)


def _merge_race(into: Race, other: Race) -> None:
    other_canon = _has_canon(other.citations)
    into.abilities = sorted(set(into.abilities + other.abilities))
    if other.description and (not into.description or other_canon):
        into.description = other.description
    into.citations = _merge_citations(into.citations, other.citations)


def _merge_mechanism(into: Mechanism, other: Mechanism) -> None:
    other_canon = _has_canon(other.citations)
    if other_canon or len(other.description) > len(into.description):
        into.description = other.description
    into.rules = sorted(set(into.rules + other.rules))
    into.citations = _merge_citations(into.citations, other.citations)


def _dedupe_essences(items: list[Essence]) -> list[Essence]:
    by_name: dict[str, Essence] = {}
    for e in items:
        key = e.name.strip()
        if key not in by_name:
            by_name[key] = e.model_copy(deep=True)
            continue
        _merge_essence(by_name[key], e)
    return sorted(by_name.values(), key=lambda x: (-(x.grade or 0), x.name))


def _dedupe_characters(items: list[Character]) -> list[Character]:
    by_name: dict[str, Character] = {}
    for c in items:
        key = c.name.strip()
        if key not in by_name:
            by_name[key] = c.model_copy(deep=True)
            continue
        _merge_character(by_name[key], c)
    return sorted(by_name.values(), key=lambda x: x.name)


def _dedupe_locations(items: list[Location]) -> list[Location]:
    by_name: dict[str, Location] = {}
    for loc in items:
        key = loc.name.strip()
        if key not in by_name:
            by_name[key] = loc.model_copy(deep=True)
            continue
        _merge_location(by_name[key], loc)
    return sorted(by_name.values(), key=lambda x: (x.location_type, x.name))


def _dedupe_races(items: list[Race]) -> list[Race]:
    by_name: dict[str, Race] = {}
    for r in items:
        key = r.name.strip()
        if key not in by_name:
            by_name[key] = r.model_copy(deep=True)
            continue
        _merge_race(by_name[key], r)
    return sorted(by_name.values(), key=lambda x: x.name)


def _dedupe_mechanisms(items: list[Mechanism]) -> list[Mechanism]:
    by_name: dict[str, Mechanism] = {}
    for m in items:
        key = m.name.strip()
        if key not in by_name:
            by_name[key] = m.model_copy(deep=True)
            continue
        _merge_mechanism(by_name[key], m)
    return sorted(by_name.values(), key=lambda x: (x.category, x.name))


def _source_stats(facts: CanonFacts) -> dict[str, int]:
    counter: dict[str, int] = {}
    for group in (
        facts.essences,
        facts.characters,
        facts.locations,
        facts.races,
        facts.mechanisms,
    ):
        for item in group:
            citations = getattr(item, "citations", None) or []
            if not citations:
                counter["uncited"] = counter.get("uncited", 0) + 1
                continue
            strongest = max(citations, key=citation_priority)
            key = strongest.source.value
            counter[key] = counter.get(key, 0) + 1
    return counter


def _cross_ref_stats(facts: CanonFacts) -> dict[str, int]:
    """본 entity 본 source coverage 본 명시 bucket."""
    stats = {
        "wiki_only": 0,
        "canon_only": 0,
        "dc_only": 0,
        "wiki_and_canon": 0,
        "wiki_and_dc": 0,
        "canon_and_dc": 0,
        "wiki_canon_dc": 0,
        "other": 0,
    }
    for group in (
        facts.essences,
        facts.characters,
        facts.locations,
        facts.races,
        facts.mechanisms,
    ):
        for item in group:
            citations = getattr(item, "citations", None) or []
            sources = {c.source for c in citations}
            has_wiki = Source.WIKI in sources
            has_canon = Source.CANON in sources
            has_dc = Source.DC in sources
            if has_wiki and has_canon and has_dc:
                stats["wiki_canon_dc"] += 1
            elif has_wiki and has_canon:
                stats["wiki_and_canon"] += 1
            elif has_canon and has_dc:
                stats["canon_and_dc"] += 1
            elif has_wiki and has_dc:
                stats["wiki_and_dc"] += 1
            elif has_canon:
                stats["canon_only"] += 1
            elif has_wiki:
                stats["wiki_only"] += 1
            elif has_dc:
                stats["dc_only"] += 1
            else:
                stats["other"] += 1
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge wiki + episode extraction")
    parser.add_argument(
        "--wiki",
        type=Path,
        default=Path(".local/canon/canon_facts.json"),
    )
    parser.add_argument(
        "--episodes",
        type=Path,
        default=Path(".local/canon/canon_facts_episodes_raw.json"),
    )
    parser.add_argument(
        "--dc",
        type=Path,
        default=None,
        help="optional DC raw extraction (★ canon_facts_dc_raw.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".local/canon/canon_facts_v2.json"),
    )
    parser.add_argument(
        "--version",
        default="2.0.0",
        help="output version string",
    )
    args = parser.parse_args()

    if not args.wiki.exists():
        print(f"❌ wiki input not found: {args.wiki}")
        return 1
    if not args.episodes.exists():
        print(f"❌ episodes input not found: {args.episodes}")
        return 1

    wiki_facts = CanonFacts.model_validate_json(
        args.wiki.read_text(encoding="utf-8")
    )
    ep_facts = CanonFacts.model_validate_json(
        args.episodes.read_text(encoding="utf-8")
    )
    dc_facts: CanonFacts | None = None
    if args.dc is not None:
        if not args.dc.exists():
            print(f"❌ dc input not found: {args.dc}")
            return 1
        dc_facts = CanonFacts.model_validate_json(
            args.dc.read_text(encoding="utf-8")
        )

    print(
        f"wiki:  e={len(wiki_facts.essences)} c={len(wiki_facts.characters)} "
        f"l={len(wiki_facts.locations)} r={len(wiki_facts.races)} "
        f"m={len(wiki_facts.mechanisms)}"
    )
    print(
        f"eps:   e={len(ep_facts.essences)} c={len(ep_facts.characters)} "
        f"l={len(ep_facts.locations)} r={len(ep_facts.races)} "
        f"m={len(ep_facts.mechanisms)}"
    )
    if dc_facts is not None:
        print(
            f"dc:    e={len(dc_facts.essences)} c={len(dc_facts.characters)} "
            f"l={len(dc_facts.locations)} r={len(dc_facts.races)} "
            f"m={len(dc_facts.mechanisms)}"
        )

    def _concat(attr: str) -> list[Any]:
        out = list(getattr(wiki_facts, attr)) + list(getattr(ep_facts, attr))
        if dc_facts is not None:
            out += list(getattr(dc_facts, attr))
        return out

    merged = CanonFacts(
        essences=_dedupe_essences(_concat("essences")),
        characters=_dedupe_characters(_concat("characters")),
        locations=_dedupe_locations(_concat("locations")),
        races=_dedupe_races(_concat("races")),
        mechanisms=_dedupe_mechanisms(_concat("mechanisms")),
        version=args.version,
        last_updated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        review_status="draft",
    )
    merged.source_stats = _source_stats(merged)
    cross = _cross_ref_stats(merged)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(merged.model_dump_json(indent=2), encoding="utf-8")

    print()
    label = f"v{args.version.split('.')[0]}"
    print(f"=== merged ({label}) ===")
    print(f"essences:   {len(merged.essences)}")
    print(f"characters: {len(merged.characters)}")
    print(f"locations:  {len(merged.locations)}")
    print(f"races:      {len(merged.races)}")
    print(f"mechanisms: {len(merged.mechanisms)}")
    print(f"source_stats: {merged.source_stats}")
    print(f"cross-ref:    {cross}")
    print(f"output: {args.output}")
    print(f"priority key: {SOURCE_PRIORITY}")
    _ = Confidence  # imported for downstream consumers
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
