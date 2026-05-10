"""LoRA 학습 결과 검증 — bjorn_warrior trigger word 본격 (★ Phase 5).

본 commit (★ ai-toolkit Flux LoRA 학습 후 검증):
- 학습된 LoRA로 신규 자료 본격
- 일관성 검증 (★ 같은 캐릭터?)
- ComfyUI workflow에 LoraLoaderModelOnly 노드 삽입
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
    detect_comfyui_output_dir,
    submit_workflow,
    wait_for_completion,
)

LORA_NAME = "worldfork_bjorn_v1.safetensors"
TRIGGER_WORD = "bjorn_warrior"


# 검증 prompts (★ 다양 scene)
TEST_PROMPTS: list[str] = [
    (
        "bjorn_warrior, barbarian warrior, holding axe, "
        "front portrait, fantasy concept art"
    ),
    (
        "bjorn_warrior, side profile, fierce determined expression, "
        "fantasy concept art"
    ),
    (
        "bjorn_warrior, full body, action pose with axe raised, "
        "fantasy concept art"
    ),
    (
        "bjorn_warrior, in crystal cavern, holding axe, "
        "fantasy concept art"
    ),
]


def build_lora_workflow(
    prompt: str,
    seed: int,
    lora_name: str = LORA_NAME,
    lora_strength: float = 0.8,
    width: int = 1024,
    height: int = 1024,
    steps: int = 25,
    guidance: float = 3.5,
) -> dict[str, Any]:
    """LoRA 적용 Flux dev workflow (★ 25-step + FluxGuidance 본격).

    LoraLoaderModelOnly 노드를 UNETLoader → KSampler 사이에 본격 삽입.
    """
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "flux1-dev.safetensors",
                "weight_dtype": "default",
            },
        },
        "1b": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": lora_name,
                "strength_model": lora_strength,
            },
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5xxl_fp16.safetensors",
                "type": "flux",
            },
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["2", 0]},
        },
        "5": {
            "class_type": "FluxGuidance",
            "inputs": {"conditioning": ["4", 0], "guidance": guidance},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["2", 0]},
        },
        "7": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            },
        },
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1b", 0],  # ★ LoRA 적용된 model
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["8", 0], "vae": ["3", 0]},
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["9", 0],
                "filename_prefix": "worldfork/lora_test",
            },
        },
    }


def main() -> int:
    print("=" * 80)
    print("Phase 5 — 비요른 LoRA 검증")
    print("=" * 80)

    comfyui_output = detect_comfyui_output_dir()
    if comfyui_output is None:
        print("[ERROR] ComfyUI output dir 미진단")
        return 1

    # ★ LoRA 자료가 ComfyUI loras 폴더에 있어야 본격
    lora_target = comfyui_output.parent / "models" / "loras" / LORA_NAME
    if not lora_target.exists():
        print(f"[WARN] {lora_target} 미발견")
        print(
            "  → ai-toolkit output ~/lora_output/worldfork_bjorn_v1/"
            "*.safetensors 본격 복사 필요"
        )
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    generated: list[Path] = []

    for i, prompt in enumerate(TEST_PROMPTS):
        seed = 88800 + i * 100
        print(f"\n[{i + 1}/{len(TEST_PROMPTS)}] {prompt[:60]}...")

        try:
            workflow = build_lora_workflow(prompt=prompt, seed=seed)
            prompt_id = submit_workflow(workflow)
            result = wait_for_completion(prompt_id, timeout=300)
        except Exception as e:
            print(f"  ❌ {e}")
            continue

        outputs = result.get("outputs", {})
        for node_outputs in outputs.values():
            for img in node_outputs.get("images", []):
                subfolder = img.get("subfolder", "")
                if subfolder:
                    src = comfyui_output / subfolder / img["filename"]
                else:
                    src = comfyui_output / img["filename"]

                if src.exists():
                    dst = OUTPUT_DIR / f"lora_test_bjorn_{i:02d}.png"
                    try:
                        src.rename(dst)
                    except OSError:
                        shutil.move(str(src), str(dst))
                    generated.append(dst)
                    print(f"  → {dst.name}")

    elapsed = time.monotonic() - start

    metadata: dict[str, Any] = {
        "phase": "Phase 5 LoRA test",
        "lora_name": LORA_NAME,
        "trigger_word": TRIGGER_WORD,
        "test_prompts": TEST_PROMPTS,
        "elapsed_seconds": round(elapsed, 1),
        "generated_files": [p.name for p in generated],
    }
    metadata_path = OUTPUT_DIR / "phase5_lora_test_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== 결과 ===")
    print(f"LoRA test 자료: {len(generated)}/{len(TEST_PROMPTS)}")
    print(f"시간: {elapsed:.1f}s")
    print("본인 검수 본격: 일관성 OK?")

    return 0


if __name__ == "__main__":
    sys.exit(main())
