"""Phase 1 누락 자료 재생성 (★ Phase 2 A).

검수 finding (★ vision 검수):
- 비요른_00: pose 매칭 X (★ "unknown" slug, 본격 첫 prompt 매칭 실패)
- 에르웬_06: action stance pose timeout 누락
- 에르웬_07: walking pose timeout 누락

본 commit fix:
- timeout 300s 본격 (★ wait_for_completion fix)
- 기존 .bak.png 본격 안전
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from typing import Any

from .character_base import (
    CHARACTERS,
    OUTPUT_DIR,
    POSES,
    build_character_prompt,
    build_flux_workflow,
    detect_comfyui_output_dir,
    submit_workflow,
    wait_for_completion,
)

# 누락 자료 본격 명세 (★ vision 검수 본격)
MISSING_TARGETS: list[dict[str, Any]] = [
    # 비요른_00 본격 unknown (★ 첫 prompt pose 매칭 X)
    {"character": "비요른", "pose_idx": 0, "seed": 42},
    # 에르웬_06 (★ action stance, timeout)
    {"character": "에르웬", "pose_idx": 6, "seed": 1048},
    # 에르웬_07 (★ walking, timeout)
    {"character": "에르웬", "pose_idx": 7, "seed": 1049},
]


def regenerate_one(
    character: str,
    pose_idx: int,
    seed: int,
    comfyui_output: Path,
) -> Path | None:
    """단일 누락 자료 본격 재생성."""
    char_data = CHARACTERS[character]
    pose = POSES[pose_idx]
    prompt = build_character_prompt(char_data, pose=pose)

    print(f"[{character}_{pose_idx:02d}] {pose[:50]}...")

    try:
        workflow = build_flux_workflow(prompt=prompt, seed=seed)
        prompt_id = submit_workflow(workflow)
        result = wait_for_completion(prompt_id, timeout=300)
    except Exception as e:
        print(f"  ❌ {e}")
        return None

    outputs = result.get("outputs", {})
    for node_outputs in outputs.values():
        for img in node_outputs.get("images", []):
            subfolder = img.get("subfolder", "")
            if subfolder:
                src = comfyui_output / subfolder / img["filename"]
            else:
                src = comfyui_output / img["filename"]

            if src.exists():
                pose_slug = pose[:30].replace(" ", "_").replace(",", "")
                dst = (
                    OUTPUT_DIR
                    / f"{character}_{pose_idx:02d}_{pose_slug}.png"
                )

                # 기존 파일 .bak.png 백업 (★ 덮어쓰기 안전)
                if dst.exists():
                    backup = dst.with_suffix(".bak.png")
                    dst.rename(backup)
                    print(f"  기존 → {backup.name}")

                # 추가로 unknown.png 본격도 백업 본격 (★ 비요른_00)
                unknown_path = (
                    OUTPUT_DIR / f"{character}_{pose_idx:02d}_unknown.png"
                )
                if unknown_path.exists() and unknown_path != dst:
                    backup = unknown_path.with_suffix(".bak.png")
                    unknown_path.rename(backup)
                    print(f"  unknown → {backup.name}")

                try:
                    src.rename(dst)
                except OSError:
                    shutil.move(str(src), str(dst))

                print(f"  → {dst.name}")
                return dst

    print("  ⚠️ src 자료 X 발견")
    return None


def main() -> int:
    print("=" * 80)
    print("Phase 2 A — 누락 보강 (★ vision 검수 finding)")
    print("=" * 80)

    comfyui_output = detect_comfyui_output_dir()
    if comfyui_output is None:
        print("[ERROR] ComfyUI output dir 미진단")
        return 1

    print(f"[OK] ComfyUI output: {comfyui_output}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    regenerated: list[Path] = []

    for target in MISSING_TARGETS:
        result = regenerate_one(
            character=target["character"],
            pose_idx=target["pose_idx"],
            seed=target["seed"],
            comfyui_output=comfyui_output,
        )
        if result:
            regenerated.append(result)

    elapsed = time.monotonic() - start

    print("\n=== 결과 ===")
    print(f"재생성: {len(regenerated)}/{len(MISSING_TARGETS)}")
    print(f"시간: {elapsed:.1f}s ({elapsed / 60:.1f}분)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
