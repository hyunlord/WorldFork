"""Phase C — 본문 740 episode 본 8 chunk → 본 episode 별 file.

★ wiki splitter 와 동일 패턴 (★ canon_audit_split_wiki.py).
★ extract_episodes.py 의 입력.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

EP_HEADER_RE = re.compile(r"^## Episode (\d{4})", re.MULTILINE)


def split_episodes(source_dir: Path, output_dir: Path) -> int:
    """본 chunk 본 read + episode 별 file 산출."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("ep_*.md"):
        old.unlink()

    count = 0
    chunks = sorted(source_dir.glob("episodes_*.md"))
    if not chunks:
        return 0

    for chunk_file in chunks:
        text = chunk_file.read_text(encoding="utf-8")
        positions = [
            (m.start(), m.group(1)) for m in EP_HEADER_RE.finditer(text)
        ]
        # sentinel for last episode's end
        positions.append((len(text), None))

        for i in range(len(positions) - 1):
            start, ep_num = positions[i]
            end = positions[i + 1][0]
            ep_text = text[start:end].rstrip() + "\n"
            out_path = output_dir / f"ep_{ep_num}.md"
            out_path.write_text(ep_text, encoding="utf-8")
            count += 1

    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Split episode chunks")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(".local/canon/upload_ready/episodes"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".local/canon/audit_episodes"),
    )
    args = parser.parse_args()

    count = split_episodes(args.source_dir, args.output_dir)
    print(f"split {count} episodes → {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
