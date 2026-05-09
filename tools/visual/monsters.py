"""1층 9등급 몬스터 7종 generation (★ Phase 3).

작품 본문 정합 (1층 9등급 7종):
- 고블린: 일반, 전역
- 고블린_궁수: 원거리, 전역
- 노움: 22화 남쪽 통로 영역
- 슬라임: 청록색, 산성, 전역
- 칼날늑대: 50/221화, 빠름
- 레이스: 60/17화, 빛 약점
- 위치스램프: 지능형
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

MONSTERS: dict[str, dict[str, str]] = {
    "고블린": {
        "english": "goblin",
        "physical": (
            "small green-skinned humanoid, sharp teeth, pointed ears, "
            "hunched posture, tattered loincloth"
        ),
        "weapon": "crude rusty short sword, small wooden shield",
        "behavior": "aggressive feral expression, snarling",
    },
    "고블린_궁수": {
        "english": "goblin archer",
        "physical": (
            "small green-skinned humanoid, sharp teeth, pointed ears, "
            "leather armor"
        ),
        "weapon": "short bow drawn, quiver of arrows",
        "behavior": "alert focused expression, aiming",
    },
    "노움": {
        "english": "hostile gnome",
        "physical": (
            "small earthy humanoid, brown wrinkled skin, large ugly nose, "
            "dirty rough tunic, dirt-stained skin"
        ),
        "weapon": (
            "wielding crude sharpened pickaxe aggressively, threatening pose"
        ),
        "behavior": (
            "hostile snarling expression, malicious eyes, baring yellowed teeth, "
            "aggressive territorial stance, ready to attack"
        ),
    },
    "슬라임": {
        "english": "slime",
        "physical": (
            "translucent gelatinous blob, teal-green color, "
            "viscous oozing form, no fixed shape"
        ),
        "weapon": "acidic body, dripping corrosive ooze",
        "behavior": "shapeless oozing forward",
    },
    "칼날늑대": {
        "english": "bladewolf",
        "physical": (
            "large wolf with razor-sharp metallic blades along spine "
            "and legs, dark fur, glowing red eyes"
        ),
        "weapon": "blade-edged limbs, sharp claws",
        "behavior": "predatory pouncing stance, fangs bared",
    },
    "레이스": {
        "english": "wraith",
        "physical": (
            "ghostly translucent humanoid, tattered ethereal robes, "
            "hollow glowing eye sockets, shadow form"
        ),
        "weapon": "ethereal touch, shadow tendrils",
        "behavior": "floating menacing, drifting in darkness",
    },
    "위치스램프": {
        "english": "witchlamp",
        "physical": (
            "floating animated lantern, sickly green flame inside, "
            "ornate metal frame, wispy tendrils"
        ),
        "weapon": "deceptive lure light, shadow magic",
        "behavior": "intelligent malicious aura, flame flickering",
    },
}


def build_monster_prompt(
    name: str,
    data: dict[str, str],
    style: str = (
        "fantasy concept art, monster portrait, painterly digital art, "
        "detailed, dramatic lighting, dungeon background blurred"
    ),
) -> str:
    """몬스터 prompt 본격 (★ 9등급 본문 정합)."""
    return (
        f"{data['english']}, {data['physical']}, "
        f"{data['weapon']}, {data['behavior']}, "
        f"9th grade dungeon monster, dark dungeon background, "
        f"{style}, masterpiece, best quality, 8k uhd"
    )


def generate_monster(
    name: str,
    data: dict[str, str],
    seed: int,
    comfyui_output: Path,
    width: int = 1024,
    height: int = 1024,
) -> Path | None:
    """단일 몬스터 본격 generation."""
    prompt = build_monster_prompt(name, data)
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
                dst = OUTPUT_DIR / f"monster_{name}.png"
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
    print("Phase 3 — 몬스터 7종 generation (★ 9등급 본문 정합)")
    print("=" * 80)

    comfyui_output = detect_comfyui_output_dir()
    if comfyui_output is None:
        print("[ERROR] ComfyUI output dir 미진단")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    generated_paths: list[Path] = []

    for i, (name, data) in enumerate(MONSTERS.items()):
        seed = 7000 + i * 100
        result = generate_monster(name, data, seed, comfyui_output)
        if result:
            generated_paths.append(result)

    elapsed = time.monotonic() - start

    metadata: dict[str, Any] = {
        "phase": "Phase 3 monsters",
        "monsters": list(MONSTERS.keys()),
        "model": "FLUX.1-dev",
        "elapsed_seconds": round(elapsed, 1),
        "generated_files": [p.name for p in generated_paths],
    }
    metadata_path = OUTPUT_DIR / "phase3_monsters_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== 결과 ===")
    print(f"몬스터: {len(generated_paths)}/7")
    print(f"시간: {elapsed:.1f}s ({elapsed / 60:.1f}분)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
