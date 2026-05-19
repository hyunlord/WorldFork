"""Phase C — namuwiki_001.md 본 162 page 별 file 분리.

★ wiki canon filter (canon_audit_wiki_filter.py) 의 입력.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def split_namuwiki(source: Path, output_dir: Path) -> list[Path]:
    """namuwiki 본 page 별 분리."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*.md"):
        old.unlink()

    text = source.read_text(encoding="utf-8")
    # ^# 를 separator 로 split. 본 첫 chunk 본 file header 본 skip.
    raw_pages = re.split(r"\n(?=^# )", text, flags=re.MULTILINE)

    written: list[Path] = []
    skip_titles = {"Namuwiki canon 자료"}

    for idx, page in enumerate(raw_pages):
        first_line = page.split("\n", 1)[0].strip()
        if not first_line.startswith("# "):
            continue
        title = first_line[2:].strip()
        if title in skip_titles:
            continue
        # filename sanitize — 한글 + 영문 + 숫자 + dash + underscore
        safe = re.sub(r"[^\w가-힣\-]+", "_", title)[:80].strip("_")
        if not safe:
            safe = f"page_{idx}"
        out_path = output_dir / f"{idx:03d}_{safe}.md"
        out_path.write_text(page, encoding="utf-8")
        written.append(out_path)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Split namuwiki upload chunk")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(".local/canon/upload_ready/namuwiki_001.md"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".local/canon/audit_wiki_pages"),
    )
    args = parser.parse_args()

    pages = split_namuwiki(args.source, args.output_dir)
    print(f"split {len(pages)} pages → {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
