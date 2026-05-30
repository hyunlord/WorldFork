"""ItemRegistry element/sensitivity 확장 단위 테스트."""

from __future__ import annotations

from service.canon.items import (
    ItemRegistry,
    SensitivityItem,
    _parse_element,
    _parse_sensitivity_item,
)
from service.canon.schema import CanonFacts, Mechanism

# ── _parse_element ──────────────────────────────────────────────────────────


def test_element_fire() -> None:
    assert _parse_element("화염검", "") == "불"
    assert _parse_element("롱소드", "화염 피해를 입힌다") == "불"  # description 기반


def test_element_holy() -> None:
    assert _parse_element("성스러운 검", "") == "신성력"


def test_element_cold() -> None:
    assert _parse_element("서리 단검", "") == "냉기"
    assert _parse_element("검", "빙결 속성 부여") == "냉기"


def test_element_lightning_light() -> None:
    assert _parse_element("번개 창", "") == "전격"
    assert _parse_element("여명의 활", "") == "빛"


def test_element_none() -> None:
    assert _parse_element("강철 검", "평범한 무기") == ""


# ── _parse_sensitivity_item ─────────────────────────────────────────────────


def test_sensitivity_item_cold() -> None:
    """빙정: 냉기 감응도 +3."""
    item = _parse_sensitivity_item("빙정", "냉기 감응도를 영구적으로 +3 상승. 세 번까지.")
    assert item is not None
    assert item.element == "냉기"
    assert item.bonus == 3


def test_sensitivity_item_fire() -> None:
    """순수한 불꽃: 화염 감응도 +15 → 불."""
    item = _parse_sensitivity_item("순수한 불꽃", "화염 감응도가 +15 증가.")
    assert item is not None
    assert item.element == "불"
    assert item.bonus == 15


def test_sensitivity_item_no_keyword() -> None:
    assert _parse_sensitivity_item("강철 검", "공격력 +5") is None


def test_sensitivity_item_no_bonus() -> None:
    """감응도 언급되나 +N 없음 → None."""
    assert _parse_sensitivity_item("X", "냉기 감응도 관련 수치") is None


# ── ItemRegistry 통합 ───────────────────────────────────────────────────────


def _facts() -> CanonFacts:
    return CanonFacts(
        essences=[], characters=[], locations=[], races=[],
        mechanisms=[
            Mechanism(name="화염검", category="combat",
                      description="불타는 장검. 공격력 +8"),
            Mechanism(name="빙정", category="magic",
                      description="냉기 감응도를 영구적으로 +3 상승."),
            Mechanism(name="순수한 불꽃", category="progression",
                      description="포션. 화염 감응도가 +15 증가."),
            Mechanism(name="강철 검", category="combat", description="평범한 검"),
        ],
    )


def test_registry_weapon_element() -> None:
    reg = ItemRegistry(_facts())
    fire = reg.lookup("화염검")
    assert fire is not None
    assert fire.element == "불"
    assert fire.attack_bonus == 8
    steel = reg.lookup("강철 검")
    assert steel is not None
    assert steel.element == ""


def test_registry_sensitivity_items() -> None:
    reg = ItemRegistry(_facts())
    items = {s.name: s for s in reg.sensitivity_items()}
    assert items["빙정"].element == "냉기" and items["빙정"].bonus == 3
    assert items["순수한 불꽃"].element == "불" and items["순수한 불꽃"].bonus == 15
    # 무기는 sensitivity item 아님
    assert reg.lookup_sensitivity_item("화염검") is None


def test_registry_dataclass_type() -> None:
    reg = ItemRegistry(_facts())
    for s in reg.sensitivity_items():
        assert isinstance(s, SensitivityItem)
