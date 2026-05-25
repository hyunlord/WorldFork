"""Phase E-4: 종족별 starting_inventory_default 본문 정합 테스트."""

from __future__ import annotations

from service.canon.races import Race, get_race_config


def test_all_races_have_starting_inventory_default() -> None:
    """모든 race에 starting_inventory_default field 존재."""
    for race in Race:
        config = get_race_config(race)
        assert hasattr(config, "starting_inventory_default")
        assert isinstance(config.starting_inventory_default, tuple)


def test_barbarian_default_axe() -> None:
    """ep_0002: 카락 성인식 → '양손도끼라! 훌륭하다!' — 바바리안 정합 기본 무기."""
    config = get_race_config(Race.BARBARIAN)
    assert config.starting_inventory_default == ("도끼",)


def test_human_default_sword() -> None:
    """wiki 012: '오러는 무조건 도검류. 검은 오러를 가장 활용하기 좋은 무기'."""
    config = get_race_config(Race.HUMAN)
    assert config.starting_inventory_default == ("검",)


def test_dwarf_default_hammer() -> None:
    """wiki 012: '내 망치를 걸고 맹세', '두모카' = 판결하는 망치 (부족장 칭호)."""
    config = get_race_config(Race.DWARF)
    assert config.starting_inventory_default == ("망치",)


def test_beastkin_default_empty() -> None:
    """wiki 012: '발톱 — 비무장 공격 +3' traits 정합 — 비무장 출발."""
    config = get_race_config(Race.BEASTKIN)
    assert config.starting_inventory_default == ()


def test_beastkin_claws_in_traits() -> None:
    """발톱이 traits에 존재 — 비무장 근거 확인."""
    config = get_race_config(Race.BEASTKIN)
    assert any("발톱" in trait for trait in config.traits)


def test_fairy_default_dagger() -> None:
    """정령술 마법 위주 + 기동성 정합 — 근접 보조 단검."""
    config = get_race_config(Race.FAIRY)
    assert config.starting_inventory_default == ("단검",)
