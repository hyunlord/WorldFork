"""캐릭터 base portrait generation — Flux dev 본격 (★ Phase 1 v2).

본 commit (★ 본인 결정 + 환경 진단):
- 환경 본격: ComfyUI 8188 (★ pulid-flux-pipeline)
- 로드 본격: Flux dev (★ Schnell X, 25-step 본격)
- 비요른 (BARBARIAN) / 에르웬 (FAERIE)
- 8장/캐릭터 (★ 16장 총)
- LoRA X (★ Phase 2 본격, 일관성 검수 후)

작품 본문 정합:
- 비요른: 두 손 도끼 / 부족 마킹 / 흉터 (★ BARBARIAN)
- 에르웬: 영혼 마법 / 투명 날개 / 빛나는 아우라 (★ FAERIE)
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

COMFYUI_API = "http://localhost:8188"
OUTPUT_DIR = Path.home() / "ComfyUI" / "output" / "worldfork"


def detect_comfyui_output_dir() -> Path | None:
    """ComfyUI 본격 output dir 자동 진단 (★ 본인 finding 직접 답).

    본격 우선순위:
    1. ComfyUI process /proc/<pid>/cwd (★ 본인 환경 진단 본격)
    2. Path.home() / "ComfyUI" / "output" (★ default)

    Returns:
        본격 output dir Path (★ /worldfork 미포함, 상위)
    """
    try:
        result = subprocess.run(
            ["pgrep", "-f", "ComfyUI.*main.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        for pid in result.stdout.strip().split("\n"):
            if pid:
                cwd_link = Path(f"/proc/{pid}/cwd")
                if cwd_link.exists():
                    cwd = cwd_link.resolve()
                    output_dir = cwd / "output"
                    if output_dir.is_dir():
                        return output_dir
    except (OSError, subprocess.SubprocessError):
        pass

    default = Path.home() / "ComfyUI" / "output"
    return default if default.is_dir() else None


# ─── 캐릭터 본격 정의 (★ 작품 본문 정합) ───

CHARACTERS: dict[str, dict[str, str]] = {
    "비요른": {
        "race": "BARBARIAN",
        "race_visual": (
            "muscular barbarian warrior, fur and leather clothing, "
            "tribal markings"
        ),
        "appearance": (
            "tall man, dark braided hair, fierce blue eyes, "
            "weathered skin, scar on cheek"
        ),
        "weapon": "two-handed battle axe",
        "personality_visual": "stoic determined expression",
    },
    "에르웬": {
        "race": "FAERIE",
        "race_visual": (
            "ethereal faerie, delicate translucent wings, "
            "glowing aura, slender build"
        ),
        "appearance": (
            "petite woman, long silver hair, luminous green eyes, "
            "fair pale skin, pointed ears"
        ),
        "weapon": "soul magic energy in palms, no physical weapon",
        "personality_visual": "wise gentle expression",
    },
}


# ─── pose 본격 (★ 8장 다양) ───

POSES: list[str] = [
    "front view portrait, head and shoulders, neutral expression",
    "front view portrait, head and shoulders, determined expression",
    "side view profile, head and shoulders",
    "three quarter view, slight smile",
    "three quarter view, serious focused expression",
    "front view full body, standing pose",
    "front view full body, action ready stance",
    "three quarter view full body, walking forward",
]


# ─── Flux Schnell workflow 본격 ───


def build_flux_workflow(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    steps: int = 25,
    guidance: float = 3.5,
) -> dict[str, Any]:
    """Flux dev workflow JSON 본격 (★ 환경 진단: pulid-flux-pipeline).

    Flux dev 본격 본질:
    - 25-step 본격 (★ Schnell 4-step과 다름)
    - cfg 1.0 (★ Flux 본격 KSampler cfg=1)
    - FluxGuidance 노드 본격 (★ guidance scale 본격)
    - euler simple sampler
    """
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "flux1-dev.safetensors",
                "weight_dtype": "default",
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
                "model": ["1", 0],
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
                "filename_prefix": "worldfork/character",
            },
        },
    }


# ─── ComfyUI API 본격 ───


def submit_workflow(workflow: dict[str, Any]) -> str:
    """ComfyUI API에 workflow 제출 (★ prompt_id 반환)."""
    response = requests.post(
        f"{COMFYUI_API}/prompt",
        json={"prompt": workflow},
        timeout=10,
    )
    response.raise_for_status()
    result: str = response.json()["prompt_id"]
    return result


def wait_for_completion(
    prompt_id: str, timeout: int = 300
) -> dict[str, Any]:
    """ComfyUI 완료 대기 (★ history API).

    Phase 2 본격 fix: timeout 180→300s (★ Flux dev 25-step 안전).
    """
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        history = requests.get(
            f"{COMFYUI_API}/history/{prompt_id}", timeout=5
        )
        if history.status_code == 200:
            data = history.json().get(prompt_id)
            if data and data.get("status", {}).get("completed"):
                result: dict[str, Any] = data
                return result
        time.sleep(2)
    raise TimeoutError(f"prompt_id {prompt_id} 본격 X 완료")


# ─── prompt 본격 ───


def build_character_prompt(
    char_data: dict[str, str],
    pose: str,
    background: str = "neutral grey studio background",
    style: str = (
        "fantasy concept art, painterly digital art, detailed, "
        "cinematic lighting"
    ),
) -> str:
    """캐릭터 portrait prompt 본격 (★ race + appearance + pose + style)."""
    return (
        f"{char_data['race_visual']}, "
        f"{char_data['appearance']}, "
        f"{char_data['personality_visual']}, "
        f"{pose}, "
        f"{background}, "
        f"holding {char_data['weapon']}, "
        f"{style}, masterpiece, best quality, 8k uhd, sharp focus"
    )


# ─── generation pipeline 본격 ───


def generate_character_set(
    character_name: str,
    num_images: int = 8,
) -> list[Path]:
    """캐릭터 base portrait set 본격 generation.

    본 commit fix (★ 옵션 3, 본인 finding 직접 답):
    - ComfyUI 본격 cwd 자동 진단 (★ rename 안전)
    - X 발견 시 사일런트 실패 X (★ 정공법)
    - cross-device shutil fallback
    """
    import shutil

    char_data = CHARACTERS[character_name]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ★ 본 commit fix: ComfyUI output dir 자동 진단
    comfyui_output = detect_comfyui_output_dir()
    if comfyui_output is None:
        print("[ERROR] ComfyUI output dir 본격 X 진단 — generation skip")
        return []
    print(f"[INFO] ComfyUI output: {comfyui_output}")

    generated_paths: list[Path] = []
    poses_to_use = POSES[:num_images]

    seed_base = 1042 if character_name == "에르웬" else 42

    for i, pose in enumerate(poses_to_use):
        prompt = build_character_prompt(char_data, pose=pose)
        seed = seed_base + i

        print(f"[{i + 1}/{num_images}] {character_name} — {pose[:40]}...")

        try:
            workflow = build_flux_workflow(prompt=prompt, seed=seed)
            prompt_id = submit_workflow(workflow)
            result = wait_for_completion(prompt_id)

            outputs = result.get("outputs", {})
            for node_outputs in outputs.values():
                images = node_outputs.get("images", [])
                for img in images:
                    subfolder = img.get("subfolder", "")
                    if subfolder:
                        src = comfyui_output / subfolder / img["filename"]
                    else:
                        src = comfyui_output / img["filename"]

                    if src.exists():
                        pose_slug = (
                            pose[:30]
                            .replace(" ", "_")
                            .replace(",", "")
                        )
                        dst = (
                            OUTPUT_DIR
                            / f"{character_name}_{i:02d}_{pose_slug}.png"
                        )
                        try:
                            src.rename(dst)
                        except OSError:
                            shutil.move(str(src), str(dst))
                        generated_paths.append(dst)
                        print(f"  → {dst.name}")
                    else:
                        # ★ 본 commit: 사일런트 실패 X (★ 정공법)
                        print(
                            f"  ⚠️ X 발견: {src} "
                            "(★ post-process 본격 필요)"
                        )
        except Exception as e:
            print(f"  ❌ {e}")

    return generated_paths


def main() -> int:
    print("=" * 80)
    print(
        "Visual Phase 1 v2 — 캐릭터 base "
        "(Flux Schnell, LoRA Phase 2 미룸)"
    )
    print("=" * 80)

    try:
        r = requests.get(f"{COMFYUI_API}/system_stats", timeout=5)
        r.raise_for_status()
        print(f"[OK] ComfyUI {COMFYUI_API} 본격 작동")
    except requests.RequestException as e:
        print(f"[ERROR] ComfyUI 접속 X: {e}")
        return 1

    start = time.monotonic()

    print("\n=== 비요른 (BARBARIAN) ===")
    bjorn_paths = generate_character_set("비요른", num_images=8)
    print(f"비요른: {len(bjorn_paths)}장 본격")

    print("\n=== 에르웬 (FAERIE) ===")
    erwen_paths = generate_character_set("에르웬", num_images=8)
    print(f"에르웬: {len(erwen_paths)}장 본격")

    elapsed = time.monotonic() - start

    metadata: dict[str, Any] = {
        "phase": "Phase 1 v2",
        "model": "FLUX.1-dev",
        "characters": list(CHARACTERS.keys()),
        "num_images_per_character": 8,
        "elapsed_seconds": round(elapsed, 1),
        "output_dir": str(OUTPUT_DIR),
        "generated_files": {
            "비요른": [p.name for p in bjorn_paths],
            "에르웬": [p.name for p in erwen_paths],
        },
        "notes": "LoRA X (Phase 2 본격), prompt-only 일관성 본격 검증",
    }
    metadata_path = OUTPUT_DIR / "phase1_v2_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== 본격 결과 ===")
    print(f"비요른: {len(bjorn_paths)}장")
    print(f"에르웬: {len(erwen_paths)}장")
    print(f"시간: {elapsed:.1f}s ({elapsed / 60:.1f}분)")
    print(f"metadata: {metadata_path}")
    print(f"본인 검수 본질: {OUTPUT_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
