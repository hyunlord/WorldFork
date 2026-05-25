"""RaceConfig + Race enum 검증 (phase-e-1)."""

from __future__ import annotations

from service.canon.races import (
    RACE_CONFIGS,
    Race,
    RaceConfig,
    apply_race_base_stats,
    get_race_config,
    race_from_string,
)


def test_all_5_races_defined() -> None:
    """5종 종족 정의 (★ 용인족 제외)."""
    assert len(Race) == 5
    assert Race.BARBARIAN in Race
    assert Race.HUMAN in Race
    assert Race.DWARF in Race
    assert Race.BEASTKIN in Race
    assert Race.FAIRY in Race


def test_all_races_have_config() -> None:
    """모든 race의 config 존재 + 필수 필드."""
    for race in Race:
        config = get_race_config(race)
        assert isinstance(config, RaceConfig)
        assert config.hp_base > 0
        assert config.soul_power_base >= 10
        assert config.max_essences_base >= 1
        assert config.name_ko
        assert config.name_en


def test_race_configs_count() -> None:
    """RACE_CONFIGS 정확히 5종."""
    assert len(RACE_CONFIGS) == 5


def test_barbarian_canon_stats() -> None:
    """바바리안 — wiki: '생명력이 가장 높은 데다가, 근력 기댓값도 높아서'."""
    config = get_race_config(Race.BARBARIAN)
    assert config.name_ko == "바바리안"
    assert config.hp_base == 120
    assert config.attack_base == 14
    assert config.max_essences_base == 1
    assert config.soul_power_base == 10


def test_barbarian_highest_hp() -> None:
    """바바리안 HP가 5종 중 최고 (★ wiki 정합)."""
    barb_hp = get_race_config(Race.BARBARIAN).hp_base
    for race in Race:
        if race != Race.BARBARIAN:
            assert barb_hp >= get_race_config(race).hp_base


def test_fairy_essence_slot_bonus() -> None:
    """요정 — 정수 슬롯 2, 영혼력 20 (★ 정령술/기감 정합)."""
    config = get_race_config(Race.FAIRY)
    assert config.max_essences_base == 2
    assert config.soul_power_base == 20


def test_fairy_lowest_hp() -> None:
    """요정 HP가 5종 중 최저 (★ 소형 체구)."""
    fairy_hp = get_race_config(Race.FAIRY).hp_base
    for race in Race:
        if race != Race.FAIRY:
            assert fairy_hp <= get_race_config(race).hp_base


def test_beastkin_highest_dex() -> None:
    """수인 민첩이 5종 중 최고 (★ wiki: '유별나게 높으며')."""
    beastkin_dex = get_race_config(Race.BEASTKIN).dex_base
    for race in Race:
        if race != Race.BEASTKIN:
            assert beastkin_dex >= get_race_config(race).dex_base


def test_dwarf_highest_defense() -> None:
    """드워프 방어가 5종 중 최고 (★ wiki: 무구의 축복)."""
    dwarf_def = get_race_config(Race.DWARF).defense_base
    for race in Race:
        if race != Race.DWARF:
            assert dwarf_def >= get_race_config(race).defense_base


def test_race_from_string_korean() -> None:
    """한국어 → Race enum."""
    assert race_from_string("바바리안") == Race.BARBARIAN
    assert race_from_string("인간") == Race.HUMAN
    assert race_from_string("드워프") == Race.DWARF
    assert race_from_string("수인") == Race.BEASTKIN
    assert race_from_string("요정") == Race.FAIRY


def test_race_from_string_english_lower() -> None:
    """영문 소문자 → Race enum."""
    assert race_from_string("barbarian") == Race.BARBARIAN
    assert race_from_string("human") == Race.HUMAN
    assert race_from_string("dwarf") == Race.DWARF
    assert race_from_string("beastkin") == Race.BEASTKIN
    assert race_from_string("fairy") == Race.FAIRY


def test_race_from_string_english_upper() -> None:
    """영문 대문자 → Race enum."""
    assert race_from_string("BARBARIAN") == Race.BARBARIAN
    assert race_from_string("HUMAN") == Race.HUMAN


def test_race_from_string_english_title() -> None:
    """영문 title case → Race enum."""
    assert race_from_string("Barbarian") == Race.BARBARIAN
    assert race_from_string("Human") == Race.HUMAN
    assert race_from_string("Fairy") == Race.FAIRY


def test_race_from_string_invalid() -> None:
    """미존재 → None."""
    assert race_from_string("용인족") is None
    assert race_from_string("dragonkin") is None
    assert race_from_string("xyz") is None


def test_race_from_string_empty() -> None:
    """빈 string → None."""
    assert race_from_string("") is None


def test_apply_race_base_stats_barbarian() -> None:
    """바바리안 base stat 적용 — HP 120, 영혼력 10."""
    initial: dict[str, object] = {"current_hp": 999, "max_hp": 999, "race": "unknown"}
    result = apply_race_base_stats(initial, Race.BARBARIAN)
    assert result["race"] == "barbarian"
    assert result["current_hp"] == 120
    assert result["max_hp"] == 120
    assert result["max_essences"] == 1
    assert result["soul_power"] == 10


def test_apply_race_base_stats_fairy() -> None:
    """요정 base stat 적용 — HP 80, 영혼력 20, 슬롯 2."""
    initial: dict[str, object] = {}
    result = apply_race_base_stats(initial, Race.FAIRY)
    assert result["race"] == "fairy"
    assert result["current_hp"] == 80
    assert result["max_hp"] == 80
    assert result["max_essences"] == 2
    assert result["soul_power"] == 20


def test_apply_race_base_stats_preserves_other_fields() -> None:
    """apply_race_base_stats — 기존 필드 보존."""
    initial: dict[str, object] = {"inventory": ["검"], "turn_count": 5}
    result = apply_race_base_stats(initial, Race.HUMAN)
    assert result["inventory"] == ["검"]
    assert result["turn_count"] == 5


def test_race_enum_values_are_lowercase_english() -> None:
    """Race enum value → lowercase English (DB 저장 정합)."""
    for race in Race:
        assert race.value == race.value.lower()
        assert race.value.isascii()
