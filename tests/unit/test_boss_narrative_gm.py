"""audit-3 commit 3 — boss_narrative_gm 27B mock 단위 테스트."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from service.canon.boss_narrative import (
    BossNarrativeContext,
    BossTier,
)
from service.sim.boss_narrative_gm import (
    compose_boss_encounter_narrative_sync,
    compose_chamber_entry_narrative_sync,
)


def _mock_json_response(narrative: str) -> MagicMock:
    resp = MagicMock()
    resp.parsed = {"narrative": narrative}
    return resp


class TestComposeBossEncounterNarrative(unittest.TestCase):
    def _make_ctx(
        self,
        tier: BossTier = BossTier.NORMAL,
        is_variant: bool = False,
        visual_clues: list[str] | None = None,
    ) -> BossNarrativeContext:
        return BossNarrativeContext(
            rift_id="bloody_castle",
            rift_name="핏빛성채",
            sub_area_id="bc_ch5",
            boss_name="저주받은 기사 블라터",
            boss_grade=6,
            tier=tier,
            is_variant_rift=is_variant,
            visual_clues=visual_clues or [],
        )

    def test_normal_tier_calls_generate_json(self) -> None:
        ctx = self._make_ctx(tier=BossTier.NORMAL)
        mock_resp = _mock_json_response("예상한 대로 블라터가 등장했다.")

        with patch(
            "service.sim.boss_narrative_gm.get_qwen36_27b_q3"
        ) as mock_client_fn:
            mock_client = MagicMock()
            mock_client.generate_json.return_value = mock_resp
            mock_client_fn.return_value = mock_client

            result = compose_boss_encounter_narrative_sync(ctx)

        self.assertEqual(result, "예상한 대로 블라터가 등장했다.")
        mock_client.generate_json.assert_called_once()

    def test_hidden_tier_prompt_includes_visual_clues(self) -> None:
        ctx = self._make_ctx(
            tier=BossTier.HIDDEN,
            is_variant=True,
            visual_clues=["보스룸 문고리의 색상이 평소와 다르다."],
        )
        mock_resp = _mock_json_response("전례 없는 캠보르미어가 모습을 드러냈다.")

        with patch(
            "service.sim.boss_narrative_gm.get_qwen36_27b_q3"
        ) as mock_client_fn:
            mock_client = MagicMock()
            mock_client.generate_json.return_value = mock_resp
            mock_client_fn.return_value = mock_client

            result = compose_boss_encounter_narrative_sync(ctx)

        self.assertIn("전례 없는", result)
        # Verify the prompt contained visual clues
        call_args = mock_client.generate_json.call_args
        prompt = call_args[0][0]  # first positional arg = Prompt
        self.assertIn("문고리", prompt.user)

    def test_returns_string(self) -> None:
        ctx = self._make_ctx()
        mock_resp = _mock_json_response("보스가 등장했다.")

        with patch(
            "service.sim.boss_narrative_gm.get_qwen36_27b_q3"
        ) as mock_client_fn:
            mock_client = MagicMock()
            mock_client.generate_json.return_value = mock_resp
            mock_client_fn.return_value = mock_client

            result = compose_boss_encounter_narrative_sync(ctx)

        self.assertIsInstance(result, str)


class TestComposeChamberEntryNarrative(unittest.TestCase):
    def test_calls_27b_and_returns_narrative(self) -> None:
        mock_resp = _mock_json_response("외곽 검문소에 들어섰다.")

        with patch(
            "service.sim.boss_narrative_gm.get_qwen36_27b_q3"
        ) as mock_client_fn:
            mock_client = MagicMock()
            mock_client.generate_json.return_value = mock_resp
            mock_client_fn.return_value = mock_client

            result = compose_chamber_entry_narrative_sync(
                rift_id="bloody_castle",
                sub_area_id="bc_ch1",
                sub_area_name="외곽 검문소",
                is_variant_rift=False,
            )

        self.assertEqual(result, "외곽 검문소에 들어섰다.")

    def test_variant_rift_prompt_includes_visual_clues(self) -> None:
        mock_resp = _mock_json_response("문고리 색상이 이상하다.")

        with patch(
            "service.sim.boss_narrative_gm.get_qwen36_27b_q3"
        ) as mock_client_fn:
            mock_client = MagicMock()
            mock_client.generate_json.return_value = mock_resp
            mock_client_fn.return_value = mock_client

            compose_chamber_entry_narrative_sync(
                rift_id="bloody_castle",
                sub_area_id="bc_ch5",
                sub_area_name="영주성 악마 숭배실",
                is_variant_rift=True,
            )

        call_args = mock_client.generate_json.call_args
        prompt = call_args[0][0]
        self.assertIn("문고리", prompt.user)

    def test_uses_rift_name_mapping(self) -> None:
        mock_resp = _mock_json_response("빙하굴에 들어섰다.")

        with patch(
            "service.sim.boss_narrative_gm.get_qwen36_27b_q3"
        ) as mock_client_fn:
            mock_client = MagicMock()
            mock_client.generate_json.return_value = mock_resp
            mock_client_fn.return_value = mock_client

            compose_chamber_entry_narrative_sync(
                rift_id="glacier_cave",
                sub_area_id="gc_ch1",
                sub_area_name="동굴 입구",
                is_variant_rift=False,
            )

        call_args = mock_client.generate_json.call_args
        prompt = call_args[0][0]
        self.assertIn("빙하굴", prompt.user)


if __name__ == "__main__":
    unittest.main()
