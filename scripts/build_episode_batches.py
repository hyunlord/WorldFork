"""Build 100-episode .md batches for Claude.ai project knowledge upload.

본 commit (Phase 9.19-a):
- .local/canon/episodes/episode_*.txt → .local/canon/upload_ready/episodes/episodes_NNNN-NNNN.md
- 각 batch 100 episodes, Claude.ai 30MB 미만 정합
- markdown header per episode (★ navigation 본격)

사용:
  python scripts/build_episode_batches.py
"""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    src = Path(".local/canon/episodes")
    dst = Path(".local/canon/upload_ready/episodes")
    dst.mkdir(parents=True, exist_ok=True)

    eps = sorted(src.glob("episode_*.txt"))
    if not eps:
        print(f"❌ No episodes found in {src}")
        return 1

    print(f"total {len(eps)} episodes")

    # Clear existing batches (★ idempotent)
    for old in dst.glob("episodes_*.md"):
        old.unlink()

    batch_size = 100
    for batch_idx in range(0, len(eps), batch_size):
        batch = eps[batch_idx : batch_idx + batch_size]
        start_num = batch_idx + 1
        end_num = batch_idx + len(batch)
        out_path = dst / f"episodes_{start_num:04d}-{end_num:04d}.md"

        with out_path.open("w", encoding="utf-8") as fo:
            fo.write(f"# Episodes {start_num}-{end_num}\n\n")
            fo.write(
                "본 file 본격 본인 manual upload 본격 Claude.ai project "
                "knowledge 본격 본격 본격. audit + 본격 본격 본격 본격.\n\n"
            )
            for ep_path in batch:
                ep_num = ep_path.stem.split("_")[1]
                content = ep_path.read_text(encoding="utf-8")
                fo.write(f"\n## Episode {ep_num}\n\n")
                fo.write(content)
                if not content.endswith("\n"):
                    fo.write("\n")
                fo.write("\n---\n")

        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  {out_path.name}: {size_mb:.2f} MB ({len(batch)} eps)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
