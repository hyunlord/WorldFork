"""Phase C — canon_facts_raw.json 본 dedupe + cross-reference.

본 entity 본 name 기준 group → merge citations + source priority.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from pydantic import BaseModel

from service.canon.schema import (
    SOURCE_PRIORITY,
    CanonFacts,
    Character,
    Citation,
    Essence,
    Location,
    Mechanism,
    Race,
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


def _strongest_citation(item: BaseModel) -> int:
    citations = getattr(item, "citations", None) or []
    if not citations:
        return 0
    return max(citation_priority(c) for c in citations)


def _dedupe_essences(items: list[Essence]) -> list[Essence]:
    by_name: dict[str, Essence] = {}
    for e in items:
        key = e.name.strip()
        if key not in by_name:
            by_name[key] = e.model_copy(deep=True)
            continue
        merged = by_name[key]
        if e.grade is not None and merged.grade is None:
            merged.grade = e.grade
        for k, v in e.abilities.items():
            if k not in merged.abilities:
                merged.abilities[k] = v
        merged.skills_granted = sorted(set(merged.skills_granted + e.skills_granted))
        merged.side_effects = sorted(set(merged.side_effects + e.side_effects))
        if e.absorption_mechanism and not merged.absorption_mechanism:
            merged.absorption_mechanism = e.absorption_mechanism
        merged.citations = _merge_citations(merged.citations, e.citations)
    return sorted(
        by_name.values(),
        key=lambda x: (-(x.grade or 0), x.name),
    )


def _dedupe_characters(items: list[Character]) -> list[Character]:
    by_name: dict[str, Character] = {}
    for c in items:
        key = c.name.strip()
        if key not in by_name:
            by_name[key] = c.model_copy(deep=True)
            continue
        merged = by_name[key]
        merged.aliases = sorted(set(merged.aliases + c.aliases))
        if c.role and not merged.role:
            merged.role = c.role
        if c.grade is not None and merged.grade is None:
            merged.grade = c.grade
        if c.race and not merged.race:
            merged.race = c.race
        merged.skills = sorted(set(merged.skills + c.skills))
        merged.essences_absorbed = sorted(
            set(merged.essences_absorbed + c.essences_absorbed)
        )
        if c.background and not merged.background:
            merged.background = c.background
        merged.citations = _merge_citations(merged.citations, c.citations)
    return sorted(
        by_name.values(),
        key=lambda x: (-_strongest_citation(x), x.name),
    )


def _dedupe_locations(items: list[Location]) -> list[Location]:
    by_name: dict[str, Location] = {}
    for loc in items:
        key = loc.name.strip()
        if key not in by_name:
            by_name[key] = loc.model_copy(deep=True)
            continue
        merged = by_name[key]
        merged.sub_locations = sorted(set(merged.sub_locations + loc.sub_locations))
        if loc.description and not merged.description:
            merged.description = loc.description
        merged.citations = _merge_citations(merged.citations, loc.citations)
    return sorted(by_name.values(), key=lambda x: (x.location_type, x.name))


def _dedupe_races(items: list[Race]) -> list[Race]:
    by_name: dict[str, Race] = {}
    for r in items:
        key = r.name.strip()
        if key not in by_name:
            by_name[key] = r.model_copy(deep=True)
            continue
        merged = by_name[key]
        merged.abilities = sorted(set(merged.abilities + r.abilities))
        if r.description and not merged.description:
            merged.description = r.description
        merged.citations = _merge_citations(merged.citations, r.citations)
    return sorted(by_name.values(), key=lambda x: x.name)


def _dedupe_mechanisms(items: list[Mechanism]) -> list[Mechanism]:
    by_name: dict[str, Mechanism] = {}
    for m in items:
        key = m.name.strip()
        if key not in by_name:
            by_name[key] = m.model_copy(deep=True)
            continue
        merged = by_name[key]
        if len(m.description) > len(merged.description):
            merged.description = m.description
        merged.rules = sorted(set(merged.rules + m.rules))
        merged.citations = _merge_citations(merged.citations, m.citations)
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
                counter.setdefault("uncited", 0)
                counter["uncited"] += 1
                continue
            # strongest citation determines bucket
            strongest = max(citations, key=citation_priority)
            key = strongest.source.value
            counter.setdefault(key, 0)
            counter[key] += 1
    return counter


def main() -> int:
    parser = argparse.ArgumentParser(description="Canon facts dedupe")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(".local/canon/canon_facts_raw.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".local/canon/canon_facts.json"),
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"❌ input not found: {args.input}")
        return 1

    raw = CanonFacts.model_validate_json(args.input.read_text(encoding="utf-8"))
    print(f"raw counts: e={len(raw.essences)} c={len(raw.characters)} "
          f"l={len(raw.locations)} r={len(raw.races)} m={len(raw.mechanisms)}")

    deduped = CanonFacts(
        essences=_dedupe_essences(raw.essences),
        characters=_dedupe_characters(raw.characters),
        locations=_dedupe_locations(raw.locations),
        races=_dedupe_races(raw.races),
        mechanisms=_dedupe_mechanisms(raw.mechanisms),
        version=raw.version,
        last_updated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        review_status="draft",
    )
    deduped.source_stats = _source_stats(deduped)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        deduped.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print()
    print("=== deduped ===")
    print(f"essences:   {len(deduped.essences)}")
    print(f"characters: {len(deduped.characters)}")
    print(f"locations:  {len(deduped.locations)}")
    print(f"races:      {len(deduped.races)}")
    print(f"mechanisms: {len(deduped.mechanisms)}")
    print(f"source_stats: {deduped.source_stats}")
    print(f"output: {args.output}")
    print(f"priority key (★ tie-break reference): {SOURCE_PRIORITY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
