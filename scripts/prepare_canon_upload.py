"""Claude.ai project knowledge 업로드용 정리.

본 commit (Phase 9.19-a):
- .local/canon/namuwiki/*.md → upload_ready/namuwiki_*.md (★ 30MB 미만 chunking)
- .local/canon/dc/posts/*.md → upload_ready/dc_posts_NNNN.md
  (★ 100 post 본격 통합 본격)
- size check (★ 30MB 본격 본격 본격 fail)

사용:
  python scripts/prepare_canon_upload.py
"""

from __future__ import annotations

from pathlib import Path

MAX_BYTES = 28 * 1024 * 1024  # 28MB safety margin (★ 30MB limit)

CANON_DIR = Path(".local/canon")
NAMU_SRC = CANON_DIR / "namuwiki"
DC_POSTS_SRC = CANON_DIR / "dc" / "posts"
UPLOAD_DIR = CANON_DIR / "upload_ready"


def _flush(out: Path, header: str, chunks: list[str]) -> None:
    text = header + "".join(chunks)
    out.write_text(text, encoding="utf-8")
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"  {out.name}: {size_mb:.2f} MB ({len(chunks)} entries)")


def prepare_namuwiki() -> int:
    if not NAMU_SRC.exists():
        print(f"  (skip) {NAMU_SRC} not found")
        return 0

    pages = sorted(NAMU_SRC.glob("*.md"))
    if not pages:
        print("  (skip) no namuwiki pages")
        return 0

    # Clear old
    for old in UPLOAD_DIR.glob("namuwiki_*.md"):
        old.unlink()

    print(f"namuwiki: {len(pages)} pages")
    batch: list[str] = []
    batch_idx = 1
    cur_bytes = 0

    def out_path(idx: int) -> Path:
        return UPLOAD_DIR / f"namuwiki_{idx:03d}.md"

    header = (
        "# Namuwiki 본격 본격 본격\n\n"
        "본 file 본격 namuwiki crawl 본격 본격 본격 본격 "
        "(★ 게임 속 바바리안으로 살아남기 + 직접 link). "
        "audit + 본격 본격 본격 본격.\n\n"
    )

    saved = 0
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


def prepare_dc_posts() -> int:
    if not DC_POSTS_SRC.exists():
        print(f"  (skip) {DC_POSTS_SRC} not found")
        return 0

    posts = sorted(
        DC_POSTS_SRC.glob("*.md"), key=lambda p: int(p.stem)
    )
    if not posts:
        print("  (skip) no DC posts")
        return 0

    # Clear old
    for old in UPLOAD_DIR.glob("dc_posts_*.md"):
        old.unlink()

    print(f"dc: {len(posts)} posts")
    batch: list[str] = []
    batch_idx = 1
    cur_bytes = 0

    def out_path(idx: int) -> Path:
        return UPLOAD_DIR / f"dc_posts_{idx:04d}.md"

    header = (
        "# DC Gallery '게임속바바리안' 본격 본격 본격\n\n"
        "본 file 본격 dcinside mgallery `belheraaaaaaaaaaaaaa` "
        "crawl 본격 본격. audit + community insight 본격.\n\n"
    )

    saved = 0
    for post in posts:
        content = f"\n---\n\n{post.read_text(encoding='utf-8')}\n"
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

    print(f"dc: {saved} batches")
    return saved


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
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    prepare_namuwiki()
    prepare_dc_posts()
    over = verify_sizes()
    if over:
        print(f"\n❌ {over} files > 30MB — manual split needed")
        return 1
    print("\n✓ all files within 30MB budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
