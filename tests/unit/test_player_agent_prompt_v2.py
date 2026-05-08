"""PLAYER_AGENT_SYSTEM_PROMPT v2 본격 보강 검증.

본 commit (★ A — LLM prompt 보강):
- 13 ActionType 다양 가이드 본격
- 1층 6단계 진행 본질 본격
- few-shot 예시 본격
- 추천 힌트 rule-based 본격
"""

from __future__ import annotations

from service.sim.player_agent import (
    PLAYER_AGENT_SYSTEM_PROMPT,
    _build_player_prompt,
)


def test_system_prompt_contains_all_13_action_types() -> None:
    """13 ActionType 모두 본격 출력."""
    p = PLAYER_AGENT_SYSTEM_PROMPT
    for at in [
        "activate_light",
        "move",
        "explore",
        "attack",
        "absorb_essence",
        "use_item",
        "offer_to_stone",
        "enter_rift",
        "exit_rift",
        "rest",
        "wait",
        "communicate",
        "flee",
    ]:
        assert at in p, f"{at} 본격 출력 X"


def test_system_prompt_contains_progression_stages() -> None:
    """1층 6단계 진행 본질."""
    p = PLAYER_AGENT_SYSTEM_PROMPT
    assert "1단계: 빛 확보" in p
    assert "2단계: 탐색" in p
    assert "3단계: 정수" in p
    assert "4단계: 전투" in p
    assert "5단계: 휴식" in p
    assert "6단계: 균열" in p


def test_system_prompt_contains_few_shot_examples() -> None:
    """few-shot 예시 본격."""
    p = PLAYER_AGENT_SYSTEM_PROMPT
    assert "예시 1" in p
    assert "예시 2" in p
    assert "예시 3" in p
    # 예시별 ActionType 본격
    assert "activate_light" in p
    assert "absorb_essence" in p
    assert "rest" in p


def test_system_prompt_forbids_explore_only() -> None:
    """EXPLORE만 반복 금지 본격."""
    p = PLAYER_AGENT_SYSTEM_PROMPT
    assert "EXPLORE만 반복" in p


def test_build_prompt_no_light_hint() -> None:
    """빛 X / 진입 시 ACTIVATE_LIGHT 힌트."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": False,
                "essence_slots_used": 0,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 0,
            "party_members": ["비요른"],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "진입점",
        },
    }
    p = _build_player_prompt("비요른", ctx)
    assert "ACTIVATE_LIGHT 우선 권장" in p


def test_build_prompt_low_hp_hint() -> None:
    """HP < 30% / REST 힌트."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 30,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 0,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 5,
            "party_members": ["비요른"],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "진입점",
        },
    }
    p = _build_player_prompt("비요른", ctx)
    assert "REST 권장" in p


def test_build_prompt_long_dungeon_hint() -> None:
    """미궁 시간 100h+ / 균열 진입 힌트."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 7,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 120,
            "party_members": ["비요른"],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "진입점",
        },
    }
    p = _build_player_prompt("비요른", ctx)
    assert "168h 한도 임박" in p
