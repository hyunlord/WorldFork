"""Claude.ai project knowledge 업로드용 정리.

Phase 9.19-a (초안) — namuwiki + DC posts 본 28MB 안전 margin 본 chunking.
Phase C (확장) — episode 흡수 (★ build_episode_batches.py 통합) + DC
CANON_KEYWORDS first-pass filter (★ 13,684 post 본 canon 정합 keyword 본
hit 본 post 만 통과).

사용:
  python scripts/prepare_canon_upload.py
  python scripts/prepare_canon_upload.py --dc-keyword-threshold 2 --skip-namuwiki

Phase C audit (★ canon_facts.json LLM extraction) 본 후속 commit 본 분리.
"""

from __future__ import annotations

import argparse
from pathlib import Path

MAX_BYTES = 28 * 1024 * 1024  # 28MB safety margin (★ Claude.ai 30MB cap)
EPISODE_BATCH_SIZE = 100

CANON_DIR = Path(".local/canon")
EP_SRC = CANON_DIR / "episodes"
NAMU_SRC = CANON_DIR / "namuwiki"
DC_POSTS_SRC = CANON_DIR / "dc" / "posts"
UPLOAD_DIR = CANON_DIR / "upload_ready"
EP_DST = UPLOAD_DIR / "episodes"

# DC post 본 canon 정합 keyword (★ first-pass filter).
# 한 post 본 KEYWORD set hit count >= --dc-keyword-threshold 시 통과.
# 본 list 본 본인 manual review 후 추가/조정 가능.
CANON_KEYWORDS: frozenset[str] = frozenset(
    {
        # ★ 주요 character
        "비요른",
        "에르웬",
        "한스",
        "에쉬드",
        "셰인",
        "아이나르",
        "미샤",
        "카나바로",
        # ★ 본문 mechanism
        "정수",
        "마석",
        "균열",
        "등급",
        "탐험가",
        "수호자",
        "계층군주",
        "수정동굴",
        # ★ 위치 / 던전
        "라프도니아",
        "라스카니아",
        "노아르크",
        "도서관",
        "라비기온",
        "파르시티에브",
        "핏빛성채",
        "빙하굴",
        "강철의 묘",
        "녹색탄광",
        "망자의 땅",
        # ★ 종족 / 직업
        "드워프",
        "오크",
        "고블린",
        "약탈자",
        # ★ 본문 작품명 (★ 적은 hit, 보조)
        "겜바바",
        "바바리안",
    }
)


def _score_keyword(text: str) -> int:
    """본 text 본 CANON_KEYWORDS hit unique count."""
    return sum(1 for kw in CANON_KEYWORDS if kw in text)


def _flush(out: Path, header: str, chunks: list[str]) -> None:
    text = header + "".join(chunks)
    out.write_text(text, encoding="utf-8")
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"  {out.name}: {size_mb:.2f} MB ({len(chunks)} entries)")


def prepare_episodes() -> int:
    """본문 740 episode 본 100ep batch 본 chunked .md 출력."""
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
    """나무위키 153 page 본 chunk 본 size 본 packed."""
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


def prepare_dc_posts(keyword_threshold: int) -> tuple[int, int, int]:
    """DC posts 본 CANON_KEYWORDS first-pass filter + chunk.

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

    print(f"dc: {len(posts)} posts (★ threshold={keyword_threshold})")
    batch: list[str] = []
    batch_idx = 1
    cur_bytes = 0
    saved = 0
    kept = 0

    def out_path(idx: int) -> Path:
        return UPLOAD_DIR / f"dc_posts_{idx:04d}.md"

    header = (
        f"# DC Gallery 'belheraaaaaaaaaaaaaa' canon posts\n\n"
        f"본 file 은 dcinside mgallery `belheraaaaaaaaaaaaaa` crawl 의 "
        f"CANON_KEYWORDS hit count >= {keyword_threshold} post 만 통과한 "
        f"audit 자료.\n\n"
    )

    for post in posts:
        text = post.read_text(encoding="utf-8")
        if _score_keyword(text) < keyword_threshold:
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
        "--dc-keyword-threshold",
        type=int,
        default=2,
        help="DC post 본 canon keyword hit 최소 (★ 기본 2, 0 비활성)",
    )
    parser.add_argument(
        "--skip-episodes",
        action="store_true",
        help="episode chunking 건너뜀",
    )
    parser.add_argument(
        "--skip-namuwiki",
        action="store_true",
        help="namuwiki chunking 건너뜀",
    )
    parser.add_argument(
        "--skip-dc",
        action="store_true",
        help="DC chunking 건너뜀",
    )
    args = parser.parse_args()

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_episodes:
        prepare_episodes()
    if not args.skip_namuwiki:
        prepare_namuwiki()
    if not args.skip_dc:
        prepare_dc_posts(args.dc_keyword_threshold)

    over = verify_sizes()
    if over:
        print(f"\n❌ {over} files > 30MB — manual split needed")
        return 1
    print("\n✓ all files within 30MB budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
