"""비요른 LoRA dataset 준비 (★ Phase 5).

본 commit (★ ai-toolkit Flux LoRA):
- Phase 1 v2 비요른 9장 → ai-toolkit dataset 본격
- 자료 이미 1024×1024 (★ resize X 본격)
- 캡션 자동 생성 (★ trigger word + pose hint)

작품 본문 정합:
- trigger word: bjorn_warrior
- 본문 비요른 = barbarian warrior, dark hair, blue eyes
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from .character_base import OUTPUT_DIR

SOURCE_DIR = OUTPUT_DIR
DATASET_DIR = SOURCE_DIR / "lora_dataset_bjorn"

TRIGGER_WORD = "bjorn_warrior"


def prepare_bjorn_dataset(
    source_dir: Path = SOURCE_DIR,
    output_dir: Path = DATASET_DIR,
) -> int:
    """비요른 자료 → LoRA dataset 본격."""
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(source_dir.glob("비요른_*.png"))
    # ★ .bak.png / .v1.png 제외
    sources = [
        s for s in sources if ".bak" not in s.name and ".v1" not in s.name
    ]

    print(f"비요른 자료: {len(sources)}장")

    for i, src in enumerate(sources):
        dst_img = output_dir / f"{i:03d}.png"
        dst_caption = output_dir / f"{i:03d}.txt"

        # 자료는 이미 1024×1024 — copy 본격 (★ Pillow X 회피)
        shutil.copy2(src, dst_img)

        # 캡션 (★ trigger word + pose 본격)
        # 파일명에서 pose 추출 (★ 비요른_NN_pose_slug.png)
        parts = src.stem.split("_", 2)
        if len(parts) >= 3:
            pose_hint = parts[2].replace("_", " ").strip()
        else:
            pose_hint = "portrait"

        caption = (
            f"{TRIGGER_WORD}, {pose_hint}, "
            f"barbarian warrior, dark hair, blue eyes, "
            f"fantasy concept art"
        )
        dst_caption.write_text(caption, encoding="utf-8")
        print(f"  {dst_img.name}: {caption[:70]}...")

    return len(sources)


def main() -> int:
    print("=" * 80)
    print("Phase 5 — 비요른 LoRA dataset 준비")
    print("=" * 80)

    count = prepare_bjorn_dataset()

    print("\n=== 결과 ===")
    print(f"dataset 자료: {count}장")
    print(f"위치: {DATASET_DIR}")
    print(f"trigger word: {TRIGGER_WORD}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
