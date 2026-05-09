"""1층 sub_areas 6개 environment generation (★ Phase 2 B).

작품 본문 정합 (★ 어둠 미궁 1층):
- 진입점: 안전 구역, 가시거리 10m, 어둠
- 북쪽 통로: 약한 몬스터 영역
- 남쪽 통로: 노움 서식 (★ 22화)
- 수정 동굴: 정수 풍부 (★ 109/151/478화)
- 비석 공동: 공물 비석 (★ 374화)
- 포탈 영역: 균열 4종 입구
  (★ 핏빛성채/빙하굴/녹색탄광/강철의 묘)
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

from .character_base import (
    OUTPUT_DIR,
    build_flux_workflow,
    detect_comfyui_output_dir,
    submit_workflow,
    wait_for_completion,
)

# 6 sub_areas 본격 본문 정합
SUB_AREAS: dict[str, dict[str, str]] = {
    "진입점": {
        "english": "dungeon entrance",
        "atmosphere": (
            "first floor entry chamber, dim torch light, stone walls"
        ),
        "details": (
            "ancient stone archway, faint torch glow, "
            "mysterious darkness ahead, 10 meter visibility"
        ),
        "mood": "ominous yet welcoming, threshold between safety and danger",
    },
    "북쪽_통로": {
        "english": "northern passage",
        "atmosphere": "dark winding corridor, narrow rough-hewn walls",
        "details": (
            "twisting tunnel, scattered bones, claw marks on walls, "
            "distant echoes"
        ),
        "mood": "tense, danger lurking, monster territory",
    },
    "남쪽_통로": {
        "english": "southern passage",
        "atmosphere": "earthen corridor with mounds, gnome territory",
        "details": (
            "small earth mounds, dirt piles, gnome holes, scattered tools"
        ),
        "mood": "rustic dangerous, gnome warren feeling",
    },
    "수정_동굴": {
        "english": "crystal cavern",
        "atmosphere": (
            "vast crystal chamber, glowing crystals, ethereal light"
        ),
        "details": (
            "luminous crystals embedded in walls, floating essences in air, "
            "multicolored glow, vast cavernous space"
        ),
        "mood": "magical wondrous, sanctuary of essences",
    },
    "비석_공동": {
        "english": "stele hollow",
        "atmosphere": "circular stone chamber with offering stele",
        "details": (
            "ancient stone monument in center, stone tablets, "
            "ritual circle, dim sacred atmosphere"
        ),
        "mood": "sacred ritualistic, threshold to something greater",
    },
    "포탈_영역": {
        "english": "portal zone",
        "atmosphere": (
            "convergence point of four rifts, swirling energies"
        ),
        "details": (
            "four shimmering portals "
            "(blood crimson, ice blue, toxic green, steel grey), "
            "reality distortion, energy crackling"
        ),
        "mood": "powerful liminal, gateway to deeper realms",
    },
}


def build_sub_area_prompt(
    name: str,
    data: dict[str, str],
    style: str = (
        "fantasy concept art, environment art, painterly digital art, "
        "atmospheric, cinematic lighting, detailed"
    ),
) -> str:
    """sub_area environment prompt 본격 (★ no characters)."""
    return (
        f"{data['english']}, {data['atmosphere']}, "
        f"{data['details']}, {data['mood']}, "
        f"first floor of dark dungeon, no characters, "
        f"{style}, masterpiece, best quality, 8k uhd, wide view"
    )


def generate_sub_area(
    name: str,
    data: dict[str, str],
    seed: int,
    comfyui_output: Path,
    width: int = 1536,
    height: int = 1024,
) -> Path | None:
    """단일 sub_area 본격 generation (★ wide aspect 본격)."""
    prompt = build_sub_area_prompt(name, data)
    print(f"[{name}] {data['english']}")
    print(f"  prompt: {prompt[:100]}...")

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
                dst = OUTPUT_DIR / f"sub_area_{name}.png"
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
    print("Phase 2 B — sub_areas 6개 environment 본격 (★ 1층 어둠 미궁)")
    print("=" * 80)

    comfyui_output = detect_comfyui_output_dir()
    if comfyui_output is None:
        print("[ERROR] ComfyUI output dir 미진단")
        return 1

    print(f"[OK] ComfyUI output: {comfyui_output}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    generated_paths: list[Path] = []

    for i, (name, data) in enumerate(SUB_AREAS.items()):
        seed = 5000 + i * 100
        result = generate_sub_area(name, data, seed, comfyui_output)
        if result:
            generated_paths.append(result)

    elapsed = time.monotonic() - start

    metadata = {
        "phase": "Phase 2 sub_areas",
        "sub_areas": list(SUB_AREAS.keys()),
        "model": "FLUX.1-dev",
        "elapsed_seconds": round(elapsed, 1),
        "generated_files": [p.name for p in generated_paths],
    }
    metadata_path = OUTPUT_DIR / "phase2_subareas_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== 결과 ===")
    print(f"sub_areas: {len(generated_paths)}/6")
    print(f"시간: {elapsed:.1f}s ({elapsed / 60:.1f}분)")
    print(f"metadata: {metadata_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
