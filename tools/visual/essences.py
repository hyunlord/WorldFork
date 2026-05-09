"""1층 9등급 정수 visual effect 5종 (★ Phase 3).

작품 본문 정합 (★ 13/14화 30분 자연 소멸):
- 갈색: 고블린 정수
- 흙색: 노움 정수 (★ 22화)
- 청록: 슬라임 정수
- 핏빛: 칼날늑대 정수 (★ 50/221화)
- 회청: 레이스 정수 (★ 60/17화)
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from .character_base import (
    OUTPUT_DIR,
    build_flux_workflow,
    detect_comfyui_output_dir,
    submit_workflow,
    wait_for_completion,
)

ESSENCES: dict[str, dict[str, str]] = {
    "갈색_정수": {
        "color": "warm brown",
        "source": "goblin",
        "details": (
            "warm earthy brown floating orb, swirling brown energy, "
            "semi-translucent"
        ),
    },
    "흙색_정수": {
        "color": "ochre dirt",
        "source": "gnome",
        "details": (
            "ochre dirt-colored floating orb, swirling earth-tone energy, "
            "dusty appearance"
        ),
    },
    "청록_정수": {
        "color": "teal cyan",
        "source": "slime",
        "details": (
            "vibrant teal-cyan floating orb, swirling viscous energy, "
            "watery iridescent glow"
        ),
    },
    "핏빛_정수": {
        "color": "blood crimson",
        "source": "bladewolf",
        "details": (
            "blood crimson floating orb, swirling violent energy, "
            "dark red glow"
        ),
    },
    "회청_정수": {
        "color": "grey-blue",
        "source": "wraith",
        "details": (
            "ghostly grey-blue floating orb, ethereal swirling energy, "
            "ethereal cold glow"
        ),
    },
}


def build_essence_prompt(
    name: str,
    data: dict[str, str],
    style: str = (
        "magical visual effect, particle effect, glowing energy, "
        "fantasy game asset, ethereal lighting, painterly"
    ),
) -> str:
    """정수 prompt 본격 (★ floating visual effect)."""
    return (
        f"floating magical essence orb, {data['details']}, "
        f"{data['source']} essence, dungeon ambient lighting, "
        f"natural dispersion, mystical aura, "
        f"{style}, masterpiece, best quality, 8k uhd, "
        f"centered composition"
    )


def generate_essence(
    name: str,
    data: dict[str, str],
    seed: int,
    comfyui_output: Path,
) -> Path | None:
    """단일 정수 본격 generation."""
    prompt = build_essence_prompt(name, data)
    print(f"[{name}] {data['color']}")

    try:
        workflow = build_flux_workflow(
            prompt=prompt, width=1024, height=1024, seed=seed,
        )
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
                dst = OUTPUT_DIR / f"essence_{name}.png"
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
    print("Phase 3 — 정수 5종 generation (★ 13/14화 본문 정합)")
    print("=" * 80)

    comfyui_output = detect_comfyui_output_dir()
    if comfyui_output is None:
        print("[ERROR] ComfyUI output dir 미진단")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    generated_paths: list[Path] = []

    for i, (name, data) in enumerate(ESSENCES.items()):
        seed = 9000 + i * 100
        result = generate_essence(name, data, seed, comfyui_output)
        if result:
            generated_paths.append(result)

    elapsed = time.monotonic() - start

    metadata: dict[str, Any] = {
        "phase": "Phase 3 essences",
        "essences": list(ESSENCES.keys()),
        "model": "FLUX.1-dev",
        "elapsed_seconds": round(elapsed, 1),
        "generated_files": [p.name for p in generated_paths],
    }
    metadata_path = OUTPUT_DIR / "phase3_essences_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== 결과 ===")
    print(f"정수: {len(generated_paths)}/5")
    print(f"시간: {elapsed:.1f}s ({elapsed / 60:.1f}분)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
