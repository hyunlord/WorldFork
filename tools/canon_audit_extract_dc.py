"""Phase C — DC 7,091 entry 본 27B SGLang batched entity 추출.

★ batch 단위 호출 (★ entry 본 짧음, 평균 ~452 char).
★ source=dc, confidence=low, dc_post_id 본 citation.
★ progress cache (★ batch_NNN_NNN 단위) — resume 지원.
★ EXTRACTION_SCHEMA 재사용 (★ wiki/episode extract 와 동일).
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
from tools.canon_audit_extract import (
    EXTRACTION_SCHEMA,
    _build_entities,
)

ENTRY_NO_RE = re.compile(r"entry_(\d+)")

DC_EXTRACTION_SYSTEM = (
    "당신은 한국 web novel canon entity extraction expert. "
    "DC 게시판 post 본 fan 토론 (★ source=dc, confidence=low). "
    "본문 명시 entity 만 추출 — fan speculation 본 retain OK. "
    "meta 노이즈 ('GM', '갤러리 운영' 등) 본 reject."
)

DC_EXTRACTION_USER_TEMPLATE = """\
다음 DC 게시판 entries 본 entity 추출.

작품: 게임 속 바바리안으로 살아남기 (작가 정윤강)
source: DC inside 마이너 갤러리 (★ fan 토론, confidence=low)

추출 RULE:
- 본 entry 본 directly mention 본 entity 만 (★ 본 entry 본 post_no header)
- 본문 명시 (★ 비요른 / 미궁 / 정수 등) 본 추출 OK
- fan theory / 추측 (★ "창세보구 본 미래에 사용") 본 reasonable speculation 만 retain
- 본 batch 본 entity 별 post_no citation 기록 (★ schema 본 quote 필드)
- "GM", "ㅇㅇ" 본 meta noise 본 reject
- 본 entity 본 본 entry 본 정확 reference

본 batch 본 {batch_size} entries:
---
{content}
---

JSON 출력:"""

CONTENT_TRUNCATE = 28000


def _entry_post_no(path: Path) -> int:
    m = ENTRY_NO_RE.search(path.stem)
    if not m:
        raise ValueError(f"cannot parse entry no from {path.name}")
    return int(m.group(1))


def _batch_label(entries: list[Path]) -> str:
    first = _entry_post_no(entries[0])
    last = _entry_post_no(entries[-1])
    return f"{first:06d}_{last:06d}"


def _build_batch_content(entries: list[Path]) -> str:
    parts: list[str] = []
    for ep in entries:
        text = ep.read_text(encoding="utf-8")
        parts.append(f"\n=== DC entry post_no={_entry_post_no(ep)} ===\n{text}\n")
    return "\n".join(parts)


def _attach_dc_citation(item: Any, entry_post_nos: list[int]) -> None:
    """본 entity 의 wiki_page citation 을 dc_post_id citation 본 swap.

    quote 본 _build_entities 본 처음 citation 본 quote 본 유지.
    본 batch 본 본 entry 본 post_no 본 attribute (★ joined).
    """
    quote = None
    if item.citations:
        quote = item.citations[0].quote
    # 본 batch 본 첫 post_no 본 representative dc_post_id (★ batch evidence)
    representative = entry_post_nos[0] if entry_post_nos else 0
    item.citations = [
        Citation(
            source=Source.DC,
            confidence=Confidence.LOW,
            dc_post_id=str(representative),
            quote=quote,
        )
    ]


async def _extract_dc_batch(
    client: httpx.AsyncClient,
    endpoint: str,
    model: str,
    entries: list[Path],
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    content = _build_batch_content(entries)[:CONTENT_TRUNCATE]
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": DC_EXTRACTION_SYSTEM},
            {
                "role": "user",
                "content": DC_EXTRACTION_USER_TEMPLATE.format(
                    batch_size=len(entries),
                    content=content,
                ),
            },
        ],
        "max_tokens": 6000,
        "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "DCBatchExtraction",
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
        raise RuntimeError(f"empty content for batch {_batch_label(entries)}")
    extracted: dict[str, Any] = json.loads(text)
    return extracted


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


async def _process_dc(
    batches: list[list[Path]],
    *,
    endpoint: str,
    model: str,
    concurrency: int,
    cache_path: Path,
    flush_every: int,
) -> dict[str, list[Any]]:
    cache = _load_cache(cache_path)
    pending = [b for b in batches if _batch_label(b) not in cache]
    print(
        f"DC: total_batches={len(batches)} cached={len(batches) - len(pending)} "
        f"pending={len(pending)} concurrency={concurrency}"
    )

    pooled: dict[str, list[Any]] = {
        "essences": [],
        "characters": [],
        "locations": [],
        "races": [],
        "mechanisms": [],
    }

    # 1) cache 본 결과 본 inject
    for label, raw in cache.items():
        entities = _build_entities(
            raw,
            source=Source.DC,
            confidence=Confidence.LOW,
            page_name=label,
        )
        try:
            first_no = int(label.split("_")[0])
        except (ValueError, IndexError):
            continue
        for k, items in entities.items():
            for item in items:
                _attach_dc_citation(item, [first_no])
                pooled[k].append(item)

    if not pending:
        return pooled

    semaphore = asyncio.Semaphore(concurrency)
    errors = 0

    async with httpx.AsyncClient() as client:
        async def _job(batch: list[Path]) -> tuple[str, list[int], dict[str, Any]]:
            label = _batch_label(batch)
            raw = await _extract_dc_batch(client, endpoint, model, batch, semaphore)
            post_nos = [_entry_post_no(p) for p in batch]
            return (label, post_nos, raw)

        tasks = {
            asyncio.create_task(_job(b)): _batch_label(b) for b in pending
        }
        completed = 0
        for fut in asyncio.as_completed(tasks.keys()):
            try:
                label, post_nos, raw = await fut
                cache[label] = raw
                entities = _build_entities(
                    raw,
                    source=Source.DC,
                    confidence=Confidence.LOW,
                    page_name=label,
                )
                for k, items in entities.items():
                    for item in items:
                        _attach_dc_citation(item, post_nos)
                        pooled[k].append(item)
            except Exception as e:  # noqa: BLE001
                errors += 1
                if errors <= 5:
                    print(f"  (skip) {type(e).__name__}: {e}")
            completed += 1
            if completed % flush_every == 0:
                _save_cache(cache_path, cache)
                print(
                    f"  scored {completed}/{len(pending)} batches "
                    f"(cache saved, errors={errors})"
                )
        _save_cache(cache_path, cache)
        print(
            f"  scored {completed}/{len(pending)} batches "
            f"(final cache saved, errors={errors})"
        )

    return pooled


def _make_batches(entries: list[Path], batch_size: int) -> list[list[Path]]:
    return [
        entries[i : i + batch_size]
        for i in range(0, len(entries), batch_size)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="DC entry entity extraction")
    parser.add_argument(
        "--entries-dir",
        type=Path,
        default=Path(".local/canon/audit_dc_entries"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".local/canon/canon_facts_dc_raw.json"),
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(".local/canon/canon_facts_dc_cache.json"),
    )
    parser.add_argument("--endpoint", default="http://localhost:8081")
    parser.add_argument("--model", default="qwen3.6-27b")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--flush-every", type=int, default=10)
    args = parser.parse_args()

    entries = sorted(args.entries_dir.glob("entry_*.md"), key=_entry_post_no)
    if not entries:
        print(f"❌ no entries in {args.entries_dir}")
        return 1
    batches = _make_batches(entries, args.batch_size)
    print(f"DC entries: {len(entries)}, batches: {len(batches)}")

    t0 = time.time()
    pooled = asyncio.run(
        _process_dc(
            batches,
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
            "dc": sum(len(v) for v in pooled.values()),
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
