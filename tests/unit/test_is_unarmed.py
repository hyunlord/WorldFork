"""is_unarmed() helper unit tests."""
from __future__ import annotations

from service.sim.inventory_helpers import is_unarmed


def test_empty_inventory_unarmed() -> None:
    assert is_unarmed([]) is True


def test_axe_armed() -> None:
    assert is_unarmed(["도끼"]) is False


def test_sword_armed() -> None:
    assert is_unarmed(["검"]) is False


def test_shield_armed() -> None:
    """방패 = 무기 판정 (★ ep_0003 비요른 방패)."""
    assert is_unarmed(["방패"]) is False


def test_torch_only_unarmed() -> None:
    """횃불 only — 무기 X."""
    assert is_unarmed(["횃불"]) is True


def test_mixed_armed() -> None:
    assert is_unarmed(["횃불", "도끼"]) is False
