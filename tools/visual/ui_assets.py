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


# 본격 자료 dict (★ Phase 6c 캐릭터 시트, 3개)
CHARACTER_SHEET_ASSETS: Final[dict[str, dict[str, Any]]] = {
    "character_bjorn_full": {
        "filename_prefix": "ui_character_bjorn_full",
        "width": 1024,
        "height": 1536,
        "prompt": (
            "bjorn_warrior, barbarian male warrior, "
            "full body character sheet portrait, standing pose, "
            "two-handed battle axe gripped firmly, "
            "battle-worn fur and leather armor, "
            "thick leather boots, tribal markings visible, "
            "dark braided hair and thick beard, "
            "fierce blue eyes, scarred face, "
            "dark fantasy painterly style, neutral dark background, "
            "rim lighting, full character visible from head to feet, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, low quality, "
            "cropped, partial body, half body, close-up"
        ),
        "lora": BJORN_LORA_NAME,  # ★ Phase 5b ship 본격
        "lora_strength": 0.8,
    },
    "character_erwen_full": {
        "filename_prefix": "ui_character_erwen_full",
        "width": 1024,
        "height": 1536,
        "prompt": (
            "ethereal faerie female mage, "
            "full body character sheet portrait, standing pose, "
            "delicate translucent wings glowing softly, "
            "long silver hair flowing past shoulders, "
            "luminous green eyes, fair pale skin, pointed ears, "
            "elegant pale robes with arcane silver embroidery, "
            "soul magic energy in palms, mystical aura, "
            "dark fantasy painterly style, neutral dark background, "
            "rim lighting, full character visible from head to feet, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, low quality, "
            "cropped, partial body, half body, close-up"
        ),
        "lora": None,  # ★ Phase 1+6a+6b 정합 본격
        "lora_strength": 1.0,
    },
    "character_essence_grid": {
        "filename_prefix": "ui_character_essence_grid",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "five mystical floating essence orbs arranged "
            "in horizontal row, "
            "first: earth brown essence with soil particles, "
            "second: teal cyan essence with ice crystals, "
            "third: blue-gray essence with mind whispers, "
            "fourth: crimson blood-red essence with dark aura, "
            "fifth: golden light essence with radiance, "
            "each orb distinct and separated, "
            "dark void background, isolated VFX elements, "
            "fantasy game collectible icons, painterly, "
            "8k, highly detailed, masterpiece"
        ),
        "negative_prompt": (
            "characters, people, scenery, modern, low quality"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
}


# 본격 자료 dict (★ Phase 6d 균열 진입, 4개)
RIFT_ENTRY_ASSETS: Final[dict[str, dict[str, Any]]] = {
    "rift_bloodcastle": {
        "filename_prefix": "ui_rift_bloodcastle",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "dark fantasy crimson blood castle interior, "
            "gothic stone archways drenched in blood, "
            "central altar with open Necronomicon grimoire, "
            "weeping goddess statue, ritual pentagram circle on floor, "
            "torchlight casting red shadows, "
            "deep dread atmosphere, 8th grade boss lair, "
            "cinematic wide shot, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, bright, cheerful, cartoon, anime, low quality, "
            "characters, people"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "rift_glacier": {
        "filename_prefix": "ui_rift_glacier",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "dark fantasy frozen glacier cavern interior, "
            "massive blue-white ice walls and stalactites, "
            "frozen ground with cracks emitting cold mist, "
            "pale cyan ethereal light, frost crystals scattered, "
            "ancient frozen pillars, breath-frosting cold atmosphere, "
            "deep underground frozen lair, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, bright, cheerful, cartoon, anime, low quality, "
            "characters, people, warm colors"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "rift_greenmine": {
        "filename_prefix": "ui_rift_greenmine",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "dark fantasy abandoned green mine interior, "
            "toxic emerald glowing crystals embedded in stone, "
            "rusted mine carts and broken wooden supports, "
            "sickly green mist drifting through tunnels, "
            "moss-covered mineral veins, dripping toxic water, "
            "abandoned mining tools, ominous green ambient light, "
            "deep underground toxic atmosphere, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, bright, cheerful, cartoon, anime, low quality, "
            "characters, people"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "rift_steeltomb": {
        "filename_prefix": "ui_rift_steeltomb",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "dark fantasy steel mausoleum interior, "
            "polished cold steel walls and floors, "
            "rows of iron sarcophagi with engraved runes, "
            "metallic blue-gray torchlight reflections, "
            "ancient warrior tombs, ceremonial steel banners, "
            "deep silence atmosphere, oppressive metallic chill, "
            "cinematic wide shot, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, bright, cheerful, cartoon, anime, low quality, "
            "characters, people, warm colors"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
}


# 본격 자료 dict (★ Phase 6e 전투, 5개)
COMBAT_ASSETS: Final[dict[str, dict[str, Any]]] = {
    "combat_bjorn_action": {
        "filename_prefix": "ui_combat_bjorn_action",
        "width": 768,
        "height": 1024,
        "prompt": (
            "bjorn_warrior, barbarian male warrior, "
            "dynamic combat action pose, mid-swing of two-handed battle axe, "
            "fierce battle cry expression, blue eyes blazing with fury, "
            "muscles taut, fur cape flowing from motion, "
            "leather armor with battle scars, tribal markings visible, "
            "long dark braided hair flying back, thick beard, "
            "dark fantasy battle scene, dramatic motion blur on axe, "
            "rim lighting, painterly action shot, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, low quality, static pose, calm"
        ),
        "lora": BJORN_LORA_NAME,  # ★ Phase 5b ship, 5th use
        "lora_strength": 0.8,
    },
    "combat_erwen_casting": {
        "filename_prefix": "ui_combat_erwen_casting",
        "width": 768,
        "height": 1024,
        "prompt": (
            "ethereal faerie female mage, dynamic spellcasting pose, "
            "staff raised high with crystal orb blazing "
            "bright blue-white light, "
            "magical energy swirling around hands, "
            "delicate translucent wings spread wide, "
            "silver-white long hair flowing from magical wind, "
            "luminous green eyes glowing with arcane power, "
            "pale robes with silver embroidery billowing, "
            "ethereal aura, fierce focused expression, "
            "dark fantasy battle scene, painterly action shot, "
            "rim lighting, 8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, low quality, static pose, calm"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "combat_monster_blade_wolf": {
        "filename_prefix": "ui_combat_monster_blade_wolf",
        "width": 768,
        "height": 1024,
        "prompt": (
            "monstrous blade wolf creature, 9th grade dungeon beast, "
            "dark fur with razor-sharp metallic blade-like spikes "
            "along spine, "
            "glowing red predator eyes, snarling fangs bared, "
            "muscular quadruped lupine body, low aggressive crouch, "
            "saliva dripping, fierce hunting posture, "
            "battle-scarred hide, claws extended, "
            "dark dungeon background, ominous lighting, "
            "dark fantasy creature design, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "cute, friendly, modern, cartoon, anime, soft, low quality, "
            "human, humanoid"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    # ★ 다듬기 3순위: 1층 4 zone 전투 일러스트 균형(서 노움/남 구울/북 고블린).
    "combat_monster_gnome": {
        "filename_prefix": "ui_combat_monster_gnome",
        "width": 768,
        "height": 1024,
        "prompt": (
            "hostile gnome creature, 9th grade dungeon dweller, "
            "small earthy humanoid, brown wrinkled skin, large ugly nose, "
            "dirt-stained skin, dirty rough tunic, "
            "wielding a crude pickaxe, malicious grin, beady cunning eyes, "
            "crouched ambush stance among crystal rocks, "
            "dark dungeon background, ominous lighting, "
            "dark fantasy creature design, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "cute, friendly, modern, cartoon, anime, soft, low quality, tall, heroic"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "combat_monster_ghoul": {
        "filename_prefix": "ui_combat_monster_ghoul",
        "width": 768,
        "height": 1024,
        "prompt": (
            "ghoulish wraith creature, 9th grade dungeon undead, "
            "ghostly translucent humanoid, tattered ethereal robes, "
            "hollow glowing eye sockets, shadow form, "
            "drifting menacingly with shadow tendrils, "
            "decayed gaunt face, clawed ethereal hands reaching, "
            "dark crystal cavern background, eerie cold lighting, "
            "dark fantasy creature design, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "cute, friendly, modern, cartoon, anime, soft, low quality, "
            "solid body, colorful"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "combat_monster_goblin": {
        "filename_prefix": "ui_combat_monster_goblin",
        "width": 768,
        "height": 1024,
        "prompt": (
            "goblin warrior creature, 9th grade dungeon raider, "
            "small green-skinned humanoid, sharp teeth, pointed ears, "
            "hunched aggressive posture, tattered loincloth, "
            "wielding a crude rusty short sword and small wooden shield, "
            "snarling battle cry, wild bloodshot eyes, "
            "dark dungeon background, ominous torchlight, "
            "dark fantasy creature design, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "cute, friendly, modern, cartoon, anime, soft, low quality, "
            "human, tall, heroic"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "combat_vfx_axe_strike": {
        "filename_prefix": "ui_combat_vfx_axe_strike",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "dynamic axe slash VFX effect, "
            "crescent arc of golden energy, "
            "sharp slicing motion lines, "
            "sparks and impact particles flying outward, "
            "isolated VFX element, transparent edges, "
            "dark void background, "
            "fantasy game battle effect, painterly, "
            "8k, highly detailed, masterpiece"
        ),
        "negative_prompt": (
            "characters, people, scenery, modern, low quality"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "combat_vfx_magic_missile": {
        "filename_prefix": "ui_combat_vfx_magic_missile",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "magical missile projectile VFX effect, "
            "swirling blue-white arcane energy bolt, "
            "trailing particle stream, "
            "glowing ethereal core with crackling edges, "
            "isolated VFX element, transparent edges, "
            "dark void background, "
            "fantasy game spell effect, painterly, "
            "8k, highly detailed, masterpiece"
        ),
        "negative_prompt": (
            "characters, people, scenery, modern, low quality"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
}


# 본격 자료 dict (★ Phase 6f 대화/이벤트, 4개)
DIALOGUE_ASSETS: Final[dict[str, dict[str, Any]]] = {
    "dialogue_message_stone": {
        "filename_prefix": "ui_dialogue_message_stone",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "ancient mystical message stone, "
            "smooth polished obsidian surface "
            "with glowing runic inscriptions, "
            "soft pulsing blue-white ethereal light from within, "
            "floating slightly above the ground, "
            "magical communication artifact, "
            "intricate runes carved deep, "
            "dark void background with mist, "
            "fantasy game key item, painterly, "
            "8k, highly detailed, masterpiece"
        ),
        "negative_prompt": (
            "characters, people, scenery, modern, low quality"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "dialogue_other_explorer_male": {
        "filename_prefix": "ui_dialogue_other_explorer_male",
        "width": 768,
        "height": 1024,
        "prompt": (
            "human male dungeon explorer portrait, half-body shot, "
            "weathered adventurer in his thirties, "
            "short dark hair with grey streaks, sharp hazel eyes, "
            "stubbled jaw, serious focused expression, "
            "studded leather armor with travel cloak, "
            "sword sheathed at side, lantern in hand, "
            "dark fantasy dungeon background with dim torchlight, "
            "painterly portrait style, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, low quality, "
            "bjorn, viking, barbarian, axe, beard, braided hair"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "dialogue_other_explorer_female": {
        "filename_prefix": "ui_dialogue_other_explorer_female",
        "width": 768,
        "height": 1024,
        "prompt": (
            "human female dungeon explorer portrait, half-body shot, "
            "rogue adventurer in her late twenties, "
            "raven black hair tied back in practical braid, "
            "piercing dark green eyes, focused alert expression, "
            "dark leather armor with hood pulled back, "
            "twin daggers at belt, gloved hands, "
            "dark fantasy dungeon background with dim torchlight, "
            "painterly portrait style, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "modern, anime, cartoon, soft, low quality, "
            "erwen, elven, silver hair, staff, wings, robes, faerie"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
    "dialogue_ancient_stone": {
        "filename_prefix": "ui_dialogue_ancient_stone",
        "width": 1024,
        "height": 1024,
        "prompt": (
            "ancient towering stone monolith in dungeon chamber, "
            "weathered gray stone covered in deep carved runic glyphs, "
            "faint warm golden glow emanating from the runes, "
            "moss and cracks of age, ceremonial offerings at base, "
            "small carved bowl for tributes, "
            "dark stone chamber background with dim torchlight, "
            "deep mystical atmosphere, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "characters, people, modern, cartoon, low quality"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
}


# 본격 자료 dict (★ Phase 6g 시작 메뉴, 1개 — minimal 마무리)
START_MENU_ASSETS: Final[dict[str, dict[str, Any]]] = {
    "start_menu_bg": {
        "filename_prefix": "ui_start_menu_bg",
        "width": 1920,
        "height": 1080,
        "prompt": (
            "dark fantasy ominous dungeon entrance from outside, "
            "massive ancient stone gateway carved into mountainside, "
            "pitch-black void inside the entrance, "
            "only faint reddish glow from deep within, "
            "weathered runic inscriptions on the arch, "
            "cracked stone steps leading down into darkness, "
            "moonless night atmosphere, foreboding silence, "
            "vast cinematic wide shot, painterly, "
            "8k, masterpiece, highly detailed"
        ),
        "negative_prompt": (
            "bright, cheerful, modern, cartoon, anime, low quality, "
            "characters, people, interior view"
        ),
        "lora": None,
        "lora_strength": 1.0,
    },
}


# 본격 dict 통합 7/7 마무리 (★ Phase 6 완성)
ALL_ASSET_DICTS: Final[dict[str, dict[str, dict[str, Any]]]] = {
    "main_screen": MAIN_SCREEN_ASSETS,
    "gameplay_screen": GAMEPLAY_SCREEN_ASSETS,
    "character_sheet": CHARACTER_SHEET_ASSETS,
    "rift_entry": RIFT_ENTRY_ASSETS,
    "combat": COMBAT_ASSETS,
    "dialogue": DIALOGUE_ASSETS,
    "start_menu": START_MENU_ASSETS,
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
