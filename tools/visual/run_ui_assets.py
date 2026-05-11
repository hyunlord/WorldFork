"""UI 자료 본격 queue runner (★ Phase 6 caller, MBNU X).

본격 사용:
    python -m tools.visual.run_ui_assets [screen_name]

screen_name 본격:
- main_screen (★ Phase 6a)
- gameplay_screen (★ Phase 6b)
- 후속 6c-g 본격 추가

screen_name 본격 X → ALL_ASSET_DICTS 본격 전체 queue.
"""

from __future__ import annotations

import sys
import time

from tools.visual.ui_assets import (
    ALL_ASSET_DICTS,
    generate_ui_asset,
    spec_from_dict,
)


def queue_screen(screen_name: str, base_seed: int = 60000) -> int:
    """단일 화면 자료 본격 queue (★ ComfyUI HTTP)."""
    if screen_name not in ALL_ASSET_DICTS:
        print(f"❌ 본격 X: {screen_name}")
        print(f"  본격 화면: {sorted(ALL_ASSET_DICTS)}")
        return 1

    assets = ALL_ASSET_DICTS[screen_name]
    print(f"=== {screen_name} ({len(assets)} 자료) ===")

    for i, (name, data) in enumerate(assets.items()):
        spec = spec_from_dict(name, data)
        seed = base_seed + i
        print(
            f"  [{i + 1}/{len(assets)}] {name} "
            f"({spec.width}x{spec.height}, LoRA={spec.lora})"
        )
        try:
            pid = generate_ui_asset(spec, seed=seed)
            print(f"    prompt_id: {pid}")
        except Exception as exc:  # noqa: BLE001
            print(f"    ❌ {exc}")
            return 1
        time.sleep(2)  # ★ queue 안전

    return 0


def main() -> int:
    if len(sys.argv) >= 2:
        return queue_screen(sys.argv[1])

    # 본격 전체 queue (★ Phase 6 모든 화면)
    print(f"=== 전체 queue ({len(ALL_ASSET_DICTS)} 화면) ===")
    for i, screen_name in enumerate(ALL_ASSET_DICTS):
        base_seed = 60000 + i * 100
        rc = queue_screen(screen_name, base_seed=base_seed)
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
