"""tools/visual/ui_assets 본격 단위 검증 (★ Phase 6a)."""

from __future__ import annotations

from typing import Any, cast

from tools.visual.ui_assets import (
    ALL_ASSET_DICTS,
    BJORN_LORA_NAME,
    GAMEPLAY_SCREEN_ASSETS,
    MAIN_SCREEN_ASSETS,
    build_workflow_with_lora,
    spec_from_dict,
)


def _node(workflow: dict[str, Any], node_id: str) -> dict[str, Any]:
    """workflow에서 본격 node 추출 (★ test util)."""
    nodes = cast(dict[str, Any], workflow["prompt"])
    return cast(dict[str, Any], nodes[node_id])


class TestMainScreenAssets:
    def test_assets_count_three(self) -> None:
        assert len(MAIN_SCREEN_ASSETS) == 3
        assert set(MAIN_SCREEN_ASSETS) == {
            "main_bg",
            "main_bjorn",
            "main_erwen",
        }

    def test_main_bg_1920x1080(self) -> None:
        bg = MAIN_SCREEN_ASSETS["main_bg"]
        assert bg["width"] == 1920
        assert bg["height"] == 1080
        assert bg["lora"] is None

    def test_main_bjorn_lora(self) -> None:
        bjorn = MAIN_SCREEN_ASSETS["main_bjorn"]
        assert bjorn["lora"] == BJORN_LORA_NAME
        # ★ trigger word 본격 prompt 본격
        assert "bjorn_warrior" in str(bjorn["prompt"])

    def test_main_erwen_prompt_only(self) -> None:
        erwen = MAIN_SCREEN_ASSETS["main_erwen"]
        assert erwen["lora"] is None  # ★ Phase 1 일관성


class TestSpecFromDict:
    def test_conversion(self) -> None:
        spec = spec_from_dict("main_bg", MAIN_SCREEN_ASSETS["main_bg"])
        assert spec.filename_prefix == "ui_main_bg"
        assert spec.width == 1920
        assert spec.lora is None

    def test_lora_preserved(self) -> None:
        spec = spec_from_dict(
            "main_bjorn", MAIN_SCREEN_ASSETS["main_bjorn"]
        )
        assert spec.lora == BJORN_LORA_NAME
        assert spec.lora_strength == 0.8

    def test_frozen_dataclass(self) -> None:
        """UIAssetSpec frozen 본격 (★ slots)."""
        spec = spec_from_dict("main_bg", MAIN_SCREEN_ASSETS["main_bg"])
        import pytest

        with pytest.raises((AttributeError, Exception)):
            spec.width = 999  # type: ignore[misc]


class TestBuildWorkflow:
    def test_lora_none_simple(self) -> None:
        spec = spec_from_dict("main_bg", MAIN_SCREEN_ASSETS["main_bg"])
        wf = build_workflow_with_lora(spec, seed=12345)
        nodes = cast(dict[str, Any], wf["prompt"])
        assert "1b" not in nodes  # ★ LoRA 노드 X
        # KSampler model 본격 본 UNETLoader
        assert _node(wf, "8")["inputs"]["model"] == ["1", 0]

    def test_lora_branch(self) -> None:
        spec = spec_from_dict(
            "main_bjorn", MAIN_SCREEN_ASSETS["main_bjorn"]
        )
        wf = build_workflow_with_lora(spec, seed=12345)
        nodes = cast(dict[str, Any], wf["prompt"])
        assert "1b" in nodes  # ★ LoRA 노드 본격
        # KSampler model 본격 LoRA 경유
        assert _node(wf, "8")["inputs"]["model"] == ["1b", 0]
        # LoRA strength + name 본격
        assert _node(wf, "1b")["inputs"]["strength_model"] == 0.8
        assert _node(wf, "1b")["inputs"]["lora_name"] == BJORN_LORA_NAME

    def test_workflow_node_set_no_lora(self) -> None:
        spec = spec_from_dict("main_bg", MAIN_SCREEN_ASSETS["main_bg"])
        wf = build_workflow_with_lora(spec)
        nodes = cast(dict[str, Any], wf["prompt"])
        # ★ Flux dev 본격 10 노드 (★ LoRA X)
        assert set(nodes.keys()) == {
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        }
        # SaveImage prefix 본격
        assert (
            _node(wf, "10")["inputs"]["filename_prefix"]
            == "worldfork/ui_main_bg"
        )

    def test_workflow_node_set_with_lora(self) -> None:
        spec = spec_from_dict(
            "main_bjorn", MAIN_SCREEN_ASSETS["main_bjorn"]
        )
        wf = build_workflow_with_lora(spec)
        nodes = cast(dict[str, Any], wf["prompt"])
        # ★ Flux dev 11 노드 (★ LoRA 1b 추가)
        assert "1b" in nodes
        assert len(nodes) == 11

    def test_seed_applied(self) -> None:
        spec = spec_from_dict("main_bg", MAIN_SCREEN_ASSETS["main_bg"])
        wf = build_workflow_with_lora(spec, seed=99999)
        assert _node(wf, "8")["inputs"]["seed"] == 99999

    def test_flux_guidance_default(self) -> None:
        """FluxGuidance 본격 3.5 default (★ Flux dev pattern)."""
        spec = spec_from_dict("main_bg", MAIN_SCREEN_ASSETS["main_bg"])
        wf = build_workflow_with_lora(spec)
        assert _node(wf, "5")["inputs"]["guidance"] == 3.5

    def test_ksampler_25_steps(self) -> None:
        """KSampler 25-step 본격 (★ Flux dev, NOT Schnell 4-step)."""
        spec = spec_from_dict("main_bg", MAIN_SCREEN_ASSETS["main_bg"])
        wf = build_workflow_with_lora(spec)
        assert _node(wf, "8")["inputs"]["steps"] == 25
        assert _node(wf, "8")["inputs"]["cfg"] == 1.0


class TestPromptContent:
    def test_dark_fantasy_keywords(self) -> None:
        for name, data in MAIN_SCREEN_ASSETS.items():
            prompt = str(data["prompt"]).lower()
            keywords = ["dark", "fantasy", "warrior", "mage", "dungeon", "faerie"]
            assert any(kw in prompt for kw in keywords), (
                f"{name} 본격 다크 판타지 X"
            )

    def test_negative_low_quality(self) -> None:
        for name, data in MAIN_SCREEN_ASSETS.items():
            neg = str(data["negative_prompt"]).lower()
            assert "low quality" in neg, (
                f"{name} 본격 negative low quality X"
            )

    def test_bjorn_phase1_compat(self) -> None:
        """비요른 prompt가 Phase 1 spec 정합 (★ braided + axe)."""
        bjorn = MAIN_SCREEN_ASSETS["main_bjorn"]
        prompt = str(bjorn["prompt"]).lower()
        assert "braided" in prompt or "braids" in prompt
        assert "axe" in prompt

    def test_erwen_phase1_compat(self) -> None:
        """에르웬 prompt가 Phase 1 spec 정합 (★ faerie + wings)."""
        erwen = MAIN_SCREEN_ASSETS["main_erwen"]
        prompt = str(erwen["prompt"]).lower()
        assert "faerie" in prompt or "fairy" in prompt
        assert "wings" in prompt


class TestGameplayScreenAssets:
    """Phase 6b 본격 게임 플레이 화면 자료 검증."""

    def test_assets_count_four(self) -> None:
        assert len(GAMEPLAY_SCREEN_ASSETS) == 4
        assert set(GAMEPLAY_SCREEN_ASSETS) == {
            "gameplay_bg_crystal",
            "gameplay_bjorn_portrait",
            "gameplay_erwen_portrait",
            "gameplay_essence_effect",
        }

    def test_bg_crystal_1920x1080(self) -> None:
        bg = GAMEPLAY_SCREEN_ASSETS["gameplay_bg_crystal"]
        assert bg["width"] == 1920
        assert bg["height"] == 1080
        assert bg["lora"] is None
        prompt = str(bg["prompt"]).lower()
        assert "crystal" in prompt
        assert "teal" in prompt or "cyan" in prompt

    def test_bjorn_portrait_lora(self) -> None:
        bjorn = GAMEPLAY_SCREEN_ASSETS["gameplay_bjorn_portrait"]
        assert bjorn["lora"] == BJORN_LORA_NAME
        assert bjorn["lora_strength"] == 0.8
        prompt = str(bjorn["prompt"]).lower()
        assert "bjorn_warrior" in prompt
        assert "half-body" in prompt or "portrait" in prompt

    def test_erwen_portrait_prompt_only(self) -> None:
        erwen = GAMEPLAY_SCREEN_ASSETS["gameplay_erwen_portrait"]
        assert erwen["lora"] is None  # ★ Phase 1 + 6a 정합
        prompt = str(erwen["prompt"]).lower()
        assert "faerie" in prompt or "fairy" in prompt
        assert "wings" in prompt

    def test_essence_effect_vfx(self) -> None:
        """정수 VFX 본격 (★ 캐릭터 X)."""
        essence = GAMEPLAY_SCREEN_ASSETS["gameplay_essence_effect"]
        assert essence["lora"] is None
        neg = str(essence["negative_prompt"]).lower()
        assert "characters" in neg or "people" in neg
        prompt = str(essence["prompt"]).lower()
        assert "essence" in prompt or "orb" in prompt


class TestAllAssetDicts:
    """Phase 6 통합 dict 본격."""

    def test_dict_integration(self) -> None:
        assert "main_screen" in ALL_ASSET_DICTS
        assert "gameplay_screen" in ALL_ASSET_DICTS
        assert ALL_ASSET_DICTS["main_screen"] is MAIN_SCREEN_ASSETS
        assert ALL_ASSET_DICTS["gameplay_screen"] is GAMEPLAY_SCREEN_ASSETS

    def test_dict_phase_6_progress(self) -> None:
        """6a + 6b 본격 2/7 화면."""
        assert len(ALL_ASSET_DICTS) >= 2


class TestGameplayWorkflow:
    """Phase 6b workflow 본격 검증."""

    def test_bjorn_portrait_lora_workflow(self) -> None:
        from typing import cast

        spec = spec_from_dict(
            "gameplay_bjorn_portrait",
            GAMEPLAY_SCREEN_ASSETS["gameplay_bjorn_portrait"],
        )
        wf = build_workflow_with_lora(spec)
        nodes = cast(dict[str, Any], wf["prompt"])
        assert "1b" in nodes
        assert nodes["1b"]["inputs"]["lora_name"] == BJORN_LORA_NAME
        assert nodes["1b"]["inputs"]["strength_model"] == 0.8

    def test_erwen_portrait_no_lora(self) -> None:
        from typing import cast

        spec = spec_from_dict(
            "gameplay_erwen_portrait",
            GAMEPLAY_SCREEN_ASSETS["gameplay_erwen_portrait"],
        )
        wf = build_workflow_with_lora(spec)
        nodes = cast(dict[str, Any], wf["prompt"])
        assert "1b" not in nodes  # ★ prompt-only

    def test_portrait_dimensions(self) -> None:
        from typing import cast

        spec = spec_from_dict(
            "gameplay_bjorn_portrait",
            GAMEPLAY_SCREEN_ASSETS["gameplay_bjorn_portrait"],
        )
        wf = build_workflow_with_lora(spec)
        nodes = cast(dict[str, Any], wf["prompt"])
        assert nodes["7"]["inputs"]["width"] == 512
        assert nodes["7"]["inputs"]["height"] == 768


class TestPhase6Consistency:
    """Phase 6a + 6b 일관성 본격 검증."""

    def test_all_negative_low_quality(self) -> None:
        for asset_dict in (MAIN_SCREEN_ASSETS, GAMEPLAY_SCREEN_ASSETS):
            for name, data in asset_dict.items():
                neg = str(data["negative_prompt"]).lower()
                assert "low quality" in neg, f"{name}: negative 본격 X"

    def test_all_bjorn_use_lora(self) -> None:
        """6a + 6b 모든 bjorn 자료 LoRA 본격 정합."""
        for asset_dict in (MAIN_SCREEN_ASSETS, GAMEPLAY_SCREEN_ASSETS):
            for name, data in asset_dict.items():
                if "bjorn" in name:
                    assert data["lora"] == BJORN_LORA_NAME, (
                        f"{name}: LoRA 본격 X"
                    )

    def test_all_erwen_prompt_only(self) -> None:
        """6a + 6b 모든 erwen 자료 prompt-only 정합."""
        for asset_dict in (MAIN_SCREEN_ASSETS, GAMEPLAY_SCREEN_ASSETS):
            for name, data in asset_dict.items():
                if "erwen" in name:
                    assert data["lora"] is None, (
                        f"{name}: erwen prompt-only X"
                    )
