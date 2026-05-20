"""Phase C — DC 7,091 entry 본 별도 file 분리.

★ dc_posts_0001.md 본 entry separator: `\\n---\\n` + `# <title>` header.
★ post_no 본 entry 본 정확 id (★ filename + citation 본 사용).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

POST_NO_RE = re.compile(r"^post_no:\s*(\d+)", re.MULTILINE)


def split_dc(source: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("entry_*.md"):
        old.unlink()

    text = source.read_text(encoding="utf-8")
    raw_parts = text.split("\n---\n")
    # file header 본 skip — "# DC Gallery" 포함.
    entries = [p for p in raw_parts if p.strip().startswith("# ") and "DC Gallery" not in p[:60]]

    count = 0
    for entry in entries:
        m = POST_NO_RE.search(entry)
        if not m:
            continue
        post_no = int(m.group(1))
        out_path = output_dir / f"entry_{post_no:06d}.md"
        out_path.write_text(entry.strip() + "\n", encoding="utf-8")
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Split DC chunk")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(".local/canon/upload_ready/dc_posts_0001.md"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".local/canon/audit_dc_entries"),
    )
    args = parser.parse_args()

    count = split_dc(args.source, args.output_dir)
    print(f"split {count} DC entries → {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
