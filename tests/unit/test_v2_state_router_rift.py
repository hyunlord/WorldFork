"""audit-3 commit 2 — v2_state_router _maybe_spawn_rift_encounters 단위 테스트."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from service.api.v2_state_router import (
    _maybe_spawn_encounters,
    _maybe_spawn_rift_encounters,
    _V2StateHolder,
)
from service.game.state_v2 import Location, Realm
from service.sim.types import Encounter, EncounterType


def _make_holder(rift_id: str | None = None, rift_sub_area: str | None = None) -> _V2StateHolder:
    h = _V2StateHolder()
    h.location = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area=rift_sub_area or "bc_ch1",
        rift_id=rift_id,
        rift_sub_area=rift_sub_area,
    )
    h.active_encounters = []
    h.turn = 3
    return h


class TestMaybeSpawnRiftEncounters(unittest.TestCase):
    def test_rift_path_skips_llm(self) -> None:
        h = _make_holder(rift_id="bloody_castle", rift_sub_area="bc_ch1")

        with patch(
            "service.api.v2_state_router._maybe_spawn_rift_encounters"
        ) as mock_rift:
            _maybe_spawn_encounters(h)
            mock_rift.assert_called_once_with(h)

    def test_non_rift_uses_llm_path(self) -> None:
        h = _make_holder(rift_id=None, rift_sub_area=None)

        with (
            patch("service.api.v2_state_router._maybe_spawn_rift_encounters") as mock_rift,
            patch.object(h, "get_sim_gm_agent", side_effect=Exception("skip")),
        ):
            try:
                _maybe_spawn_encounters(h)
            except Exception:
                pass
            mock_rift.assert_not_called()

    def test_rift_spawn_adds_encounter(self) -> None:
        h = _make_holder(rift_id="bloody_castle", rift_sub_area="bc_ch1")

        fake_enemy = {"name": "데드맨", "hp": 30, "grade": 1}
        mock_table = MagicMock()
        with (
            patch("service.canon.context.get_spawn_table", return_value=mock_table),
            patch("service.sim.spawn_trigger.trigger_spawn", return_value=[fake_enemy]),
        ):
            _maybe_spawn_rift_encounters(h)
            self.assertEqual(len(h.active_encounters), 1)
            self.assertEqual(h.active_encounters[0].name, "데드맨")

    def test_rift_spawn_skips_if_encounters_exist(self) -> None:
        h = _make_holder(rift_id="bloody_castle", rift_sub_area="bc_ch1")
        h.active_encounters.append(
            Encounter(
                type=EncounterType.MONSTER,
                name="기존 몬스터",
                location="bc_ch1",
            )
        )
        with patch("service.sim.spawn_trigger.trigger_spawn") as mock_trigger:
            _maybe_spawn_rift_encounters(h)
            mock_trigger.assert_not_called()

    def test_non_dungeon_skips_entirely(self) -> None:
        h = _make_holder(rift_id=None)
        h.location = Location(realm=Realm.CITY)

        with patch("service.api.v2_state_router._maybe_spawn_rift_encounters") as mock_rift:
            _maybe_spawn_encounters(h)
            mock_rift.assert_not_called()


if __name__ == "__main__":
    unittest.main()
