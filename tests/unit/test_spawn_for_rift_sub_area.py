"""audit-3 commit 2 — SpawnTable.spawn_for_rift_sub_area 단위 테스트."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from service.canon.spawn import SpawnTable
from service.game.state_v2 import RiftChamberType, RiftSubAreaDef


def _make_spawn_table() -> SpawnTable:
    facts = MagicMock()
    facts.locations = []
    facts.characters = []
    facts.races = []
    return SpawnTable(facts)


class TestSpawnForRiftSubAreaEntrance(unittest.TestCase):
    def test_entrance_returns_monsters_from_pool(self) -> None:
        table = _make_spawn_table()
        sub_def = RiftSubAreaDef(
            id="bc_ch1",
            name="외곽 검문소",
            chamber_type=RiftChamberType.ENTRANCE,
            monsters=("데드맨", "병사 데드맨", "지휘관 데드맨"),
        )
        result = table.spawn_for_rift_sub_area(sub_def, n=1)
        self.assertEqual(len(result), 1)
        self.assertIn(result[0].name, ("데드맨", "병사 데드맨", "지휘관 데드맨"))

    def test_entrance_n2_returns_two_distinct_enemies(self) -> None:
        table = _make_spawn_table()
        sub_def = RiftSubAreaDef(
            id="bc_ch1",
            name="외곽 검문소",
            chamber_type=RiftChamberType.ENTRANCE,
            monsters=("데드맨", "병사 데드맨", "지휘관 데드맨"),
        )
        result = table.spawn_for_rift_sub_area(sub_def, n=2)
        self.assertEqual(len(result), 2)

    def test_entrance_empty_monsters_returns_fallback(self) -> None:
        table = _make_spawn_table()
        sub_def = RiftSubAreaDef(
            id="bc_ch1",
            name="외곽 검문소",
            chamber_type=RiftChamberType.ENTRANCE,
            monsters=(),
        )
        result = table.spawn_for_rift_sub_area(sub_def, n=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "이름 모를 적")


class TestSpawnForRiftSubAreaMidBoss(unittest.TestCase):
    def test_mid_boss_returns_single_boss(self) -> None:
        table = _make_spawn_table()
        sub_def = RiftSubAreaDef(
            id="bc_ch4",
            name="내성벽 지하 감옥",
            chamber_type=RiftChamberType.MID_BOSS,
            monsters=("스컬 랫", "벤시"),
            mid_boss_name="시체골렘",
            mid_boss_grade=7,
        )
        result = table.spawn_for_rift_sub_area(sub_def, n=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "시체골렘")
        self.assertEqual(result[0].grade, 7)

    def test_mid_boss_grade_applied_to_stats(self) -> None:
        table = _make_spawn_table()
        sub_def = RiftSubAreaDef(
            id="gc_ch2",
            name="지하 + 토템",
            chamber_type=RiftChamberType.MID_BOSS,
            monsters=("서리 늑대",),
            mid_boss_name="상위 변이종 예티",
            mid_boss_grade=5,
        )
        result = table.spawn_for_rift_sub_area(sub_def, n=1)
        enemy = result[0]
        self.assertEqual(enemy.grade, 5)
        self.assertEqual(enemy.hp, 20 + 5 * 10)  # 70
        self.assertEqual(enemy.attack, 5 + 5 * 3)  # 20

    def test_mid_boss_no_name_falls_back_to_monsters(self) -> None:
        table = _make_spawn_table()
        sub_def = RiftSubAreaDef(
            id="xx_ch2",
            name="중간 챕터",
            chamber_type=RiftChamberType.MID_BOSS,
            monsters=("고블린 전사",),
            mid_boss_name=None,
        )
        result = table.spawn_for_rift_sub_area(sub_def, n=1)
        self.assertEqual(result[0].name, "고블린 전사")


class TestSpawnForRiftSubAreaBoss(unittest.TestCase):
    def test_boss_chamber_returns_from_monsters(self) -> None:
        table = _make_spawn_table()
        sub_def = RiftSubAreaDef(
            id="bc_ch5",
            name="영주성 악마 숭배실",
            chamber_type=RiftChamberType.BOSS,
            monsters=("가고일 석상", "데스핀드", "본 나이트"),
        )
        result = table.spawn_for_rift_sub_area(sub_def, n=1)
        self.assertEqual(len(result), 1)
        self.assertIn(result[0].name, ("가고일 석상", "데스핀드", "본 나이트"))

    def test_boss_chamber_empty_monsters_fallback(self) -> None:
        table = _make_spawn_table()
        sub_def = RiftSubAreaDef(
            id="it_ch4",
            name="최심부",
            chamber_type=RiftChamberType.BOSS,
            monsters=(),
        )
        result = table.spawn_for_rift_sub_area(sub_def, n=1)
        self.assertEqual(result[0].name, "이름 모를 적")


if __name__ == "__main__":
    unittest.main()
