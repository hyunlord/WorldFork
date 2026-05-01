"""W1 D7: CATEGORY_MAPPING 확장 + ux 카테고리 단위 테스트.

W1 D6 Round 4 발견 카테고리 (AI/prompt/IP/clarity/pacing/worldbuilding ...)
모두 매핑되는지 확인.
"""

from tools.ai_playtester.seed_converter import (
    CATEGORY_MAPPING,
    EXPECTED_BEHAVIORS_BY_CATEGORY,
    _map_category,
)


class TestExtendedMappings:
    def test_ai_variants(self) -> None:
        """W1 D6에서 발견된 AI 변형 (5건)."""
        assert _map_category("ai") == "ai_breakout"
        assert _map_category("prompt") == "ai_breakout"
        assert _map_category("prompt_injection") == "ai_breakout"
        assert _map_category("prompt_injection_resistance") == "ai_breakout"
        assert _map_category("meta_question") == "ai_breakout"
        assert _map_category("self_disclosure") == "ai_breakout"

    def test_ip_variants(self) -> None:
        """W1 D6에서 발견된 IP 변형 (4건)."""
        assert _map_category("ip") == "ip_leakage"
        assert _map_category("intellectual_property") == "ip_leakage"

    def test_world_variants(self) -> None:
        assert _map_category("worldbuilding") == "world_consistency"
        assert _map_category("space_rules") == "world_consistency"
        assert _map_category("anachronism") == "world_consistency"
        assert _map_category("magic_system") == "world_consistency"
        assert _map_category("context_loss") == "world_consistency"

    def test_korean_variants(self) -> None:
        assert _map_category("speech_style") == "korean_quality"
        assert _map_category("honorifics") == "korean_quality"
        assert _map_category("language") == "korean_quality"
        assert _map_category("language_mixing") == "korean_quality"
        assert _map_category("verbose_clueless") == "korean_quality"
        assert _map_category("외국어혼입") == "korean_quality"

    def test_ux_category_new(self) -> None:
        """W1 D7 신규 카테고리."""
        assert _map_category("ux") == "ux"
        assert _map_category("ui") == "ux"
        assert _map_category("clarity") == "ux"
        assert _map_category("pacing") == "ux"
        assert _map_category("navigation") == "ux"
        assert _map_category("too_many_choices") == "ux"
        assert _map_category("onboarding") == "ux"
        assert _map_category("feedback") == "ux"
        assert _map_category("repetitive_intro") == "ux"
        # broken_ux 이동 (general → ux)
        assert _map_category("broken_ux") == "ux"

    def test_persona_variants(self) -> None:
        assert _map_category("personality") == "persona_consistency"

    def test_unknown_falls_to_general(self) -> None:
        """모르는 카테고리 → general."""
        assert _map_category("totally_unknown_xyz") == "general"

    def test_case_insensitive(self) -> None:
        """대소문자 무관."""
        assert _map_category("AI") == "ai_breakout"
        assert _map_category("IP") == "ip_leakage"
        assert _map_category("Verbose") == "korean_quality"
        assert _map_category("UX") == "ux"


class TestExpectedBehaviors:
    def test_ux_expected(self) -> None:
        ux = EXPECTED_BEHAVIORS_BY_CATEGORY["ux"]
        assert ux.get("clear_choices") is True
        assert ux.get("no_navigation_loss") is True
        assert ux.get("appropriate_pacing") is True

    def test_all_target_categories_have_expected(self) -> None:
        """매핑 결과 모든 카테고리에 expected 정의."""
        target_categories = set(CATEGORY_MAPPING.values())
        for cat in target_categories:
            assert cat in EXPECTED_BEHAVIORS_BY_CATEGORY, (
                f"Missing expected_behaviors for '{cat}'"
            )

    def test_mapping_size_w1_d7(self) -> None:
        """W1 D7: 매핑 크게 확장 (16 → 50+)."""
        assert len(CATEGORY_MAPPING) >= 50

    def test_all_target_categories_count(self) -> None:
        """7 target categories: persona/korean/ip/world/ai/ux/general."""
        target = set(CATEGORY_MAPPING.values())
        assert target == {
            "persona_consistency",
            "korean_quality",
            "ip_leakage",
            "world_consistency",
            "ai_breakout",
            "ux",
            "general",
        }
