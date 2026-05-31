"""ScenarioMode + ScenarioConfig 검증 (phase-e-2)."""
from __future__ import annotations

from service.canon.races import Race
from service.canon.scenario import (
    SCENARIO_CONFIGS,
    ScenarioMode,
    resolve_race_for_scenario,
    scenario_from_string,
)


def test_two_scenario_modes_defined() -> None:
    """ScenarioMode 2종 (BJORN + NEW_EXPLORER)."""
    assert len(ScenarioMode) == 2
    assert ScenarioMode.BJORN in ScenarioMode
    assert ScenarioMode.NEW_EXPLORER in ScenarioMode


def test_all_scenarios_have_config() -> None:
    """SCENARIO_CONFIGS 2종 완전성."""
    assert len(SCENARIO_CONFIGS) == 2
    for mode in ScenarioMode:
        cfg = SCENARIO_CONFIGS[mode]
        assert cfg.name_ko
        assert cfg.starting_location
        assert cfg.starting_floor >= 0  # ★ 0 = 성인식 마을/성지 (ep_0002)


def test_bjorn_fixed_race_barbarian() -> None:
    """BJORN — fixed_race=BARBARIAN (★ ep_0003 anchor)."""
    cfg = SCENARIO_CONFIGS[ScenarioMode.BJORN]
    assert cfg.fixed_race == Race.BARBARIAN


def test_new_explorer_no_fixed_race() -> None:
    """NEW_EXPLORER — fixed_race=None (5종 자유 선택)."""
    cfg = SCENARIO_CONFIGS[ScenarioMode.NEW_EXPLORER]
    assert cfg.fixed_race is None


def test_bjorn_location_ip_safe() -> None:
    """BJORN starting_location — 라스카니아 포함, 라프도니아 없음 (IP 보호)."""
    cfg = SCENARIO_CONFIGS[ScenarioMode.BJORN]
    assert "라스카니아" in cfg.starting_location
    assert "라프도니아" not in cfg.starting_location


def test_bjorn_canon_anchor() -> None:
    """BJORN canon_anchor = ep_0002 (★ 성인식 — 부족 성지 성년식)."""
    cfg = SCENARIO_CONFIGS[ScenarioMode.BJORN]
    assert cfg.canon_anchor == "ep_0002"


def test_resolve_bjorn_always_barbarian() -> None:
    """BJORN — user_choice 무시, 항상 BARBARIAN."""
    assert resolve_race_for_scenario(ScenarioMode.BJORN) == Race.BARBARIAN
    assert resolve_race_for_scenario(ScenarioMode.BJORN, Race.FAIRY) == Race.BARBARIAN
    assert resolve_race_for_scenario(ScenarioMode.BJORN, Race.DWARF) == Race.BARBARIAN


def test_resolve_new_explorer_user_choice() -> None:
    """NEW_EXPLORER — user_choice 반영."""
    assert resolve_race_for_scenario(ScenarioMode.NEW_EXPLORER, Race.FAIRY) == Race.FAIRY
    assert resolve_race_for_scenario(ScenarioMode.NEW_EXPLORER, Race.BEASTKIN) == Race.BEASTKIN


def test_resolve_new_explorer_default_human() -> None:
    """NEW_EXPLORER — user_choice=None → HUMAN fallback."""
    assert resolve_race_for_scenario(ScenarioMode.NEW_EXPLORER, None) == Race.HUMAN
    assert resolve_race_for_scenario(ScenarioMode.NEW_EXPLORER) == Race.HUMAN


def test_scenario_from_string_valid() -> None:
    """scenario_from_string — 소문자 → ScenarioMode."""
    assert scenario_from_string("bjorn") == ScenarioMode.BJORN
    assert scenario_from_string("new_explorer") == ScenarioMode.NEW_EXPLORER


def test_scenario_from_string_case_insensitive() -> None:
    """scenario_from_string — 대소문자 무시."""
    assert scenario_from_string("BJORN") == ScenarioMode.BJORN
    assert scenario_from_string("New_Explorer") == ScenarioMode.NEW_EXPLORER


def test_scenario_from_string_invalid() -> None:
    """scenario_from_string — 미존재 → None."""
    assert scenario_from_string("unknown") is None
    assert scenario_from_string("") is None
