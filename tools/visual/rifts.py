"""1층 균열 4종 generation (★ Phase 4).

작품 본문 정합 (1층 균열, 27화 본격):
- 핏빛성채: 8등급 보스 + 네크로노미콘 + 여신의 눈물
- 빙하굴: 8등급 보스 (★ 102화 6시간 1챕터)
- 녹색탄광: 8등급 보스
- 강철의_묘: 8등급 보스

각 균열은 1층 sub_area 포탈_영역에서 진입.
보스 정수 드롭률 33% (수호자).
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

# 4 균열 본문 정합
RIFTS: dict[str, dict[str, str]] = {
    "핏빛성채": {
        "english": "blood crimson rift fortress",
        "atmosphere": (
            "crimson stone fortress interior, bloody ritual chamber, "
            "dark gothic architecture"
        ),
        "details": (
            "imposing crimson stone walls, ritual circles in blood, "
            "ominous goddess statue weeping crimson tears, "
            "ancient grimoire (Necronomicon) on altar, "
            "8th grade boss lair, blood-soaked floor, dim red torches"
        ),
        "mood": "horrifying sacred, dread sanctum",
        "color_theme": "deep crimson, dark red, black shadows",
    },
    "빙하굴": {
        "english": "ice glacier cave",
        "atmosphere": (
            "frozen crystalline cave, ice walls, freezing mist"
        ),
        "details": (
            "massive ice pillars, frozen waterfalls, ice crystals everywhere, "
            "frozen tomb, ancient frost guardian remains, "
            "8th grade boss lair, glittering ice formations, "
            "deep cave system stretching into darkness"
        ),
        "mood": "frigid mysterious, ancient frozen majesty",
        "color_theme": "ice blue, white frost, deep teal shadows",
    },
    "녹색탄광": {
        "english": "toxic green mine",
        "atmosphere": (
            "abandoned mineshaft with toxic green fumes, mining tunnel system"
        ),
        "details": (
            "rusted mining equipment, broken support beams, "
            "glowing toxic green crystals embedded in walls, "
            "noxious mist seeping from cracks, mine carts on rails, "
            "8th grade boss lair, eerie green fungal growth, "
            "abandoned for ages"
        ),
        "mood": "toxic decay, abandoned dread",
        "color_theme": "sickly green, rust brown, black shadows",
    },
    "강철의_묘": {
        "english": "steel tomb mausoleum",
        "atmosphere": (
            "metal sarcophagus chamber, industrial gothic crypt"
        ),
        "details": (
            "heavy steel sarcophagi lined in rows, riveted metal walls, "
            "ancient steel armor mounted on walls, "
            "rusted chains hanging from ceiling, "
            "8th grade boss lair, dim metallic sheen, "
            "machinery integrated with crypt"
        ),
        "mood": "industrial gothic, metallic dread",
        "color_theme": "steel grey, rust copper, deep iron black",
    },
}


def build_rift_prompt(
    name: str,
    data: dict[str, str],
    style: str = (
        "fantasy concept art, environment art, painterly digital art, "
        "atmospheric, cinematic lighting, detailed, dramatic"
    ),
) -> str:
    """균열 environment prompt (★ 8등급 보스 lair, no characters)."""
    return (
        f"{data['english']}, {data['atmosphere']}, "
        f"{data['details']}, {data['mood']}, "
        f"color palette: {data['color_theme']}, "
        f"interior of dimensional rift, no characters, "
        f"{style}, masterpiece, best quality, 8k uhd, wide view, ominous"
    )


def generate_rift(
    name: str,
    data: dict[str, str],
    seed: int,
    comfyui_output: Path,
    width: int = 1536,
    height: int = 1024,
) -> Path | None:
    """단일 균열 본격 generation."""
    prompt = build_rift_prompt(name, data)
    print(f"[{name}] {data['english']}")

    try:
        workflow = build_flux_workflow(
            prompt=prompt, width=width, height=height, seed=seed,
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
                dst = OUTPUT_DIR / f"rift_{name}.png"
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
    print("Phase 4 — 균열 4종 generation (★ 1층 보스 lair)")
    print("=" * 80)

    comfyui_output = detect_comfyui_output_dir()
    if comfyui_output is None:
        print("[ERROR] ComfyUI output dir 미진단")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    generated_paths: list[Path] = []

    for i, (name, data) in enumerate(RIFTS.items()):
        seed = 11000 + i * 100
        result = generate_rift(name, data, seed, comfyui_output)
        if result:
            generated_paths.append(result)

    elapsed = time.monotonic() - start

    metadata: dict[str, Any] = {
        "phase": "Phase 4 rifts",
        "rifts": list(RIFTS.keys()),
        "model": "FLUX.1-dev",
        "elapsed_seconds": round(elapsed, 1),
        "generated_files": [p.name for p in generated_paths],
    }
    metadata_path = OUTPUT_DIR / "phase4_rifts_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== 결과 ===")
    print(f"균열: {len(generated_paths)}/4")
    print(f"시간: {elapsed:.1f}s ({elapsed / 60:.1f}분)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
