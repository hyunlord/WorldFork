"""Audit C1 — 마석 환산 table 단위 테스트."""

from service.canon.exchange import MAGE_STONE_EXCHANGE_RATE, compute_stone_for_mage_stone


def test_9th_grade_confirmed():
    assert compute_stone_for_mage_stone(9) == 20


def test_8th_grade_confirmed():
    assert compute_stone_for_mage_stone(8) == 100


def test_count_multiplier():
    assert compute_stone_for_mage_stone(9, 3) == 60
    assert compute_stone_for_mage_stone(8, 2) == 200


def test_unknown_grade_returns_zero():
    assert compute_stone_for_mage_stone(0) == 0
    assert compute_stone_for_mage_stone(10) == 0


def test_all_grades_present():
    for grade in range(1, 10):
        assert grade in MAGE_STONE_EXCHANGE_RATE
        assert MAGE_STONE_EXCHANGE_RATE[grade] > 0


def test_grade_ordering():
    # 등급 낮을수록 단가 높아야 함
    for grade in range(1, 9):
        assert MAGE_STONE_EXCHANGE_RATE[grade] > MAGE_STONE_EXCHANGE_RATE[grade + 1]
