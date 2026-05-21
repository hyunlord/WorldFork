"""audit-3 commit 2 — trigger_spawn rift_sub_area 우선순위 단위 테스트."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from service.canon.spawn import SpawnTable
from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS
from service.game.state_v2 import RiftChamberType
from service.sim.spawn_trigger import _find_rift_sub_area, trigger_spawn


def _make_spawn_table() -> SpawnTable:
    facts = MagicMock()
    facts.locations = []
    facts.characters = []
    facts.races = []
    return SpawnTable(facts)


class TestFindRiftSubArea(unittest.TestCase):
    def test_finds_matching_sub_area(self) -> None:
        result = _find_rift_sub_area("bc_ch1", FLOOR1_RIFT_DEFS)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.id, "bc_ch1")

    def test_returns_none_for_unknown_id(self) -> None:
        result = _find_rift_sub_area("xx_unknown", FLOOR1_RIFT_DEFS)
        self.assertIsNone(result)

    def test_finds_mid_boss_chamber(self) -> None:
        result = _find_rift_sub_area("bc_ch4", FLOOR1_RIFT_DEFS)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.chamber_type, RiftChamberType.MID_BOSS)

    def test_finds_glacier_cave_sub_area(self) -> None:
        result = _find_rift_sub_area("gc_ch1", FLOOR1_RIFT_DEFS)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.id, "gc_ch1")


class TestTriggerSpawnRiftPriority(unittest.TestCase):
    def _patched_should_spawn(self) -> object:
        return patch(
            "service.sim.spawn_trigger.should_spawn",
            return_value=True,
        )

    def test_uses_rift_sub_area_monsters(self) -> None:
        table = _make_spawn_table()
        with self._patched_should_spawn():
            result = trigger_spawn(
                location_name="핏빛성채 (균열 내부)",
                location_type="rift",
                turn_count=5,
                last_spawn_turn=0,
                spawn_table=table,
                rift_sub_area="bc_ch1",
                rift_defs=FLOOR1_RIFT_DEFS,
            )
        self.assertTrue(len(result) > 0)
        name = result[0]["name"]
        # bc_ch1 monsters: 데드맨, 병사 데드맨, 지휘관 데드맨
        self.assertIn(name, ("데드맨", "병사 데드맨", "지휘관 데드맨"))

    def test_mid_boss_chamber_returns_boss(self) -> None:
        table = _make_spawn_table()
        with self._patched_should_spawn():
            result = trigger_spawn(
                location_name="핏빛성채 (균열 내부)",
                location_type="rift",
                turn_count=5,
                last_spawn_turn=0,
                spawn_table=table,
                rift_sub_area="bc_ch4",
                rift_defs=FLOOR1_RIFT_DEFS,
            )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "시체골렘")

    def test_no_rift_defs_falls_back_to_generic(self) -> None:
        table = _make_spawn_table()
        with self._patched_should_spawn():
            result = trigger_spawn(
                location_name="핏빛성채 (균열 내부)",
                location_type="rift",
                turn_count=5,
                last_spawn_turn=0,
                spawn_table=table,
                rift_sub_area="bc_ch1",
                rift_defs=None,
            )
        self.assertIsInstance(result, list)

    def test_unknown_sub_area_id_falls_back_to_generic(self) -> None:
        table = _make_spawn_table()
        with self._patched_should_spawn():
            result = trigger_spawn(
                location_name="핏빛성채 (균열 내부)",
                location_type="rift",
                turn_count=5,
                last_spawn_turn=0,
                spawn_table=table,
                rift_sub_area="xx_unknown",
                rift_defs=FLOOR1_RIFT_DEFS,
            )
        self.assertIsInstance(result, list)

    def test_no_spawn_when_should_spawn_false(self) -> None:
        table = _make_spawn_table()
        with patch("service.sim.spawn_trigger.should_spawn", return_value=False):
            result = trigger_spawn(
                location_name="핏빛성채",
                location_type="rift",
                turn_count=0,
                last_spawn_turn=0,
                spawn_table=table,
                rift_sub_area="bc_ch1",
                rift_defs=FLOOR1_RIFT_DEFS,
            )
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
