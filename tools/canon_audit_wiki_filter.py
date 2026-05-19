"""Phase C — namuwiki 161 page 본 27B canon 정합 score → threshold retain.

★ Phase A.3-b xgrammar pattern 채택 — SGLang response_format json_schema 강제.
★ error 본 batch level 본 per-task catch (★ hardcoded score sentinel 회피).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx

WIKI_CANON_SYSTEM = (
    "당신은 한국어 web novel canon audit expert. "
    "page title + content 의 surface feature 만 판단."
)

WIKI_CANON_USER_TEMPLATE = """\
다음 namuwiki page 가 web novel '게임 속 바바리안으로 살아남기' (작가 정윤강)\
 와 직접 관련된 정도를 점수 0.0-1.0 으로 평가.

기준:
- 1.0: 본 작품 directly (★ 작품 본체 / 등장인물 / 설정 / 미궁 / 정수 / 종족 / 몬스터)
- 0.7-0.9: 본 작품 spinoff (★ 웹툰 / 갤러리 / 작품 본 캐릭터)
- 0.4-0.6: 유사 작품 또는 동일 genre (★ 게임 빙의물 / 비슷 작품)
- 0.0-0.3: 무관 (★ 한국어 문법 / 영화 / 군 / 다른 작품 / 일반 상식)

본 page 본 첫 부분:
---
{content}
---

JSON 출력:"""

WIKI_CANON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "canon_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "page_title": {"type": "string", "maxLength": 200},
        "reason": {"type": "string", "maxLength": 200},
    },
    "required": ["canon_score", "page_title", "reason"],
    "additionalProperties": False,
}

CONTENT_TRUNCATE = 3000


async def _score_page(
    client: httpx.AsyncClient,
    endpoint: str,
    model: str,
    page_path: Path,
    semaphore: asyncio.Semaphore,
) -> tuple[Path, float, str, str]:
    """단일 page score. error 시 raise (★ batch level catch)."""
    text = page_path.read_text(encoding="utf-8")[:CONTENT_TRUNCATE]
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": WIKI_CANON_SYSTEM},
            {
                "role": "user",
                "content": WIKI_CANON_USER_TEMPLATE.format(content=text),
            },
        ],
        "max_tokens": 300,
        "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "WikiCanonScore",
                "schema": WIKI_CANON_SCHEMA,
                "strict": True,
            },
        },
    }
    async with semaphore:
        resp = await client.post(
            f"{endpoint}/v1/chat/completions", json=payload, timeout=120.0
        )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    if content is None:
        raise RuntimeError(f"empty content for {page_path.name}")
    parsed = json.loads(content)
    score = float(parsed["canon_score"])
    score = max(0.0, min(1.0, score))
    title = str(parsed.get("page_title", page_path.stem))[:200]
    reason = str(parsed.get("reason", ""))[:200]
    return (page_path, score, title, reason)


async def _filter_all(
    pages: list[Path],
    *,
    endpoint: str,
    model: str,
    concurrency: int,
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[dict[str, Any]] = []
    errors = 0

    async with httpx.AsyncClient() as client:
        async def _job(p: Path) -> dict[str, Any]:
            path, score, title, reason = await _score_page(
                client, endpoint, model, p, semaphore
            )
            return {
                "page": path.name,
                "title": title,
                "score": score,
                "reason": reason,
            }

        tasks = {asyncio.create_task(_job(p)): p.name for p in pages}
        for fut in asyncio.as_completed(tasks.keys()):
            try:
                results.append(await fut)
            except Exception as e:  # noqa: BLE001
                errors += 1
                if errors <= 5:
                    print(f"  (skip) {type(e).__name__}: {e}")

    if errors:
        print(f"  total errors: {errors}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="namuwiki canon filter")
    parser.add_argument(
        "--pages-dir",
        type=Path,
        default=Path(".local/canon/audit_wiki_pages"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".local/canon/audit_wiki_scores.json"),
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--endpoint", default="http://localhost:8081")
    parser.add_argument("--model", default="qwen3.6-27b")
    args = parser.parse_args()

    pages = sorted(args.pages_dir.glob("*.md"))
    if not pages:
        print(f"❌ no pages in {args.pages_dir}")
        return 1
    print(f"scoring {len(pages)} pages (concurrency={args.concurrency}) …")

    t0 = time.time()
    results = asyncio.run(
        _filter_all(
            pages,
            endpoint=args.endpoint,
            model=args.model,
            concurrency=args.concurrency,
        )
    )
    elapsed = time.time() - t0
    results.sort(key=lambda r: float(r["score"]), reverse=True)

    retained = [r for r in results if float(r["score"]) >= args.threshold]
    summary = {
        "all": results,
        "retained_pages": [r["page"] for r in retained],
        "threshold": args.threshold,
        "total": len(pages),
        "retained_count": len(retained),
        "elapsed_seconds": round(elapsed, 1),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"elapsed: {elapsed:.1f}s")
    print(f"retained: {len(retained)}/{len(pages)} (threshold={args.threshold})")
    print(f"output: {args.output}")
    print()
    print("retained (top 20):")
    for r in retained[:20]:
        print(f"  {r['score']:.2f}  {r['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
