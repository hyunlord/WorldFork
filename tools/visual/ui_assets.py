"""WorldFork UI 자료 본격 — Phase 6 7 화면 본격 재사용 인프라.

본 commit (★ Phase 6a):
- MAIN_SCREEN_ASSETS dict 본격
- build_workflow_with_lora() — 옵션 LoRA 노드 본격 (★ Flux dev 25-step)
- generate_ui_asset() — 단일 자료 generation 본격

후속 Phase 6b-g 본격 재사용:
- 6b: 게임 플레이 화면
- 6c: 캐릭터 시트
- 6d: 균열 진입 (★ v2 핏빛성채 자료)
- 6e: 전투
- 6f: 대화/이벤트
- 6g: 시작 메뉴

본격 워크플로 (★ 환경 정합):
- UNETLoader: flux1-dev.safetensors
- DualCLIPLoader: clip_l + t5xxl
- VAELoader: ae.safetensors
- LoraLoaderModelOnly: model only (★ Flux dev 본격 pattern)
- KSampler: 25-step + FluxGuidance + cfg 1.0
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Final

# ★ Phase 5b LoRA 본격 (worldfork_bjorn_v1.safetensors, trigger=bjorn_warrior)
BJORN_LORA_NAME: Final[str] = "worldfork_bjorn_v1.safetensors"

# 본격 자료 dict (★ Phase 6a 메인 화면)
MAIN_SCREEN_ASSETS: Final[dict[str, dict[str, Any]]] = {
    "main_bg": {
        "filename_prefix": "ui_main_bg",
        "width": 1920,
        "height": 1080,
        "prompt": (
            "dark fantasy dungeon entrance, ancient stone archway, "
            "torchlight flickering, ominous atmosphere, "
            "depths of darkness below, gothic architecture, "
            "moss-covered walls, heavy iron door, "
            "dramatic lighting, cinematic wide shot, "
            "8k, highly detailed, masterpiece"
        ),
        "negative_prompt": (
            "modern, bright, cheerful, cartoon, anime, low quality"
        ),
        "lora": None,  # ★ 배경은 LoRA X
        "lora_strength": 1.0,
    },
    "main_bjorn": {
        "filename_prefix": "ui_main_bjorn",
        "width": 768,
        "height": 1024,
        "prompt": (
            "bjorn_warrior, barbarian male warrior portrait, "
            "rugged battle-scarred face, fur and leather armor, "
            "two-handed axe, stern determined expression, "
            "fierce blue eyes, dark braided hair and beard, "
            "tribal markings, dark fantasy painterly, "
            "dramatic lighting, 8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, photorealistic, low quality"
        ),
        "lora": BJORN_LORA_NAME,  # ★ Phase 5b 본격 trigger
        "lora_strength": 0.8,
    },
    "main_erwen": {
        "filename_prefix": "ui_main_erwen",
        "width": 768,
        "height": 1024,
        "prompt": (
            "ethereal faerie female mage portrait, "
            "delicate translucent wings, glowing aura, "
            "long silver hair, luminous green eyes, "
            "fair pale skin, pointed ears, "
            "elegant pale robes with arcane embroidery, "
            "soul magic energy in palms, mystical, "
            "wise gentle expression, dark fantasy painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, photorealistic, low quality"
        ),
        "lora": None,  # ★ Phase 1 일관성 prompt-only OK
        "lora_strength": 1.0,
    },
}


# 본격 자료 dict (★ Phase 6b 게임 플레이 화면, 4개)
GAMEPLAY_SCREEN_ASSETS: Final[dict[str, dict[str, Any]]] = {
    "gameplay_bg_crystal": {
        "filename_prefix": "ui_gameplay_bg_crystal",
        "width": 1920,
        "height": 1080,
        "prompt": (
            "dark fantasy crystal cavern interior, "
            "glowing teal and cyan crystals embedded in stone walls, "
            "dripping water from rocky ceiling, "
            "ethereal blue-green ambient light, "
            "ancient stone floor with mineral deposits, "
            "deep underground atmosphere, mysterious, "
            "cinematic wide shot, painterly, "
            "8k, highly detailed, masterpiece"
        ),
        "negative_prompt": (
            "modern, bright, cheerful, cartoon, anime, low quality, "
            "characters, people"
        ),
        "lora": None,  # ★ 배경 LoRA X
        "lora_strength": 1.0,
    },
    "gameplay_bjorn_portrait": {
        "filename_prefix": "ui_gameplay_bjorn_portrait",
        "width": 512,
        "height": 768,
        "prompt": (
            "bjorn_warrior, barbarian male warrior, "
            "in-game character portrait, half-body shot, "
            "ready stance, two-handed axe gripped firmly, "
            "battle-worn fur and leather armor, "
            "dark fantasy dungeon background, dim torchlight, "
            "stern focused expression, fierce blue eyes, "
            "dark braided hair and thick beard, tribal markings, "
            "painterly fantasy game style, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, photorealistic, low quality, "
            "full body"
        ),
        "lora": BJORN_LORA_NAME,  # ★ Phase 5b 본격 ship
        "lora_strength": 0.8,
    },
    "gameplay_erwen_portrait": {
        "filename_prefix": "ui_gameplay_erwen_portrait",
        "width": 512,
        "height": 768,
        "prompt": (
            "ethereal faerie female mage, in-game character portrait, "
            "half-body shot, magical ready stance, "
            "delicate translucent wings glowing softly, "
            "long silver hair flowing, luminous green eyes, "
            "fair pale skin, pointed ears, "
            "elegant pale robes with arcane silver embroidery, "
            "soul magic energy in palms, mystical aura, "
            "dark fantasy dungeon background, dim ambient light, "
            "graceful focused expression, painterly game style, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, photorealistic, low quality, "
            "full body"
        ),
        "lora": None,  # ★ Phase 1 + 6a 정합 본격
        "lora_strength": 1.0,
    },
    "gameplay_essence_effect": {
        "filename_prefix": "ui_gameplay_essence_effect",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "magical floating essence orb, "
            "swirling teal and cyan energy, "
            "ethereal glow, particles drifting upward, "
            "dark void background, mystical aura, "
            "isolated VFX element, soft transparent edges, "
            "fantasy game effect, painterly, "
            "8k, highly detailed, masterpiece"
        ),
        "negative_prompt": (
            "characters, people, scenery, modern, low quality"
        ),
        "lora": None,  # ★ VFX 본격
        "lora_strength": 1.0,
    },
}


# 본격 dict 통합 (★ Phase 6 화면별 본격, 후속 6c-g 본격 재사용)
ALL_ASSET_DICTS: Final[dict[str, dict[str, dict[str, Any]]]] = {
    "main_screen": MAIN_SCREEN_ASSETS,
    "gameplay_screen": GAMEPLAY_SCREEN_ASSETS,
    # 후속 Phase 6c-g 본격 추가:
    # "character_sheet": CHARACTER_SHEET_ASSETS,
    # "rift_entry": RIFT_ENTRY_ASSETS,
    # "combat": COMBAT_ASSETS,
    # "dialogue": DIALOGUE_ASSETS,
    # "start_menu": START_MENU_ASSETS,
}


@dataclass(frozen=True, slots=True)
class UIAssetSpec:
    """UI 자료 spec 본격 (★ Phase 6 재사용)."""

    filename_prefix: str
    width: int
    height: int
    prompt: str
    negative_prompt: str
    lora: str | None = None
    lora_strength: float = 1.0


def spec_from_dict(name: str, data: dict[str, Any]) -> UIAssetSpec:
    """dict → UIAssetSpec 본격 변환."""
    raw_lora = data.get("lora")
    lora_value = raw_lora if isinstance(raw_lora, str) else None
    return UIAssetSpec(
        filename_prefix=str(data["filename_prefix"]),
        width=int(data["width"]),
        height=int(data["height"]),
        prompt=str(data["prompt"]),
        negative_prompt=str(data["negative_prompt"]),
        lora=lora_value,
        lora_strength=float(data.get("lora_strength", 1.0)),
    )


def build_workflow_with_lora(
    spec: UIAssetSpec,
    seed: int = 12345,
    steps: int = 25,
    guidance: float = 3.5,
) -> dict[str, Any]:
    """ComfyUI workflow 본격 (★ Flux dev 25-step + 옵션 LoRA).

    spec.lora None → 단순 Flux dev workflow (★ LoRA 노드 X).
    spec.lora 본격 → UNETLoader → LoraLoaderModelOnly → KSampler.
    """
    # 본격 model 본격 분기 (★ LoRA X / O)
    model_ref: list[Any] = ["1b", 0] if spec.lora is not None else ["1", 0]

    nodes: dict[str, dict[str, Any]] = {
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
            "inputs": {"text": spec.prompt, "clip": ["2", 0]},
        },
        "5": {
            "class_type": "FluxGuidance",
            "inputs": {"conditioning": ["4", 0], "guidance": guidance},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": spec.negative_prompt, "clip": ["2", 0]},
        },
        "7": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": spec.width,
                "height": spec.height,
                "batch_size": 1,
            },
        },
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "model": model_ref,
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
                "filename_prefix": f"worldfork/{spec.filename_prefix}",
            },
        },
    }

    # 본격 LoRA 노드 옵션 (★ Phase 5b worldfork_bjorn_v1)
    if spec.lora is not None:
        nodes["1b"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": spec.lora,
                "strength_model": spec.lora_strength,
            },
        }

    return {"prompt": nodes}


def generate_ui_asset(
    spec: UIAssetSpec,
    *,
    comfyui_url: str = "http://localhost:8188",
    seed: int = 12345,
) -> str:
    """ComfyUI 본격 호출 + 자료 generation.

    return: prompt_id (★ ComfyUI queue 본격)
    """
    workflow = build_workflow_with_lora(spec, seed=seed)
    data = json.dumps(workflow).encode("utf-8")
    req = urllib.request.Request(
        f"{comfyui_url}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result: dict[str, Any] = json.loads(resp.read())
    prompt_id = result.get("prompt_id")
    if not isinstance(prompt_id, str):
        raise RuntimeError(f"본격 prompt_id 본격 X: {result!r}")
    return prompt_id
