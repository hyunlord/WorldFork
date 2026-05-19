"""Claude.ai project knowledge 업로드용 정리.

Phase 9.19-a (초안) — namuwiki + DC posts 본 28MB 안전 margin 본 chunking.
Phase C prepare — episode 흡수 + DC CANON_KEYWORDS first-pass filter.
Phase C LLM 2-pass — 9B (llama-server :8083) 의 surface-feature canon
classification 본 추가. keyword / LLM / union / intersect mode 본 선택.

사용:
  python scripts/prepare_canon_upload.py
  python scripts/prepare_canon_upload.py --dc-filter-mode union
  python scripts/prepare_canon_upload.py --dc-filter-mode llm --llm-score-threshold 0.5

score cache 본 .local/canon/dc/canon_scores.json (★ 재실행 시 resume).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx

MAX_BYTES = 28 * 1024 * 1024  # 28MB safety margin (★ Claude.ai 30MB cap)
EPISODE_BATCH_SIZE = 100

CANON_DIR = Path(".local/canon")
EP_SRC = CANON_DIR / "episodes"
NAMU_SRC = CANON_DIR / "namuwiki"
DC_POSTS_SRC = CANON_DIR / "dc" / "posts"
UPLOAD_DIR = CANON_DIR / "upload_ready"
EP_DST = UPLOAD_DIR / "episodes"
SCORE_CACHE_PATH = CANON_DIR / "dc" / "canon_scores.json"
EXCLUDED_SAMPLE_PATH = UPLOAD_DIR / "_excluded_dc_sample.md"

CANON_KEYWORDS: frozenset[str] = frozenset(
    {
        "비요른", "에르웬", "한스", "에쉬드", "셰인",
        "아이나르", "미샤", "카나바로",
        "정수", "마석", "균열", "등급", "탐험가",
        "수호자", "계층군주", "수정동굴",
        "라프도니아", "라스카니아", "노아르크",
        "도서관", "라비기온", "파르시티에브",
        "핏빛성채", "빙하굴", "강철의 묘",
        "녹색탄광", "망자의 땅",
        "드워프", "오크", "고블린", "약탈자",
        "겜바바", "바바리안",
    }
)

CANON_SCORE_SYSTEM = (
    "당신은 한국어 web novel 게시판 post 분류 expert. "
    "surface 만 판단하고 본문 사실 검증은 X."
)

CANON_SCORE_USER_TEMPLATE = """\
다음 post 가 web novel 본문 (캐릭터 / 던전 / 마법 / 전투 / 줄거리) 토론인지 점수 0.0-1.0.

기준:
- 1.0: 본문 캐릭터 / 본문 mechanism (정수, 마석, 균열, 등급 등) / 본문 이벤트 토론
- 0.7-0.9: 본문 entity mention + 의견/분석
- 0.4-0.6: 본문 일부 mention but 짧음
- 0.0-0.3: 메타 (작가 / 휴재 / 굿즈 / spoiler 신고 / 갤러리 운영)

Post:
{content}

JSON 출력:"""

CANON_SCORE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "canon_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string", "maxLength": 200},
    },
    "required": ["canon_score", "reason"],
    "additionalProperties": False,
}

CONTENT_TRUNCATE = 3000


def _score_keyword(text: str) -> int:
    return sum(1 for kw in CANON_KEYWORDS if kw in text)


def _flush(out: Path, header: str, chunks: list[str]) -> None:
    text = header + "".join(chunks)
    out.write_text(text, encoding="utf-8")
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"  {out.name}: {size_mb:.2f} MB ({len(chunks)} entries)")


def prepare_episodes() -> int:
    """본문 740 episode 본 100ep batch 본 chunked .md."""
    if not EP_SRC.exists():
        print(f"  (skip) {EP_SRC} not found")
        return 0
    eps = sorted(EP_SRC.glob("episode_*.txt"))
    if not eps:
        print("  (skip) no episodes")
        return 0
    EP_DST.mkdir(parents=True, exist_ok=True)
    for old in EP_DST.glob("episodes_*.md"):
        old.unlink()
    print(f"episodes: {len(eps)} files")
    saved = 0
    for batch_start in range(0, len(eps), EPISODE_BATCH_SIZE):
        batch = eps[batch_start : batch_start + EPISODE_BATCH_SIZE]
        start_num = batch_start + 1
        end_num = batch_start + len(batch)
        out_path = EP_DST / f"episodes_{start_num:04d}-{end_num:04d}.md"
        parts: list[str] = []
        parts.append(f"# Episodes {start_num}-{end_num}\n\n")
        parts.append(
            "본 file 은 본인 manual upload 용 Claude.ai project knowledge. "
            "audit + canon 추적 기반 자료.\n\n"
        )
        for ep_path in batch:
            ep_num = ep_path.stem.split("_")[1]
            content = ep_path.read_text(encoding="utf-8")
            parts.append(f"\n## Episode {ep_num}\n\n")
            parts.append(content)
            if not content.endswith("\n"):
                parts.append("\n")
            parts.append("\n---\n")
        out_path.write_text("".join(parts), encoding="utf-8")
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  {out_path.name}: {size_mb:.2f} MB ({len(batch)} eps)")
        saved += 1
    print(f"episodes: {saved} batches")
    return saved


def prepare_namuwiki() -> int:
    if not NAMU_SRC.exists():
        print(f"  (skip) {NAMU_SRC} not found")
        return 0
    pages = sorted(NAMU_SRC.glob("*.md"))
    if not pages:
        print("  (skip) no namuwiki pages")
        return 0
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for old in UPLOAD_DIR.glob("namuwiki_*.md"):
        old.unlink()
    print(f"namuwiki: {len(pages)} pages")
    batch: list[str] = []
    batch_idx = 1
    cur_bytes = 0
    saved = 0

    def out_path(idx: int) -> Path:
        return UPLOAD_DIR / f"namuwiki_{idx:03d}.md"

    header = (
        "# Namuwiki canon 자료\n\n"
        "본 file 은 namuwiki crawl 의 통합본 "
        "(★ 게임 속 바바리안으로 살아남기 + 직접 link). "
        "audit + 본문 reference.\n\n"
    )
    for page in pages:
        content = f"\n---\n\n{page.read_text(encoding='utf-8')}\n"
        page_bytes = len(content.encode("utf-8"))
        if cur_bytes + page_bytes > MAX_BYTES and batch:
            _flush(out_path(batch_idx), header, batch)
            saved += 1
            batch = []
            cur_bytes = 0
            batch_idx += 1
        batch.append(content)
        cur_bytes += page_bytes
    if batch:
        _flush(out_path(batch_idx), header, batch)
        saved += 1
    print(f"namuwiki: {saved} batches")
    return saved


# ---------------------------------------------------------------------------
# LLM 2-pass — 9B canon score
# ---------------------------------------------------------------------------


async def _score_one_llm(
    client: httpx.AsyncClient,
    endpoint: str,
    model: str,
    content: str,
    semaphore: asyncio.Semaphore,
) -> tuple[float, str]:
    """9B 단일 post score. fail 시 (0.0, '<error>') 반환."""
    truncated = content[:CONTENT_TRUNCATE]
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": CANON_SCORE_SYSTEM},
            {
                "role": "user",
                "content": CANON_SCORE_USER_TEMPLATE.format(content=truncated),
            },
        ],
        "max_tokens": 200,
        "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "CanonScore",
                "schema": CANON_SCORE_SCHEMA,
                "strict": True,
            },
        },
    }
    # error 본 caller 본 batch level 본 catch (★ score sentinel 노이즈
    # 방지 — anti-pattern hardcoded_score 회피)
    async with semaphore:
        resp = await client.post(
            f"{endpoint}/v1/chat/completions",
            json=payload,
            timeout=30.0,
        )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    if text is None:
        raise RuntimeError("empty content (reasoning_content runaway?)")
    parsed = json.loads(text)
    score = float(parsed["canon_score"])
    reason = str(parsed.get("reason", ""))[:200]
    return (max(0.0, min(1.0, score)), reason)


def _load_cache() -> dict[str, dict[str, Any]]:
    if SCORE_CACHE_PATH.exists():
        try:
            data = json.loads(SCORE_CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                # mypy 본 dict[Any, Any] 본 narrow X — explicit cast.
                return {str(k): v for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            print(f"  (cache invalid, resetting) {SCORE_CACHE_PATH}")
    return {}


def _save_cache(cache: dict[str, dict[str, Any]]) -> None:
    SCORE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )


async def _score_all_llm(
    posts: list[Path],
    *,
    endpoint: str,
    model: str,
    concurrency: int,
    cache: dict[str, dict[str, Any]],
    flush_every: int = 200,
) -> dict[str, dict[str, Any]]:
    pending = [p for p in posts if p.name not in cache]
    print(
        f"LLM score: total={len(posts)} cached={len(posts) - len(pending)} "
        f"pending={len(pending)} concurrency={concurrency}"
    )
    if not pending:
        return cache
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient() as client:
        async def _job(p: Path) -> tuple[str, float, str]:
            text = p.read_text(encoding="utf-8")
            score, reason = await _score_one_llm(
                client, endpoint, model, text, semaphore
            )
            return (p.name, score, reason)

        tasks = {asyncio.create_task(_job(p)): p.name for p in pending}
        completed = 0
        errors = 0
        for fut in asyncio.as_completed(tasks.keys()):
            try:
                name, score, reason = await fut
                cache[name] = {"score": score, "reason": reason}
            except Exception as e:  # noqa: BLE001
                # error 본 cache 본 score 본 X 본 entry 본 — 재실행 시 retry.
                # reason 본 본인 diagnostics. anti-pattern hardcoded_score
                # 회피 — 0.0 본 의도 본 reject 와 구분.
                errors += 1
                if errors <= 5:
                    print(f"  (skip) {type(e).__name__}: {e}")
            completed += 1
            if completed % flush_every == 0:
                _save_cache(cache)
                print(
                    f"  scored {completed}/{len(pending)} "
                    f"(cache saved, errors={errors})"
                )
        _save_cache(cache)
        print(
            f"  scored {completed}/{len(pending)} "
            f"(final cache saved, errors={errors})"
        )
    return cache


def _post_passes(
    text: str,
    name: str,
    mode: str,
    keyword_threshold: int,
    llm_scores: dict[str, dict[str, Any]] | None,
    llm_threshold: float,
) -> tuple[bool, int, float | None]:
    """retain 결정. (passes, kw_hits, llm_score|None) 반환.

    llm_score 본 None 본 LLM 미평가 (★ cache 없음 / parse 실패 / 범위 X).
    hardcoded score (★ 0.0) 본 사용 X — 'no judgment' vs 'judgment=0.0'
    구분 명시.
    """
    kw_hits = _score_keyword(text)
    llm_score: float | None = None
    if llm_scores is not None and name in llm_scores:
        raw = llm_scores[name].get("score")
        if isinstance(raw, (int, float)) and 0.0 <= float(raw) <= 1.0:
            llm_score = float(raw)

    kw_pass = kw_hits >= keyword_threshold
    llm_pass = llm_score is not None and llm_score >= llm_threshold

    if mode == "keyword":
        return (kw_pass, kw_hits, llm_score)
    if mode == "llm":
        # LLM 미평가 본 reject (★ 명시적 — 0.0 silent coerce X).
        return (llm_pass, kw_hits, llm_score)
    if mode == "union":
        return (kw_pass or llm_pass, kw_hits, llm_score)
    if mode == "intersect":
        return (kw_pass and llm_pass, kw_hits, llm_score)
    raise ValueError(f"unknown filter mode: {mode}")


def prepare_dc_posts(
    *,
    mode: str,
    keyword_threshold: int,
    llm_scores: dict[str, dict[str, Any]] | None,
    llm_threshold: float,
    dump_excluded_sample: bool,
) -> tuple[int, int, int]:
    """DC posts 본 mode 본 retain + chunk.

    Returns:
        (batches, total_posts, kept_posts)
    """
    if not DC_POSTS_SRC.exists():
        print(f"  (skip) {DC_POSTS_SRC} not found")
        return (0, 0, 0)
    posts = sorted(DC_POSTS_SRC.glob("*.md"), key=lambda p: int(p.stem))
    if not posts:
        print("  (skip) no DC posts")
        return (0, 0, 0)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for old in UPLOAD_DIR.glob("dc_posts_*.md"):
        old.unlink()
    if EXCLUDED_SAMPLE_PATH.exists():
        EXCLUDED_SAMPLE_PATH.unlink()

    print(
        f"dc: {len(posts)} posts (mode={mode} kw>={keyword_threshold} "
        f"llm>={llm_threshold:.2f})"
    )
    batch: list[str] = []
    batch_idx = 1
    cur_bytes = 0
    saved = 0
    kept = 0
    excluded_samples: list[str] = []
    excluded_total = 0

    def out_path(idx: int) -> Path:
        return UPLOAD_DIR / f"dc_posts_{idx:04d}.md"

    header = (
        f"# DC Gallery 'belheraaaaaaaaaaaaaa' canon posts\n\n"
        f"본 file 은 dcinside mgallery `belheraaaaaaaaaaaaaa` crawl 의 "
        f"filter mode `{mode}` (kw>={keyword_threshold}, "
        f"llm>={llm_threshold:.2f}) post 만 통과한 audit 자료.\n\n"
    )
    for post in posts:
        text = post.read_text(encoding="utf-8")
        passes, kw_hits, llm_score = _post_passes(
            text,
            post.name,
            mode,
            keyword_threshold,
            llm_scores,
            llm_threshold,
        )
        if not passes:
            excluded_total += 1
            if dump_excluded_sample and len(excluded_samples) < 30:
                reason = ""
                if llm_scores and post.name in llm_scores:
                    reason = str(llm_scores[post.name].get("reason", ""))[:160]
                llm_repr = (
                    f"{llm_score:.2f}" if llm_score is not None else "n/a"
                )
                excluded_samples.append(
                    f"\n---\n\n## {post.name} "
                    f"(kw={kw_hits}, llm={llm_repr})\n\n"
                    f"reason: {reason}\n\n{text}\n"
                )
            continue
        kept += 1
        content = f"\n---\n\n{text}\n"
        post_bytes = len(content.encode("utf-8"))
        if cur_bytes + post_bytes > MAX_BYTES and batch:
            _flush(out_path(batch_idx), header, batch)
            saved += 1
            batch = []
            cur_bytes = 0
            batch_idx += 1
        batch.append(content)
        cur_bytes += post_bytes
    if batch:
        _flush(out_path(batch_idx), header, batch)
        saved += 1

    if dump_excluded_sample and excluded_samples:
        EXCLUDED_SAMPLE_PATH.write_text(
            f"# Excluded DC posts (sample, mode={mode})\n\n"
            f"총 미포함 {excluded_total} 본 첫 {len(excluded_samples)} sample.\n"
            + "".join(excluded_samples),
            encoding="utf-8",
        )
        print(
            f"  excluded sample → {EXCLUDED_SAMPLE_PATH.name} "
            f"({len(excluded_samples)}/{excluded_total})"
        )

    retain = 100.0 * kept / max(1, len(posts))
    print(
        f"dc: {saved} batches, {kept}/{len(posts)} kept "
        f"({retain:.1f}%)"
    )
    return (saved, len(posts), kept)


def verify_sizes() -> int:
    print()
    print("=== upload_ready size check ===")
    over = 0
    for p in sorted(UPLOAD_DIR.rglob("*")):
        if not p.is_file():
            continue
        size_mb = p.stat().st_size / 1024 / 1024
        flag = " ⚠ OVER 30MB" if size_mb > 30 else ""
        print(f"  {p.relative_to(UPLOAD_DIR)}: {size_mb:.2f} MB{flag}")
        if size_mb > 30:
            over += 1
    return over


def main() -> int:
    parser = argparse.ArgumentParser(description="Canon upload prep")
    parser.add_argument(
        "--dc-filter-mode",
        choices=["keyword", "llm", "union", "intersect"],
        default="keyword",
        help="DC retain 모드 (★ default=keyword)",
    )
    parser.add_argument(
        "--dc-keyword-threshold",
        type=int,
        default=2,
        help="keyword hit 최소 (★ default 2)",
    )
    parser.add_argument(
        "--llm-score-threshold",
        type=float,
        default=0.5,
        help="LLM canon_score 최소 (★ default 0.5)",
    )
    parser.add_argument(
        "--llm-endpoint",
        default="http://localhost:8083",
        help="9B llama-server endpoint",
    )
    parser.add_argument(
        "--llm-model",
        default="qwen35-9b-q3",
        help="model name in request",
    )
    parser.add_argument(
        "--llm-concurrency",
        type=int,
        default=16,
        help="async concurrency (★ 9B server load 고려)",
    )
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="LLM 점수만 cache 에 갱신하고 chunk 산출 X",
    )
    parser.add_argument(
        "--dump-excluded-sample",
        action="store_true",
        help="미포함 sample 30개 본인 review 용 dump",
    )
    parser.add_argument(
        "--skip-episodes", action="store_true", help="episode chunking 건너뜀"
    )
    parser.add_argument(
        "--skip-namuwiki", action="store_true", help="namuwiki chunking 건너뜀"
    )
    parser.add_argument(
        "--skip-dc", action="store_true", help="DC chunking 건너뜀"
    )
    args = parser.parse_args()

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    llm_scores: dict[str, dict[str, Any]] | None = None
    needs_llm = (
        args.dc_filter_mode in ("llm", "union", "intersect")
        or args.score_only
    )

    if needs_llm and not args.skip_dc:
        if not DC_POSTS_SRC.exists():
            print(f"  (no DC source: {DC_POSTS_SRC})")
        else:
            posts = sorted(
                DC_POSTS_SRC.glob("*.md"), key=lambda p: int(p.stem)
            )
            cache = _load_cache()
            llm_scores = asyncio.run(
                _score_all_llm(
                    posts,
                    endpoint=args.llm_endpoint,
                    model=args.llm_model,
                    concurrency=args.llm_concurrency,
                    cache=cache,
                )
            )

    if args.score_only:
        print("\n--score-only → chunk 산출 건너뜀")
        return 0

    if not args.skip_episodes:
        prepare_episodes()
    if not args.skip_namuwiki:
        prepare_namuwiki()
    if not args.skip_dc:
        prepare_dc_posts(
            mode=args.dc_filter_mode,
            keyword_threshold=args.dc_keyword_threshold,
            llm_scores=llm_scores,
            llm_threshold=args.llm_score_threshold,
            dump_excluded_sample=args.dump_excluded_sample,
        )

    over = verify_sizes()
    if over:
        print(f"\n❌ {over} files > 30MB — manual split needed")
        return 1
    print("\n✓ all files within 30MB budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
