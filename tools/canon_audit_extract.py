"""Phase C — canon entity 추출 (★ 27B SGLang + xgrammar json_schema).

본 audit:
- wiki retained page 본 source=wiki, confidence=medium 으로 추출
- episodes 본 source=canon, confidence=high
- DC retained chunk 본 source=dc, confidence=low

본 commit 본 wiki 만 처리 (★ episodes + DC 는 후속 commit 의 별도 run).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx

from service.canon.schema import (
    CanonFacts,
    Character,
    Citation,
    Confidence,
    Essence,
    Location,
    Mechanism,
    Race,
    Source,
)

EXTRACTION_SYSTEM = (
    "당신은 한국 web novel canon audit expert. "
    "본문 entity 본 JSON schema 정합 추출. "
    "추론 X — 본 chunk 의 문장에 있는 사실만."
)

EXTRACTION_USER_TEMPLATE = """\
본 작품: 게임 속 바바리안으로 살아남기 (작가 정윤강)

다음 chunk 본 entity 본 JSON schema 정합 추출. 추측 X — 본문에 명시된 사실만.

추출 대상 (★ JSON schema 참조):
- essences: 정수
- characters: 캐릭터
- locations: 위치
- races: 종족
- mechanisms: mechanism

본 chunk source: {source_label}

본 chunk:
---
{content}
---

JSON 출력:"""

# 본 schema 본 extract 결과 root (★ optional list / required name).
EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "essences": {
            "type": "array",
            "maxItems": 30,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "maxLength": 100},
                    "grade": {"type": ["integer", "null"]},
                    "abilities_text": {"type": "string", "maxLength": 500},
                    "skills_granted": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 100},
                        "maxItems": 10,
                    },
                    "side_effects": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 200},
                        "maxItems": 10,
                    },
                    "absorption_mechanism": {
                        "type": "string",
                        "maxLength": 500,
                    },
                    "quote": {"type": "string", "maxLength": 300},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
        "characters": {
            "type": "array",
            "maxItems": 30,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "maxLength": 100},
                    "aliases": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 100},
                        "maxItems": 8,
                    },
                    "role": {"type": "string", "maxLength": 200},
                    "grade": {"type": ["integer", "null"]},
                    "race": {"type": "string", "maxLength": 50},
                    "skills": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 100},
                        "maxItems": 10,
                    },
                    "essences_absorbed": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 100},
                        "maxItems": 10,
                    },
                    "background": {"type": "string", "maxLength": 1000},
                    "quote": {"type": "string", "maxLength": 300},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
        "locations": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "maxLength": 100},
                    "location_type": {
                        "type": "string",
                        "enum": [
                            "city",
                            "dungeon",
                            "rift",
                            "facility",
                            "wilderness",
                            "district",
                        ],
                    },
                    "description": {"type": "string", "maxLength": 1000},
                    "sub_locations": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 100},
                        "maxItems": 15,
                    },
                    "quote": {"type": "string", "maxLength": 300},
                },
                "required": ["name", "location_type"],
                "additionalProperties": False,
            },
        },
        "races": {
            "type": "array",
            "maxItems": 15,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "maxLength": 80},
                    "description": {"type": "string", "maxLength": 800},
                    "abilities": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 200},
                        "maxItems": 8,
                    },
                    "quote": {"type": "string", "maxLength": 300},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
        "mechanisms": {
            "type": "array",
            "maxItems": 15,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "maxLength": 100},
                    "category": {
                        "type": "string",
                        "enum": [
                            "progression",
                            "economy",
                            "time",
                            "combat",
                            "social",
                            "magic",
                            "skill",
                        ],
                    },
                    "description": {"type": "string", "maxLength": 1000},
                    "rules": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 200},
                        "maxItems": 10,
                    },
                    "quote": {"type": "string", "maxLength": 300},
                },
                "required": ["name", "category", "description"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "essences",
        "characters",
        "locations",
        "races",
        "mechanisms",
    ],
    "additionalProperties": False,
}


def _make_citation(
    source: Source, confidence: Confidence, page_name: str, quote: str | None
) -> Citation:
    return Citation(
        source=source,
        confidence=confidence,
        wiki_page=page_name if source == Source.WIKI else None,
        quote=quote if quote else None,
    )


def _build_entities(
    extracted: dict[str, Any],
    *,
    source: Source,
    confidence: Confidence,
    page_name: str,
) -> dict[str, list[Any]]:
    essences: list[Essence] = []
    for e in extracted.get("essences", []):
        cite = _make_citation(source, confidence, page_name, e.get("quote"))
        abilities = {}
        text = e.get("abilities_text", "")
        if text:
            abilities["text"] = text[:500]
        essences.append(
            Essence(
                name=e["name"],
                grade=e.get("grade"),
                abilities=abilities,
                skills_granted=e.get("skills_granted", []),
                side_effects=e.get("side_effects", []),
                absorption_mechanism=e.get("absorption_mechanism") or None,
                citations=[cite],
            )
        )

    characters: list[Character] = []
    for c in extracted.get("characters", []):
        cite = _make_citation(source, confidence, page_name, c.get("quote"))
        characters.append(
            Character(
                name=c["name"],
                aliases=c.get("aliases", []),
                role=c.get("role") or None,
                grade=c.get("grade"),
                race=c.get("race") or None,
                skills=c.get("skills", []),
                essences_absorbed=c.get("essences_absorbed", []),
                background=c.get("background") or None,
                citations=[cite],
            )
        )

    locations: list[Location] = []
    for loc in extracted.get("locations", []):
        cite = _make_citation(source, confidence, page_name, loc.get("quote"))
        locations.append(
            Location(
                name=loc["name"],
                location_type=loc["location_type"],
                description=loc.get("description") or None,
                sub_locations=loc.get("sub_locations", []),
                citations=[cite],
            )
        )

    races: list[Race] = []
    for r in extracted.get("races", []):
        cite = _make_citation(source, confidence, page_name, r.get("quote"))
        races.append(
            Race(
                name=r["name"],
                description=r.get("description") or None,
                abilities=r.get("abilities", []),
                citations=[cite],
            )
        )

    mechanisms: list[Mechanism] = []
    for m in extracted.get("mechanisms", []):
        cite = _make_citation(source, confidence, page_name, m.get("quote"))
        mechanisms.append(
            Mechanism(
                name=m["name"],
                category=m["category"],
                description=m["description"],
                rules=m.get("rules", []),
                citations=[cite],
            )
        )

    return {
        "essences": essences,
        "characters": characters,
        "locations": locations,
        "races": races,
        "mechanisms": mechanisms,
    }


async def _extract_one(
    client: httpx.AsyncClient,
    endpoint: str,
    model: str,
    content: str,
    source_label: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {
                "role": "user",
                "content": EXTRACTION_USER_TEMPLATE.format(
                    content=content[:6000],
                    source_label=source_label,
                ),
            },
        ],
        "max_tokens": 4000,
        "temperature": 0.1,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "CanonExtraction",
                "schema": EXTRACTION_SCHEMA,
                "strict": True,
            },
        },
    }
    async with semaphore:
        resp = await client.post(
            f"{endpoint}/v1/chat/completions",
            json=payload,
            timeout=300.0,
        )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    if text is None:
        raise RuntimeError("empty content")
    extracted: dict[str, Any] = json.loads(text)
    return extracted


async def _process_wiki(
    pages_dir: Path,
    retained_names: list[str],
    *,
    endpoint: str,
    model: str,
    concurrency: int,
) -> dict[str, list[Any]]:
    """retain wiki page 본 entity 추출."""
    retained_paths = [pages_dir / name for name in retained_names]
    print(f"wiki extract: {len(retained_paths)} pages")
    semaphore = asyncio.Semaphore(concurrency)

    pooled: dict[str, list[Any]] = {
        "essences": [],
        "characters": [],
        "locations": [],
        "races": [],
        "mechanisms": [],
    }
    errors = 0

    async with httpx.AsyncClient() as client:
        async def _job(p: Path) -> tuple[str, dict[str, Any]]:
            text = p.read_text(encoding="utf-8")
            extracted = await _extract_one(
                client,
                endpoint,
                model,
                text,
                f"wiki page: {p.stem}",
                semaphore,
            )
            return (p.stem, extracted)

        tasks = {asyncio.create_task(_job(p)): p.name for p in retained_paths}
        completed = 0
        for fut in asyncio.as_completed(tasks.keys()):
            try:
                page_name, raw = await fut
                entities = _build_entities(
                    raw,
                    source=Source.WIKI,
                    confidence=Confidence.MEDIUM,
                    page_name=page_name,
                )
                for k, items in entities.items():
                    pooled[k].extend(items)
                completed += 1
                counts = {k: len(v) for k, v in entities.items()}
                print(f"  [{completed}/{len(retained_paths)}] {page_name}: {counts}")
            except Exception as e:  # noqa: BLE001
                errors += 1
                if errors <= 5:
                    print(f"  (skip) {type(e).__name__}: {e}")

    if errors:
        print(f"  total errors: {errors}")
    return pooled


def main() -> int:
    parser = argparse.ArgumentParser(description="Canon entity extraction")
    parser.add_argument(
        "--wiki-pages",
        type=Path,
        default=Path(".local/canon/audit_wiki_pages"),
    )
    parser.add_argument(
        "--wiki-scores",
        type=Path,
        default=Path(".local/canon/audit_wiki_scores.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".local/canon/canon_facts_raw.json"),
    )
    parser.add_argument("--endpoint", default="http://localhost:8081")
    parser.add_argument("--model", default="qwen3.6-27b")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    if not args.wiki_scores.exists():
        print(f"❌ wiki scores not found: {args.wiki_scores}")
        return 1

    scores_data = json.loads(args.wiki_scores.read_text(encoding="utf-8"))
    retained_names: list[str] = scores_data["retained_pages"]
    if not retained_names:
        print("❌ no retained pages")
        return 1

    t0 = time.time()
    pooled = asyncio.run(
        _process_wiki(
            args.wiki_pages,
            retained_names,
            endpoint=args.endpoint,
            model=args.model,
            concurrency=args.concurrency,
        )
    )
    elapsed = time.time() - t0

    facts = CanonFacts(
        essences=pooled["essences"],
        characters=pooled["characters"],
        locations=pooled["locations"],
        races=pooled["races"],
        mechanisms=pooled["mechanisms"],
        last_updated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        review_status="draft",
        source_stats={
            "wiki": sum(len(v) for v in pooled.values()),
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        facts.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print()
    print(f"elapsed: {elapsed:.1f}s")
    print(f"essences:   {len(facts.essences)}")
    print(f"characters: {len(facts.characters)}")
    print(f"locations:  {len(facts.locations)}")
    print(f"races:      {len(facts.races)}")
    print(f"mechanisms: {len(facts.mechanisms)}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
