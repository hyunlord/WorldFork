"""Day 1: 시나리오 로딩 / 프롬프트 빌드 테스트."""

import pytest

from service.game.loop import build_gm_prompt, initialize_state, load_scenario


def test_load_novice_dungeon_run() -> None:
    scenario = load_scenario("novice_dungeon_run")
    assert scenario["id"] == "novice_dungeon_run"
    assert "라스카니아" in scenario["setting"]["world"]
    assert len(scenario["characters"]) == 2
    assert len(scenario["mechanical_rules"]) == 5


def test_load_unknown_scenario() -> None:
    with pytest.raises(FileNotFoundError):
        load_scenario("does_not_exist")


def test_initialize_state_has_player() -> None:
    scenario = load_scenario("novice_dungeon_run")
    state = initialize_state(scenario)

    player = state.get_player()
    assert player is not None
    assert player.name == "투르윈"
    assert state.location == "탐험가 길드 정문"


def test_initialize_state_has_npcs() -> None:
    scenario = load_scenario("novice_dungeon_run")
    state = initialize_state(scenario)

    assert "companion_mage" in state.characters
    assert "guildmaster" in state.characters
    assert state.characters["companion_mage"].name == "셰인"


def test_build_gm_prompt_5_section_structure() -> None:
    scenario = load_scenario("novice_dungeon_run")
    state = initialize_state(scenario)
    prompt = build_gm_prompt(scenario, state, "주변을 둘러본다")

    assert "# IDENTITY" in prompt.system
    assert "# TASK" in prompt.system
    assert "# SPEC" in prompt.system
    assert "# OUTPUT FORMAT" in prompt.system
    assert "# EXAMPLES" in prompt.system

    assert "투르윈" in prompt.system
    assert "셰인" in prompt.system
    assert "라스카니아" in prompt.system

    assert "주변을 둘러본다" in prompt.user
    assert "(첫 턴)" in prompt.user


def test_build_gm_prompt_with_history() -> None:
    scenario = load_scenario("novice_dungeon_run")
    state = initialize_state(scenario)
    state.add_turn("인사한다", "셰인이 인사를 받는다.", 0.0, 12000)

    prompt = build_gm_prompt(scenario, state, "다음 행동")

    assert "[Turn 1]" in prompt.user
    assert "사용자: 인사한다" in prompt.user


def test_build_gm_prompt_includes_ip_blocking() -> None:
    """프롬프트에 IP/AI 차단 룰 포함되는지."""
    scenario = load_scenario("novice_dungeon_run")
    state = initialize_state(scenario)
    prompt = build_gm_prompt(scenario, state, "test")

    assert "AI" in prompt.system
    assert "비요른" in prompt.system
