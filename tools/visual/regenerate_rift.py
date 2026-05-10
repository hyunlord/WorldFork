"""균열 재생성 (★ vision 검수 X 발견 시).

본 commit (★ Phase 5, vision 검수 직접 답):
- 핏빛성채: prompt 보강 (★ Necronomicon + 여신 weeping 명시)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from .character_base import OUTPUT_DIR, detect_comfyui_output_dir
from .rifts import (
    RIFTS,
    generate_rift,
)

# 재생성 대상 (★ vision 검수 X)
REGENERATE_TARGETS: list[dict[str, Any]] = [
    {"name": "핏빛성채", "seed": 11050},
]


def main() -> int:
    print("=" * 80)
    print("Phase 5 — 균열 재생성 (★ vision 검수 X)")
    print("=" * 80)

    comfyui_output = detect_comfyui_output_dir()
    if comfyui_output is None:
        print("[ERROR] ComfyUI output dir 미진단")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    regenerated: list[Path] = []

    for target in REGENERATE_TARGETS:
        name = str(target["name"])
        data = RIFTS[name]
        seed = int(target["seed"])

        # 기존 파일 .v1.png 백업
        existing = OUTPUT_DIR / f"rift_{name}.png"
        if existing.exists():
            backup = existing.with_suffix(".v1.png")
            existing.rename(backup)
            print(f"  기존 → {backup.name}")

        result = generate_rift(name, data, seed, comfyui_output)
        if result:
            regenerated.append(result)

    elapsed = time.monotonic() - start

    print("\n=== 결과 ===")
    print(f"재생성: {len(regenerated)}/{len(REGENERATE_TARGETS)}")
    print(f"시간: {elapsed:.1f}s ({elapsed / 60:.1f}분)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
