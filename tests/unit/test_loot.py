"""V3 수직 슬라이스 Phase 3 — 드롭(마석/정수) → 인벤·소지금 단위 테스트.

처치 드롭이 마석→소지금(스톤)+인벤, 정수→인벤(수집)으로 반영되는가. 등급 경제값
(WORLD_BIBLE)·집계. ★ 정수 흡수/거래는 범위 밖 — 수집·표시만 검증.
"""

from service.sim.loot import Inventory, award_drop, mana_stone_value


class TestManaStoneValue:
    def test_world_bible_grades(self) -> None:
        # WORLD_BIBLE: 9등급 ≈ 20스톤, 8등급 ≈ 100스톤(등급↑일수록 고가).
        assert mana_stone_value(9) == 20
        assert mana_stone_value(8) == 100
        assert mana_stone_value(8) > mana_stone_value(9)

    def test_unknown_grade_defaults_low(self) -> None:
        assert mana_stone_value(99) == mana_stone_value(9)


class TestAwardDrop:
    def test_mana_adds_stones_and_record(self) -> None:
        inv = Inventory()
        notes = award_drop(inv, grade=9, essence="")
        assert inv.stones == 20
        assert inv.mana_stones == [9]
        assert any("마석" in n for n in notes)

    def test_essence_collected(self) -> None:
        inv = Inventory()
        award_drop(inv, grade=9, essence="고블린 정수")
        assert inv.essences == ["고블린 정수"]

    def test_no_essence_when_empty(self) -> None:
        inv = Inventory()
        award_drop(inv, grade=9, essence="")
        assert inv.essences == []

    def test_accumulates_across_kills(self) -> None:
        inv = Inventory()
        award_drop(inv, grade=9, essence="고블린 정수")
        award_drop(inv, grade=9, essence="고블린 정수")
        award_drop(inv, grade=8, essence="")
        assert inv.stones == 20 + 20 + 100
        assert inv.mana_stones.count(9) == 2
        assert inv.mana_stones.count(8) == 1
        assert len(inv.essences) == 2
