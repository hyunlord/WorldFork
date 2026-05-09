"""character_base.py 본격 단위 검증 (★ Visual Phase 1 v2 — Flux dev).

본 commit 본격 환경 진단:
- ComfyUI 8188 (★ pulid-flux-pipeline)
- Flux dev 본격 (★ Schnell X)
- 25-step + cfg 1.0 + FluxGuidance 본격
"""

from __future__ import annotations

from tools.visual.character_base import (
    CHARACTERS,
    POSES,
    build_character_prompt,
    build_flux_workflow,
)


def test_characters_dict_contains_required_pair() -> None:
    """비요른 + 에르웬 본격."""
    assert "비요른" in CHARACTERS
    assert "에르웬" in CHARACTERS


def test_characters_have_required_fields() -> None:
    required = {
        "race",
        "race_visual",
        "appearance",
        "weapon",
        "personality_visual",
    }
    for name, data in CHARACTERS.items():
        assert required.issubset(data.keys()), (
            f"{name}: 본격 X 필드 {required - data.keys()}"
        )


def test_bjorn_is_barbarian() -> None:
    assert CHARACTERS["비요른"]["race"] == "BARBARIAN"
    assert "barbarian" in CHARACTERS["비요른"]["race_visual"].lower()


def test_erwen_is_faerie() -> None:
    assert CHARACTERS["에르웬"]["race"] == "FAERIE"
    assert "faerie" in CHARACTERS["에르웬"]["race_visual"].lower()


def test_poses_count_8_or_more() -> None:
    """8 본격 pose 본격."""
    assert len(POSES) >= 8


def test_poses_are_unique() -> None:
    assert len(set(POSES)) == len(POSES)


def test_build_character_prompt_contains_race_and_weapon() -> None:
    p = build_character_prompt(CHARACTERS["비요른"], pose="front view")
    assert "barbarian" in p.lower()
    assert "axe" in p.lower()


def test_build_character_prompt_contains_pose() -> None:
    p = build_character_prompt(
        CHARACTERS["에르웬"], pose="side view profile"
    )
    assert "side view profile" in p
    assert "faerie" in p.lower()


def test_build_flux_workflow_has_25_steps_default() -> None:
    """Flux dev 본격 25-step (★ Schnell 4-step과 다름)."""
    wf = build_flux_workflow(prompt="test", seed=42)
    assert wf["8"]["inputs"]["steps"] == 25


def test_build_flux_workflow_cfg_1() -> None:
    """Flux KSampler cfg 1.0 본격 (★ guidance는 FluxGuidance 노드)."""
    wf = build_flux_workflow(prompt="test", seed=42)
    assert wf["8"]["inputs"]["cfg"] == 1.0


def test_build_flux_workflow_uses_dev_model() -> None:
    """flux1-dev.safetensors 본격 (★ pulid-flux-pipeline 환경)."""
    wf = build_flux_workflow(prompt="test", seed=42)
    assert "dev" in wf["1"]["inputs"]["unet_name"].lower()


def test_build_flux_workflow_default_resolution_1024() -> None:
    wf = build_flux_workflow(prompt="test", seed=42)
    assert wf["7"]["inputs"]["width"] == 1024
    assert wf["7"]["inputs"]["height"] == 1024


def test_build_flux_workflow_seed_reproducible() -> None:
    wf1 = build_flux_workflow(prompt="test", seed=42)
    wf2 = build_flux_workflow(prompt="test", seed=42)
    assert wf1["8"]["inputs"]["seed"] == wf2["8"]["inputs"]["seed"]


def test_build_flux_workflow_includes_text_encoders() -> None:
    """DualCLIPLoader 본격 (★ clip_l + t5xxl_fp16, type=flux)."""
    wf = build_flux_workflow(prompt="test", seed=42)
    clip_inputs = wf["2"]["inputs"]
    assert "clip_l" in clip_inputs["clip_name1"]
    assert "t5xxl" in clip_inputs["clip_name2"]
    assert clip_inputs["type"] == "flux"


def test_build_flux_workflow_has_flux_guidance_node() -> None:
    """FluxGuidance 노드 본격 (★ Flux dev 본격 guidance scale)."""
    wf = build_flux_workflow(prompt="test", seed=42, guidance=3.5)
    assert wf["5"]["class_type"] == "FluxGuidance"
    assert wf["5"]["inputs"]["guidance"] == 3.5


def test_build_flux_workflow_steps_override() -> None:
    """steps param 본격 override 가능."""
    wf = build_flux_workflow(prompt="test", seed=42, steps=10)
    assert wf["8"]["inputs"]["steps"] == 10
