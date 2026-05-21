"""Audit C1 — StateDelta stone_change 직렬화 테스트."""

from service.api.schemas.freeform_action import StateDelta


def test_stone_change_default():
    delta = StateDelta(hp_change=0)
    assert delta.stone_change == 0


def test_stone_change_positive():
    delta = StateDelta(hp_change=0, stone_change=140)
    data = delta.model_dump()
    assert data["stone_change"] == 140


def test_stone_change_negative():
    delta = StateDelta(hp_change=0, stone_change=-500)
    assert delta.stone_change == -500
