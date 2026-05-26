"""apply_race_dodge() unit tests — random monkeypatch."""
from __future__ import annotations

import random

from service.canon.races import Race
from service.sim.combat_helpers import apply_race_dodge


def test_no_dodge_no_change() -> None:
    """회피 0 race — damage 변경 X."""
    damage, dodged = apply_race_dodge(Race.BARBARIAN, 10)
    assert damage == 10
    assert dodged is False


def test_dodge_succeeds_when_roll_zero(monkeypatch: object) -> None:
    """roll 0 → 회피 성공 (드워프 5% > 0)."""

    assert isinstance(monkeypatch, object)
    mp = monkeypatch  # type: ignore[attr-defined]
    mp.setattr(random, "random", lambda: 0.0)
    damage, dodged = apply_race_dodge(Race.DWARF, 10)
    assert damage == 0
    assert dodged is True


def test_dodge_fails_when_roll_high(monkeypatch: object) -> None:
    """roll 0.99 → 회피 실패 (요정 10% < 99)."""
    mp = monkeypatch  # type: ignore[attr-defined]
    mp.setattr(random, "random", lambda: 0.99)
    damage, dodged = apply_race_dodge(Race.FAIRY, 10)
    assert damage == 10
    assert dodged is False
