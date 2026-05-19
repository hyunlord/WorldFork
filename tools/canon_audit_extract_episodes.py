"""Phase C — 본문 740 ep 본 27B SGLang entity 추출.

★ wiki extraction (canon_audit_extract.py) 의 schema / helper 재사용.
★ source=canon, confidence=high, ep_number 본 citation 등재.
★ progress cache (★ .local/canon/canon_facts_episodes_cache.json) — resume 지원.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from service.canon.schema import (
    CanonFacts,
    Citation,
    Confidence,
    Source,
)

# wiki extraction 본 helper 재사용 (★ schema / system / template / build).
from tools.canon_audit_extract import (
    EXTRACTION_SCHEMA,
    EXTRACTION_SYSTEM,
    EXTRACTION_USER_TEMPLATE,
    _build_entities,
)

CONTENT_TRUNCATE = 25000
EP_NUM_RE = re.compile(r"ep_(\d{4})")


def _ep_number(path: Path) -> int:
    m = EP_NUM_RE.search(path.stem)
    if not m:
        raise ValueError(f"cannot parse ep number from {path.name}")
    return int(m.group(1))


def _attach_ep_citation(item: Any, ep_number: int) -> None:
    """본 entity 의 wiki_page citation 본 ep_number canon citation 본 swap.

    _build_entities 는 wiki citation 본 만들기 때문에, episode 본 본문
    canon citation 본 명시적 재구성.
    """
    quote = None
    if item.citations:
        quote = item.citations[0].quote
    item.citations = [
        Citation(
            source=Source.CANON,
            confidence=Confidence.HIGH,
            ep_number=ep_number,
            quote=quote,
        )
    ]


async def _extract_episode(
    client: httpx.AsyncClient,
    endpoint: str,
    model: str,
    ep_path: Path,
    semaphore: asyncio.Semaphore,
) -> tuple[int, dict[str, Any]]:
    """단일 ep 추출. error 본 caller 본 catch."""
    content = ep_path.read_text(encoding="utf-8")[:CONTENT_TRUNCATE]
    ep_number = _ep_number(ep_path)

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {
                "role": "user",
                "content": EXTRACTION_USER_TEMPLATE.format(
                    content=content,
                    source_label=f"본문 episode {ep_number} (★ canon)",
                ),
            },
        ],
        "max_tokens": 6000,
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
        raise RuntimeError(f"empty content for ep {ep_number}")
    extracted: dict[str, Any] = json.loads(text)
    return (ep_number, extracted)


def _load_cache(path: Path) -> dict[str, dict[str, Any]]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): v for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            print(f"  (cache invalid, resetting) {path}")
    return {}


def _save_cache(path: Path, cache: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )


async def _process_episodes(
    eps: list[Path],
    *,
    endpoint: str,
    model: str,
    concurrency: int,
    cache_path: Path,
    flush_every: int,
) -> dict[str, list[Any]]:
    cache = _load_cache(cache_path)
    pending = [p for p in eps if p.name not in cache]
    print(
        f"episodes: total={len(eps)} cached={len(eps) - len(pending)} "
        f"pending={len(pending)} concurrency={concurrency}"
    )

    pooled: dict[str, list[Any]] = {
        "essences": [],
        "characters": [],
        "locations": [],
        "races": [],
        "mechanisms": [],
    }

    # 1) cache 본 기존 결과 본 inject
    for ep_name, raw in cache.items():
        entities = _build_entities(
            raw,
            source=Source.CANON,
            confidence=Confidence.HIGH,
            page_name=ep_name,
        )
        try:
            ep_number = int(EP_NUM_RE.search(ep_name).group(1))  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            continue
        for k, items in entities.items():
            for item in items:
                _attach_ep_citation(item, ep_number)
                pooled[k].append(item)

    if not pending:
        return pooled

    semaphore = asyncio.Semaphore(concurrency)
    errors = 0

    async with httpx.AsyncClient() as client:
        async def _job(p: Path) -> tuple[Path, int, dict[str, Any]]:
            ep_number, raw = await _extract_episode(
                client, endpoint, model, p, semaphore
            )
            return (p, ep_number, raw)

        tasks = {asyncio.create_task(_job(p)): p.name for p in pending}
        completed = 0
        for fut in asyncio.as_completed(tasks.keys()):
            try:
                ep_path, ep_number, raw = await fut
                cache[ep_path.name] = raw
                entities = _build_entities(
                    raw,
                    source=Source.CANON,
                    confidence=Confidence.HIGH,
                    page_name=ep_path.name,
                )
                for k, items in entities.items():
                    for item in items:
                        _attach_ep_citation(item, ep_number)
                        pooled[k].append(item)
            except Exception as e:  # noqa: BLE001
                errors += 1
                if errors <= 5:
                    print(f"  (skip) {type(e).__name__}: {e}")
            completed += 1
            if completed % flush_every == 0:
                _save_cache(cache_path, cache)
                print(
                    f"  scored {completed}/{len(pending)} "
                    f"(cache saved, errors={errors})"
                )
        _save_cache(cache_path, cache)
        print(
            f"  scored {completed}/{len(pending)} "
            f"(final cache saved, errors={errors})"
        )

    return pooled


def main() -> int:
    parser = argparse.ArgumentParser(description="Episode entity extraction")
    parser.add_argument(
        "--episodes-dir",
        type=Path,
        default=Path(".local/canon/audit_episodes"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".local/canon/canon_facts_episodes_raw.json"),
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(".local/canon/canon_facts_episodes_cache.json"),
    )
    parser.add_argument("--endpoint", default="http://localhost:8081")
    parser.add_argument("--model", default="qwen3.6-27b")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--flush-every", type=int, default=20)
    parser.add_argument(
        "--ep-range",
        default=None,
        help="optional 'N-M' subset (★ inclusive)",
    )
    args = parser.parse_args()

    eps = sorted(args.episodes_dir.glob("ep_*.md"), key=_ep_number)
    if not eps:
        print(f"❌ no episodes in {args.episodes_dir}")
        return 1

    if args.ep_range:
        try:
            low_s, high_s = args.ep_range.split("-")
            low, high = int(low_s), int(high_s)
        except (ValueError, AttributeError) as exc:
            print(f"❌ invalid --ep-range: {args.ep_range}")
            raise SystemExit(1) from exc
        eps = [p for p in eps if low <= _ep_number(p) <= high]
        print(f"ep-range {low}-{high}: {len(eps)} eps")

    t0 = time.time()
    pooled = asyncio.run(
        _process_episodes(
            eps,
            endpoint=args.endpoint,
            model=args.model,
            concurrency=args.concurrency,
            cache_path=args.cache,
            flush_every=args.flush_every,
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
            "canon": sum(len(v) for v in pooled.values()),
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(facts.model_dump_json(indent=2), encoding="utf-8")

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
