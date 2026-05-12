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


# ─── F5: slot awareness ───


def test_format_slot_status_full() -> None:
    """slot 5/5 FULL 본격 명시 + OFFER_TO_STONE 권장."""
    from service.sim.player_agent import _format_slot_status

    s = _format_slot_status(5, 5)
    assert "5/5" in s
    assert "FULL" in s
    assert "OFFER_TO_STONE" in s


def test_format_slot_status_almost_full() -> None:
    """slot 4/5 — 1 추가 가능 본격."""
    from service.sim.player_agent import _format_slot_status

    s = _format_slot_status(4, 5)
    assert "4/5" in s
    assert "1 추가" in s


def test_format_slot_status_empty() -> None:
    """slot 0/5 — 5 추가 가능 본격."""
    from service.sim.player_agent import _format_slot_status

    s = _format_slot_status(0, 5)
    assert "0/5" in s
    assert "5 추가" in s


def test_system_prompt_absorb_slot_full_forbidden() -> None:
    """ACTION_TYPE_GUIDANCE 본격 — slot FULL 시 ABSORB 금지 명시."""
    p = PLAYER_AGENT_SYSTEM_PROMPT
    assert "슬롯 5/5 FULL" in p
    assert "ABSORB_ESSENCE 사용 금지" in p
    assert "OFFER_TO_STONE" in p


def test_build_prompt_slot_full_warning() -> None:
    """slot 5/5 + essence encounter → ABSORB 금지 + OFFER 권장 본격."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 5,
                "essence_slot_max": 5,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 10,
            "party_members": ["비요른"],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "수정 동굴",
        },
        "active_encounters": [
            {
                "type": "essence",
                "name": "갈색 정수",
                "location": "수정 동굴",
                "description": "떠다니는 정수",
                "details": {},
                "spawned_at_turn": 9,
                "ttl_remaining": 30,
            }
        ],
    }
    p = _build_player_prompt("비요른", ctx)
    assert "5/5" in p
    assert "FULL" in p
    # ★ essence encounter hint 본격 slot FULL 시 OFFER_TO_STONE 권장
    assert "슬롯 FULL" in p
    assert "OFFER_TO_STONE" in p


# ─── F6: rift prerequisite ───


def test_system_prompt_enter_rift_prerequisite() -> None:
    """ACTION_TYPE_GUIDANCE 본격 — ENTER_RIFT active_rifts 조건 명시."""
    p = PLAYER_AGENT_SYSTEM_PROMPT
    assert "active_rifts" in p
    assert "활성 균열" in p
    # ★ F6: 활성 X 시 사용 금지 본격
    assert "활성 균열 없으면 사용 금지" in p or "활성 X 시" in p
    # ★ OFFER_TO_STONE 먼저 본격 명시
    assert "OFFER_TO_STONE 먼저" in p


def test_system_prompt_offer_to_stone_activation() -> None:
    """ACTION_TYPE_GUIDANCE 본격 — OFFER_TO_STONE 활성화 mechanism 명시."""
    p = PLAYER_AGENT_SYSTEM_PROMPT
    assert "world.active_rifts에 등록" in p
    assert "ENTER_RIFT 가능" in p


def test_build_prompt_active_rifts_empty_warning() -> None:
    """active_rifts empty 본격 ENTER_RIFT 금지 경고 본격."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 0,
                "essence_slot_max": 5,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 72,
            "party_members": ["비요른"],
            "active_rifts": [],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "비석 공동",
        },
    }
    p = _build_player_prompt("비요른", ctx)
    assert "활성 균열" in p
    assert "없음" in p
    assert "ENTER_RIFT 사용 금지" in p
    assert "OFFER_TO_STONE 먼저" in p


def test_build_prompt_active_rifts_present() -> None:
    """active_rifts ≥ 1 본격 ENTER_RIFT 가능 명시 본격."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 0,
                "essence_slot_max": 5,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 72,
            "party_members": ["비요른"],
            "active_rifts": ["bloody_castle"],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "포탈 근처",
        },
    }
    p = _build_player_prompt("비요른", ctx)
    assert "bloody_castle" in p
    assert "ENTER_RIFT 가능" in p


def test_build_prompt_rift_encounter_inactive_warning() -> None:
    """RIFT encounter + active_rifts X 본격 OFFER 권장 본격."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 0,
                "essence_slot_max": 5,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 72,
            "party_members": ["비요른"],
            "active_rifts": [],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "포탈 근처",
        },
        "active_encounters": [
            {
                "type": "rift",
                "name": "핏빛성채",
                "location": "포탈 근처",
                "description": "균열",
                "details": {},
                "spawned_at_turn": 1,
                "ttl_remaining": 30,
            }
        ],
    }
    p = _build_player_prompt("비요른", ctx)
    assert "핏빛성채" in p
    assert "비활성" in p
    assert "OFFER_TO_STONE 먼저" in p


def test_build_prompt_slot_partial_allowed() -> None:
    """slot 2/5 + essence encounter → ABSORB 우선 본격 (★ 본격 정합)."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 2,
                "essence_slot_max": 5,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 10,
            "party_members": ["비요른"],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "수정 동굴",
        },
        "active_encounters": [
            {
                "type": "essence",
                "name": "갈색 정수",
                "location": "수정 동굴",
                "description": "떠다니는 정수",
                "details": {},
                "spawned_at_turn": 9,
                "ttl_remaining": 30,
            }
        ],
    }
    p = _build_player_prompt("비요른", ctx)
    assert "2/5" in p
    assert "3 추가 가능" in p
    assert "ABSORB_ESSENCE 우선" in p


# ─── F7: EXIT_RIFT 본격 prompt + realm 인지 ───


def test_system_prompt_exit_rift_realm_condition() -> None:
    """EXIT_RIFT 본격 조건 'location.realm == RIFT' 본격 명시."""
    p = PLAYER_AGENT_SYSTEM_PROMPT
    assert "EXIT_RIFT" in p
    assert "location.realm == RIFT" in p or "균열 안" in p
    # 균열 밖 본격 사용 X 본격
    assert "realm=DUNGEON" in p or "균열 밖" in p


def test_system_prompt_enter_rift_in_rift_forbidden() -> None:
    """ENTER_RIFT 본격 이미 균열 안 본격 시 금지 본격."""
    p = PLAYER_AGENT_SYSTEM_PROMPT
    assert "realm=RIFT" in p or "이미 균열 안" in p
    # EXIT_RIFT 대안 본격 명시
    assert "EXIT_RIFT" in p


def test_build_prompt_in_rift_hint() -> None:
    """realm=RIFT (균열) 본격 시 EXIT_RIFT 본격 복귀 가이드 본격."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 0,
                "essence_slot_max": 5,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 73,
            "party_members": ["비요른"],
            "active_rifts": ["bloody_castle"],
        },
        "v2_initial_location": {
            "realm": "균열",
            "floor": 1,
            "sub_area": "균열 내부",
            "rift_id": "bloody_castle",
        },
    }
    p = _build_player_prompt("비요른", ctx)
    assert "현재 균열 안 본격" in p
    assert "bloody_castle" in p
    assert "EXIT_RIFT" in p
    assert "1층 복귀" in p


def test_build_prompt_in_rift_already_entered_warning() -> None:
    """realm=RIFT 본격 + active_rifts 있음 본격 'EXIT 우선' 본격."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 0,
                "essence_slot_max": 5,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 73,
            "party_members": ["비요른"],
            "active_rifts": ["bloody_castle"],
        },
        "v2_initial_location": {
            "realm": "균열",
            "floor": 1,
            "sub_area": "균열 내부",
            "rift_id": "bloody_castle",
        },
    }
    p = _build_player_prompt("비요른", ctx)
    # 이미 진입 본격 → EXIT_RIFT 우선 본격
    assert "이미 진입 본격" in p or "EXIT_RIFT 우선" in p


def test_build_prompt_dungeon_no_in_rift_hint() -> None:
    """realm=DUNGEON 본격 시 in_rift hint 본격 출현 X."""
    ctx = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": True,
                "essence_slots_used": 0,
                "essence_slot_max": 5,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 72,
            "party_members": ["비요른"],
            "active_rifts": ["bloody_castle"],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "포탈 근처",
        },
    }
    p = _build_player_prompt("비요른", ctx)
    # 균열 밖 본격 → in_rift hint 본격 X
    assert "현재 균열 안 본격" not in p
    # active_rifts 본격 ENTER_RIFT 가능 본격 (★ F6 본격)
    assert "ENTER_RIFT 가능" in p
