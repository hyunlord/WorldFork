"""tools/visual/ui_assets 본격 단위 검증 (★ Phase 6a)."""

from __future__ import annotations

from typing import Any, cast

from tools.visual.ui_assets import (
    ALL_ASSET_DICTS,
    BJORN_LORA_NAME,
    CHARACTER_SHEET_ASSETS,
    COMBAT_ASSETS,
    DIALOGUE_ASSETS,
    GAMEPLAY_SCREEN_ASSETS,
    MAIN_SCREEN_ASSETS,
    RIFT_ENTRY_ASSETS,
    START_MENU_ASSETS,
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
        for asset_dict in (
            MAIN_SCREEN_ASSETS,
            GAMEPLAY_SCREEN_ASSETS,
            CHARACTER_SHEET_ASSETS,
            RIFT_ENTRY_ASSETS,
            COMBAT_ASSETS,
            DIALOGUE_ASSETS,
            START_MENU_ASSETS,
        ):
            for name, data in asset_dict.items():
                neg = str(data["negative_prompt"]).lower()
                assert "low quality" in neg, f"{name}: negative 본격 X"

    def test_all_bjorn_use_lora(self) -> None:
        """6a+6b+6c 모든 bjorn 자료 LoRA 본격 정합."""
        for asset_dict in (
            MAIN_SCREEN_ASSETS,
            GAMEPLAY_SCREEN_ASSETS,
            CHARACTER_SHEET_ASSETS,
            RIFT_ENTRY_ASSETS,
            COMBAT_ASSETS,
            DIALOGUE_ASSETS,
            START_MENU_ASSETS,
        ):
            for name, data in asset_dict.items():
                if "bjorn" in name:
                    assert data["lora"] == BJORN_LORA_NAME, (
                        f"{name}: LoRA 본격 X"
                    )

    def test_all_erwen_prompt_only(self) -> None:
        """6a+6b+6c 모든 erwen 자료 prompt-only 정합."""
        for asset_dict in (
            MAIN_SCREEN_ASSETS,
            GAMEPLAY_SCREEN_ASSETS,
            CHARACTER_SHEET_ASSETS,
            RIFT_ENTRY_ASSETS,
            COMBAT_ASSETS,
            DIALOGUE_ASSETS,
            START_MENU_ASSETS,
        ):
            for name, data in asset_dict.items():
                if "erwen" in name:
                    assert data["lora"] is None, (
                        f"{name}: erwen prompt-only X"
                    )


class TestCharacterSheetAssets:
    """Phase 6c 캐릭터 시트 자료 검증."""

    def test_assets_count_three(self) -> None:
        assert len(CHARACTER_SHEET_ASSETS) == 3
        assert set(CHARACTER_SHEET_ASSETS) == {
            "character_bjorn_full",
            "character_erwen_full",
            "character_essence_grid",
        }

    def test_bjorn_full_lora_full_body(self) -> None:
        bjorn = CHARACTER_SHEET_ASSETS["character_bjorn_full"]
        assert bjorn["width"] == 1024
        assert bjorn["height"] == 1536  # ★ 풀바디
        assert bjorn["lora"] == BJORN_LORA_NAME
        assert bjorn["lora_strength"] == 0.8
        prompt = str(bjorn["prompt"]).lower()
        assert "full body" in prompt or "head to feet" in prompt
        neg = str(bjorn["negative_prompt"]).lower()
        assert "cropped" in neg
        assert "half body" in neg

    def test_erwen_full_prompt_only(self) -> None:
        erwen = CHARACTER_SHEET_ASSETS["character_erwen_full"]
        assert erwen["lora"] is None
        assert erwen["width"] == 1024
        assert erwen["height"] == 1536
        prompt = str(erwen["prompt"]).lower()
        assert "faerie" in prompt or "elven" in prompt
        assert "silver" in prompt

    def test_essence_grid_five_colors(self) -> None:
        essence = CHARACTER_SHEET_ASSETS["character_essence_grid"]
        assert essence["lora"] is None
        assert essence["width"] == 1024
        assert essence["height"] == 1024
        prompt = str(essence["prompt"]).lower()
        for color in (
            "earth brown",
            "teal",
            "blue-gray",
            "blood-red",
            "golden",
        ):
            assert color in prompt, f"본격 정수 색 X: {color}"
        neg = str(essence["negative_prompt"]).lower()
        assert "characters" in neg or "people" in neg


class TestAllAssetDictsExtended:
    """Phase 6 통합 dict 본격 확장 (★ 6c identity 본격)."""

    def test_character_sheet_identity(self) -> None:
        assert ALL_ASSET_DICTS["character_sheet"] is CHARACTER_SHEET_ASSETS

    def test_rift_entry_identity(self) -> None:
        assert ALL_ASSET_DICTS["rift_entry"] is RIFT_ENTRY_ASSETS


class TestCharacterSheetWorkflow:
    """Phase 6c workflow LoRA 분기."""

    def test_bjorn_full_lora_workflow(self) -> None:
        from typing import cast

        spec = spec_from_dict(
            "character_bjorn_full",
            CHARACTER_SHEET_ASSETS["character_bjorn_full"],
        )
        wf = build_workflow_with_lora(spec)
        nodes = cast(dict[str, Any], wf["prompt"])
        assert "1b" in nodes
        assert nodes["1b"]["inputs"]["lora_name"] == BJORN_LORA_NAME
        assert nodes["7"]["inputs"]["width"] == 1024
        assert nodes["7"]["inputs"]["height"] == 1536

    def test_erwen_full_no_lora(self) -> None:
        from typing import cast

        spec = spec_from_dict(
            "character_erwen_full",
            CHARACTER_SHEET_ASSETS["character_erwen_full"],
        )
        wf = build_workflow_with_lora(spec)
        nodes = cast(dict[str, Any], wf["prompt"])
        assert "1b" not in nodes


class TestRiftEntryAssets:
    """Phase 6d 균열 진입 자료 검증."""

    def test_assets_count_four(self) -> None:
        assert len(RIFT_ENTRY_ASSETS) == 4
        assert set(RIFT_ENTRY_ASSETS) == {
            "rift_bloodcastle",
            "rift_glacier",
            "rift_greenmine",
            "rift_steeltomb",
        }

    def test_all_lora_none(self) -> None:
        """4 균열 모두 LoRA X (★ 환경 본격)."""
        for name, data in RIFT_ENTRY_ASSETS.items():
            assert data["lora"] is None, f"{name}: LoRA 본격 X"

    def test_all_1024_square(self) -> None:
        for _name, data in RIFT_ENTRY_ASSETS.items():
            assert data["width"] == 1024
            assert data["height"] == 1024

    def test_bloodcastle_content(self) -> None:
        rift = RIFT_ENTRY_ASSETS["rift_bloodcastle"]
        prompt = str(rift["prompt"]).lower()
        assert "blood" in prompt
        assert "necronomicon" in prompt
        assert "weeping" in prompt or "goddess" in prompt
        assert "pentagram" in prompt

    def test_glacier_content(self) -> None:
        rift = RIFT_ENTRY_ASSETS["rift_glacier"]
        prompt = str(rift["prompt"]).lower()
        assert "ice" in prompt or "frozen" in prompt
        assert "cyan" in prompt or "blue" in prompt
        assert "cold" in prompt or "frost" in prompt

    def test_greenmine_content(self) -> None:
        rift = RIFT_ENTRY_ASSETS["rift_greenmine"]
        prompt = str(rift["prompt"]).lower()
        assert "green" in prompt or "emerald" in prompt
        assert "mine" in prompt
        assert "toxic" in prompt or "moss" in prompt

    def test_steeltomb_content(self) -> None:
        rift = RIFT_ENTRY_ASSETS["rift_steeltomb"]
        prompt = str(rift["prompt"]).lower()
        assert "steel" in prompt
        assert (
            "tomb" in prompt
            or "sarcophagi" in prompt
            or "mausoleum" in prompt
        )

    def test_all_dark_fantasy(self) -> None:
        for name, data in RIFT_ENTRY_ASSETS.items():
            prompt = str(data["prompt"]).lower()
            assert "dark fantasy" in prompt, f"{name}: 다크 판타지 X"
            neg = str(data["negative_prompt"]).lower()
            assert "characters" in neg, f"{name}: negative 캐릭터 X"


class TestRiftEntryWorkflow:
    """Phase 6d workflow LoRA X 검증."""

    def test_all_no_lora_workflow(self) -> None:
        from typing import cast

        for name in RIFT_ENTRY_ASSETS:
            spec = spec_from_dict(name, RIFT_ENTRY_ASSETS[name])
            wf = build_workflow_with_lora(spec)
            nodes = cast(dict[str, Any], wf["prompt"])
            assert "1b" not in nodes, f"{name}: LoRA 노드 본격 X"

    def test_all_1024_workflow(self) -> None:
        from typing import cast

        for name in RIFT_ENTRY_ASSETS:
            spec = spec_from_dict(name, RIFT_ENTRY_ASSETS[name])
            wf = build_workflow_with_lora(spec)
            nodes = cast(dict[str, Any], wf["prompt"])
            assert nodes["7"]["inputs"]["width"] == 1024
            assert nodes["7"]["inputs"]["height"] == 1024


class TestCombatAssets:
    """Phase 6e 전투 자료 검증."""

    def test_assets_count_five(self) -> None:
        assert len(COMBAT_ASSETS) == 5
        assert set(COMBAT_ASSETS) == {
            "combat_bjorn_action",
            "combat_erwen_casting",
            "combat_monster_blade_wolf",
            "combat_vfx_axe_strike",
            "combat_vfx_magic_missile",
        }

    def test_bjorn_action_lora(self) -> None:
        bjorn = COMBAT_ASSETS["combat_bjorn_action"]
        assert bjorn["lora"] == BJORN_LORA_NAME
        assert bjorn["lora_strength"] == 0.8
        prompt = str(bjorn["prompt"]).lower()
        assert "action" in prompt or "swing" in prompt
        assert "battle" in prompt or "combat" in prompt
        neg = str(bjorn["negative_prompt"]).lower()
        assert "static" in neg or "calm" in neg

    def test_erwen_casting_prompt_only(self) -> None:
        erwen = COMBAT_ASSETS["combat_erwen_casting"]
        assert erwen["lora"] is None
        prompt = str(erwen["prompt"]).lower()
        assert "spell" in prompt or "casting" in prompt
        assert "silver" in prompt

    def test_blade_wolf_content(self) -> None:
        wolf = COMBAT_ASSETS["combat_monster_blade_wolf"]
        assert wolf["lora"] is None
        prompt = str(wolf["prompt"]).lower()
        assert "blade" in prompt
        assert "wolf" in prompt
        assert "9th grade" in prompt or "9th-grade" in prompt
        neg = str(wolf["negative_prompt"]).lower()
        assert "cute" in neg
        assert "friendly" in neg
        assert "human" in neg

    def test_vfx_isolated(self) -> None:
        for name in ("combat_vfx_axe_strike", "combat_vfx_magic_missile"):
            vfx = COMBAT_ASSETS[name]
            assert vfx["lora"] is None
            assert vfx["width"] == 1024
            assert vfx["height"] == 1024
            neg = str(vfx["negative_prompt"]).lower()
            assert "characters" in neg or "people" in neg


class TestPhase6eIdentities:
    """Phase 6e identity 본격."""

    def test_combat_identity(self) -> None:
        assert ALL_ASSET_DICTS["combat"] is COMBAT_ASSETS


class TestDialogueAssets:
    """Phase 6f 대화/이벤트 자료 검증."""

    def test_assets_count_four(self) -> None:
        assert len(DIALOGUE_ASSETS) == 4
        assert set(DIALOGUE_ASSETS) == {
            "dialogue_message_stone",
            "dialogue_other_explorer_male",
            "dialogue_other_explorer_female",
            "dialogue_ancient_stone",
        }

    def test_message_stone_content(self) -> None:
        stone = DIALOGUE_ASSETS["dialogue_message_stone"]
        assert stone["lora"] is None
        assert stone["width"] == 1024
        assert stone["height"] == 1024
        prompt = str(stone["prompt"]).lower()
        assert "message stone" in prompt or "communication" in prompt
        assert "runic" in prompt or "rune" in prompt
        assert "blue-white" in prompt or "ethereal" in prompt
        neg = str(stone["negative_prompt"]).lower()
        assert "characters" in neg

    def test_other_explorer_male_separation(self) -> None:
        """다른 탐사대 남성 — 비요른과 분리 명시."""
        male = DIALOGUE_ASSETS["dialogue_other_explorer_male"]
        assert male["lora"] is None
        assert male["width"] == 768
        assert male["height"] == 1024
        prompt = str(male["prompt"]).lower()
        assert "male" in prompt
        assert "explorer" in prompt or "adventurer" in prompt
        neg = str(male["negative_prompt"]).lower()
        assert "bjorn" in neg
        assert "viking" in neg or "barbarian" in neg

    def test_other_explorer_female_separation(self) -> None:
        """다른 탐사대 여성 — 에르웬과 분리 명시."""
        female = DIALOGUE_ASSETS["dialogue_other_explorer_female"]
        assert female["lora"] is None
        prompt = str(female["prompt"]).lower()
        assert "female" in prompt
        assert (
            "explorer" in prompt
            or "adventurer" in prompt
            or "rogue" in prompt
        )
        neg = str(female["negative_prompt"]).lower()
        assert "erwen" in neg
        assert "elven" in neg or "silver hair" in neg

    def test_ancient_stone_content(self) -> None:
        stone = DIALOGUE_ASSETS["dialogue_ancient_stone"]
        assert stone["lora"] is None
        prompt = str(stone["prompt"]).lower()
        assert "monolith" in prompt or "stone" in prompt
        assert "runic" in prompt or "glyph" in prompt
        assert (
            "offering" in prompt
            or "tribute" in prompt
            or "bowl" in prompt
        )


class TestPhase6fIdentities:
    """Phase 6f identity."""

    def test_dialogue_identity(self) -> None:
        assert ALL_ASSET_DICTS["dialogue"] is DIALOGUE_ASSETS


class TestStartMenuAssets:
    """Phase 6g 시작 메뉴 자료 검증 (★ minimal 마무리)."""

    def test_assets_count_one(self) -> None:
        assert len(START_MENU_ASSETS) == 1
        assert set(START_MENU_ASSETS) == {"start_menu_bg"}

    def test_start_menu_bg_external_view(self) -> None:
        bg = START_MENU_ASSETS["start_menu_bg"]
        assert bg["lora"] is None
        assert bg["width"] == 1920
        assert bg["height"] == 1080
        prompt = str(bg["prompt"]).lower()
        # 외부 시점 본격 (★ 6a 내부와 차별화)
        assert "entrance" in prompt or "gateway" in prompt
        assert "outside" in prompt or "mountainside" in prompt
        # 첫 진입 분위기
        assert (
            "ominous" in prompt
            or "foreboding" in prompt
            or "dark" in prompt
        )
        neg = str(bg["negative_prompt"]).lower()
        assert "interior" in neg or "characters" in neg


class TestAllAssetDictsPhase6gMarmugi:
    """Phase 6 7/7 마무리 본격 검증."""

    def test_seven_phase_integration(self) -> None:
        assert set(ALL_ASSET_DICTS) == {
            "main_screen",
            "gameplay_screen",
            "character_sheet",
            "rift_entry",
            "combat",
            "dialogue",
            "start_menu",
        }
        assert len(ALL_ASSET_DICTS) == 7

    def test_total_assets_twenty_four(self) -> None:
        """6a 3 + 6b 4 + 6c 3 + 6d 4 + 6e 5 + 6f 4 + 6g 1 = 24."""
        total = sum(len(d) for d in ALL_ASSET_DICTS.values())
        assert total == 24

    def test_phase_per_count(self) -> None:
        expected = {
            "main_screen": 3,
            "gameplay_screen": 4,
            "character_sheet": 3,
            "rift_entry": 4,
            "combat": 5,
            "dialogue": 4,
            "start_menu": 1,
        }
        for phase, count in expected.items():
            assert len(ALL_ASSET_DICTS[phase]) == count, (
                f"{phase} count X"
            )

    def test_start_menu_identity(self) -> None:
        assert ALL_ASSET_DICTS["start_menu"] is START_MENU_ASSETS


class TestStartMenuWorkflow:
    """Phase 6g workflow LoRA X."""

    def test_no_lora_workflow(self) -> None:
        from typing import cast

        spec = spec_from_dict(
            "start_menu_bg", START_MENU_ASSETS["start_menu_bg"]
        )
        wf = build_workflow_with_lora(spec)
        nodes = cast(dict[str, Any], wf["prompt"])
        assert "1b" not in nodes


class TestPhase6Marmugi:
    """Phase 6 7/7 본격 마무리 일관성."""

    def test_bjorn_lora_count(self) -> None:
        """LoRA bjorn use count ≥ 4 (★ 6a + 6b + 6c + 6e)."""
        count = 0
        for asset_dict in ALL_ASSET_DICTS.values():
            for name, data in asset_dict.items():
                if "bjorn" in name:
                    count += 1
                    assert data["lora"] == BJORN_LORA_NAME, (
                        f"{name}: LoRA X"
                    )
        assert count >= 4, f"bjorn count {count} < 4"

    def test_erwen_prompt_only_count(self) -> None:
        """erwen prompt-only count ≥ 4 (★ Phase 1+6a+6b+6c+6e)."""
        count = 0
        for asset_dict in ALL_ASSET_DICTS.values():
            for name, data in asset_dict.items():
                if "erwen" in name:
                    count += 1
                    assert data["lora"] is None, f"{name}: prompt-only X"
        assert count >= 4, f"erwen count {count} < 4"

    def test_all_required_fields(self) -> None:
        """모든 자료 dict 필수 필드 본격."""
        required = {
            "filename_prefix",
            "width",
            "height",
            "prompt",
            "negative_prompt",
            "lora",
        }
        for asset_dict in ALL_ASSET_DICTS.values():
            for name, data in asset_dict.items():
                missing = required - data.keys()
                assert not missing, f"{name}: 필드 누락 {missing}"


class TestDialogueWorkflow:
    """Phase 6f workflow 모두 LoRA X."""

    def test_all_no_lora_workflow(self) -> None:
        from typing import cast

        for name in DIALOGUE_ASSETS:
            spec = spec_from_dict(name, DIALOGUE_ASSETS[name])
            wf = build_workflow_with_lora(spec)
            nodes = cast(dict[str, Any], wf["prompt"])
            assert "1b" not in nodes, f"{name}: LoRA 노드 X"


class TestCombatWorkflow:
    """Phase 6e LoRA action / 나머지 prompt-only."""

    def test_bjorn_action_lora_workflow(self) -> None:
        from typing import cast

        spec = spec_from_dict(
            "combat_bjorn_action",
            COMBAT_ASSETS["combat_bjorn_action"],
        )
        wf = build_workflow_with_lora(spec)
        nodes = cast(dict[str, Any], wf["prompt"])
        assert "1b" in nodes
        assert nodes["1b"]["inputs"]["lora_name"] == BJORN_LORA_NAME

    def test_others_no_lora(self) -> None:
        from typing import cast

        for name in (
            "combat_erwen_casting",
            "combat_monster_blade_wolf",
            "combat_vfx_axe_strike",
            "combat_vfx_magic_missile",
        ):
            spec = spec_from_dict(name, COMBAT_ASSETS[name])
            wf = build_workflow_with_lora(spec)
            nodes = cast(dict[str, Any], wf["prompt"])
            assert "1b" not in nodes, f"{name}: LoRA 노드 X"
