"""audit-3 commit 3 — handle_move_chamber 단위 테스트."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_move_chamber


def _make_ctx(
    rift_id: str = "bloody_castle",
    rift_sub_area: str = "bc_ch1",
    rift_is_variant: bool = False,
    user_input: str = "다음 챔버로 이동",
) -> ActionContext:
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="핏빛성채 (균열 내부)",
        rift_id=rift_id,
        rift_sub_area=rift_sub_area,
        rift_is_variant=rift_is_variant,
        user_input=user_input,
    )


class TestHandleMoveChamberNoRift(unittest.TestCase):
    def test_no_rift_id_returns_failure(self) -> None:
        ctx = ActionContext(
            current_hp=100, max_hp=100, inventory=[], location="1층 입구"
        )
        result = asyncio.run(handle_move_chamber(ctx))
        self.assertFalse(result.success)
        self.assertEqual(result.fail_reason, "no_rift_context")

    def test_unknown_rift_id_returns_failure(self) -> None:
        ctx = ActionContext(
            current_hp=100,
            max_hp=100,
            inventory=[],
            location="",
            rift_id="unknown_rift",
        )
        result = asyncio.run(handle_move_chamber(ctx))
        self.assertFalse(result.success)


class TestHandleMoveChamberNormalPath(unittest.TestCase):
    def _patch_chamber_narrative(self, narrative: str = "챔버에 진입했다.") -> object:
        return patch(
            "service.sim.boss_narrative_gm.compose_chamber_entry_narrative_sync",
            return_value=narrative,
        )

    def _patch_boss_narrative(self, narrative: str = "보스가 등장했다.") -> object:
        return patch(
            "service.sim.boss_narrative_gm.compose_boss_encounter_narrative_sync",
            return_value=narrative,
        )

    def test_moves_to_next_chamber(self) -> None:
        ctx = _make_ctx(rift_sub_area="bc_ch1")
        with self._patch_chamber_narrative():
            result = asyncio.run(handle_move_chamber(ctx))
        self.assertTrue(result.success)
        assert result.rift_transition is not None
        self.assertEqual(result.rift_transition["action"], "move_to_chamber")
        self.assertEqual(result.rift_transition["rift_sub_area"], "bc_ch2")

    def test_boss_keyword_goes_to_boss_chamber(self) -> None:
        ctx = _make_ctx(rift_sub_area="bc_ch1", user_input="보스룸으로 이동한다")
        with self._patch_boss_narrative("보스 등장"):
            result = asyncio.run(handle_move_chamber(ctx))
        self.assertTrue(result.success)
        assert result.rift_transition is not None
        self.assertEqual(result.rift_transition["rift_sub_area"], "bc_ch5")

    def test_boss_chamber_uses_boss_narrative(self) -> None:
        ctx = _make_ctx(
            rift_sub_area="bc_ch4",  # bc_ch4 → bc_ch5 (boss)
            user_input="다음 챔버로 이동",
        )
        with (
            self._patch_boss_narrative("블라터가 등장했다."),
            self._patch_chamber_narrative(),
        ):
            result = asyncio.run(handle_move_chamber(ctx))

        self.assertEqual(result.narrative, "블라터가 등장했다.")

    def test_variant_boss_name_selected(self) -> None:
        ctx = _make_ctx(
            rift_sub_area="bc_ch4",
            rift_is_variant=True,
            user_input="보스룸으로 이동",
        )
        with patch(
            "service.sim.boss_narrative_gm.compose_boss_encounter_narrative_sync",
            return_value="캠보르미어 등장",
        ) as mock_boss:
            asyncio.run(handle_move_chamber(ctx))

        call_kwargs = mock_boss.call_args[0][0]  # BossNarrativeContext
        self.assertIn("캠보르미어", call_kwargs.boss_name)

    def test_non_variant_uses_normal_boss_name(self) -> None:
        ctx = _make_ctx(
            rift_sub_area="bc_ch4",
            rift_is_variant=False,
            user_input="보스룸으로 이동",
        )
        with patch(
            "service.sim.boss_narrative_gm.compose_boss_encounter_narrative_sync",
            return_value="블라터 등장",
        ) as mock_boss:
            asyncio.run(handle_move_chamber(ctx))

        call_kwargs = mock_boss.call_args[0][0]  # BossNarrativeContext
        self.assertIn("블라터", call_kwargs.boss_name)

    def test_fallback_on_exception(self) -> None:
        ctx = _make_ctx(rift_sub_area="bc_ch1")
        with patch(
            "service.sim.boss_narrative_gm.compose_chamber_entry_narrative_sync",
            side_effect=Exception("LLM unavailable"),
        ):
            result = asyncio.run(handle_move_chamber(ctx))
        self.assertTrue(result.success)
        self.assertIn("이동했다", result.narrative)


if __name__ == "__main__":
    unittest.main()
