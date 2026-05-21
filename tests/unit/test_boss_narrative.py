"""audit-3 commit 3 — boss_narrative 순수 로직 단위 테스트."""

from __future__ import annotations

import unittest

from service.canon.boss_narrative import (
    SYSTEM_MESSAGE_TEMPLATES,
    VARIANT_VISUAL_CLUES,
    BossTier,
    build_visual_clues,
    determine_boss_tier,
    format_system_message,
)


class TestDetermineBossTier(unittest.TestCase):
    def test_cambormieure_is_hidden(self) -> None:
        tier = determine_boss_tier("뱀파이어 공작 캠보르미어", True, "bloody_castle")
        self.assertEqual(tier, BossTier.HIDDEN)

    def test_cambormieure_short_is_hidden(self) -> None:
        tier = determine_boss_tier("캠보르미어", True, "bloody_castle")
        self.assertEqual(tier, BossTier.HIDDEN)

    def test_kirdwei_is_hidden(self) -> None:
        tier = determine_boss_tier("타락한 짐승 키르뒤", True, "glacier_cave")
        self.assertEqual(tier, BossTier.HIDDEN)

    def test_normal_boss_is_normal(self) -> None:
        tier = determine_boss_tier("저주받은 기사 블라터", False, "bloody_castle")
        self.assertEqual(tier, BossTier.NORMAL)

    def test_variant_non_hidden_is_variant(self) -> None:
        tier = determine_boss_tier("상위 변이종 예티", True, "glacier_cave")
        self.assertEqual(tier, BossTier.VARIANT)

    def test_normal_boss_with_variant_false_is_normal(self) -> None:
        tier = determine_boss_tier("폭군 타룬바스", False, "glacier_cave")
        self.assertEqual(tier, BossTier.NORMAL)


class TestBuildVisualClues(unittest.TestCase):
    def test_non_variant_returns_empty(self) -> None:
        clues = build_visual_clues("bloody_castle", False)
        self.assertEqual(clues, [])

    def test_bloody_castle_variant_returns_clues(self) -> None:
        clues = build_visual_clues("bloody_castle", True)
        self.assertTrue(len(clues) > 0)
        self.assertTrue(any("문고리" in c or "관짝" in c for c in clues))

    def test_glacier_cave_variant_returns_clues(self) -> None:
        clues = build_visual_clues("glacier_cave", True)
        self.assertTrue(len(clues) > 0)
        self.assertTrue(any("시체산" in c or "얼음" in c for c in clues))

    def test_unknown_rift_variant_returns_empty(self) -> None:
        clues = build_visual_clues("unknown_rift", True)
        self.assertEqual(clues, [])

    def test_returns_copy_not_reference(self) -> None:
        clues1 = build_visual_clues("bloody_castle", True)
        clues2 = build_visual_clues("bloody_castle", True)
        clues1.append("extra")
        self.assertNotIn("extra", clues2)


class TestFormatSystemMessage(unittest.TestCase):
    def test_normal_tier_message(self) -> None:
        msg = format_system_message(BossTier.NORMAL, "핏빛성채", "블라터")
        self.assertIn("수호자가 모습을 드러냅니다", msg)
        self.assertIn("핏빛성채", msg)
        self.assertIn("「", msg)

    def test_hidden_tier_message(self) -> None:
        msg = format_system_message(BossTier.HIDDEN, "핏빛성채", "캠보르미어")
        self.assertIn("주인이", msg)
        self.assertIn("핏빛성채", msg)

    def test_variant_tier_message_includes_boss_name(self) -> None:
        msg = format_system_message(BossTier.VARIANT, "빙하굴", "상위 변이종 예티")
        self.assertIn("상위 변이종 예티", msg)

    def test_system_message_templates_all_tiers_defined(self) -> None:
        for tier in BossTier:
            self.assertIn(tier, SYSTEM_MESSAGE_TEMPLATES)


class TestVariantVisualClues(unittest.TestCase):
    def test_all_rift_ids_have_clues(self) -> None:
        for rift_id in ("bloody_castle", "glacier_cave", "green_mine", "iron_tomb"):
            self.assertIn(rift_id, VARIANT_VISUAL_CLUES)
            self.assertTrue(len(VARIANT_VISUAL_CLUES[rift_id]) > 0)


if __name__ == "__main__":
    unittest.main()
