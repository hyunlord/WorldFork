"""Phase 9.17-a solo-entry — 1인 진입 명시 + regression.

검증 본질:
- MIN_PARTY_SIZE_FLOOR1 = 1 / MAX_PARTY_SIZE = 5 상수
- 1인 진입 이미 가능 (★ 진단 결과 — 본 commit 코드 동작 변경 X)
- 2/5인 진입도 OK
- 6인 진입은 RiftDef.party_capacity=5 본격 fail (★ 9.9-a 정합)
- gm_agent prompt 본격 1인 / 4+인 narrative hint

본문 정합:
- 20화: '혼자 미궁에 들어갈 생각' / 비용 사정
- 44화: 파티 강제 / 역할군 부재 치명적
- 111화: 1층 vs 2층 차이
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    Race,
    WorldState,
)
from service.game.turn_handler_v2 import (
    MAX_PARTY_SIZE,
    MIN_PARTY_SIZE_FLOOR1,
    enter_rift,
    offer_to_stone,
)

# ─── 1. 상수 ───


def test_min_party_size_1() -> None:
    """20화 정합 — 1인 진입 본격."""
    assert MIN_PARTY_SIZE_FLOOR1 == 1


def test_max_party_size_5() -> None:
    """WorldState.max_party_members / RiftDef.party_capacity 정합."""
    assert MAX_PARTY_SIZE == 5


# ─── 2. 진입 regression (★ 1인 가능 보존) ───


def _ally(name: str) -> Character:
    return Character(
        name=name,
        race=Race.HUMAN,
        hp=100,
        hp_max=100,
        physical=12,
        strength=14,
    )


def _bjorn() -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        physical=14,
        strength=16,
    )


def test_solo_entry_to_rift_works_20hwa() -> None:
    """20화 정합 — 비용 사정 시 1인 진입 자연."""
    bjorn = _bjorn()
    world = WorldState()
    offer_to_stone(bjorn, "green_mine", world)
    result = enter_rift([bjorn], world, "green_mine")
    assert result.success is True


def test_two_person_entry_works() -> None:
    """비요른 + 에르웬 정합 (★ 5화 본문)."""
    bjorn = _bjorn()
    erwen = Character(
        name="에르웬",
        race=Race.FAERIE,
        hp=90,
        hp_max=90,
    )
    world = WorldState()
    offer_to_stone(bjorn, "green_mine", world)
    result = enter_rift([bjorn, erwen], world, "green_mine")
    assert result.success is True


def test_full_team_5_works() -> None:
    """MAX_PARTY_SIZE 본격 진입 OK."""
    members = [_ally(f"M{i}") for i in range(MAX_PARTY_SIZE)]
    world = WorldState()
    offer_to_stone(members[0], "green_mine", world)
    result = enter_rift(members, world, "green_mine")
    assert result.success is True


def test_six_members_blocked_party_capacity() -> None:
    """RiftDef.party_capacity=5 본격 6인 fail (★ 9.9-a 정합)."""
    members = [_ally(f"M{i}") for i in range(MAX_PARTY_SIZE + 1)]
    world = WorldState()
    offer_to_stone(members[0], "green_mine", world)
    result = enter_rift(members, world, "green_mine")
    assert result.success is False
    assert "한도" in result.message


def test_dead_member_not_counted_in_capacity() -> None:
    """죽은 멤버 본격 capacity 본격 본격 X (★ enter_rift alive_party 본격)."""
    members = [_ally(f"M{i}") for i in range(MAX_PARTY_SIZE + 1)]
    members[0].hp = 0  # ★ 죽은 멤버 1
    world = WorldState()
    offer_to_stone(members[1], "green_mine", world)
    result = enter_rift(members, world, "green_mine")
    # alive = 5 → cap 5 → OK
    assert result.success is True


# ─── 3. gm_agent prompt narrative hint ───


def _base_ctx(party_names: list[str]) -> dict[str, Any]:
    chars: dict[str, dict[str, Any]] = {}
    for name in party_names:
        chars[name] = {
            "race": "바바리안",
            "hp": 100,
            "hp_max": 100,
            "level": 1,
            "physical": 12,
            "strength": 14,
            "grade": 1,
            "class_type": "warrior",
        }
    return {
        "work_name": "1층",
        "work_genre": "판타지",
        "world_setting": "라프도니아",
        "world_tone": "차분",
        "world_rules": ["1층 어둠"],
        "main_character_name": party_names[0] if party_names else "",
        "main_character_role": "주인공",
        "supporting_characters": [],
        "current_location": "1층 진입점",
        "current_turn": 0,
        "v2_characters": chars,
        "v2_world_state": {
            "party_members": party_names,
            "max_party_members": 5,
        },
    }


def test_prompt_solo_warning_20hwa() -> None:
    """1인 → 20화 narrative hint."""
    prompt = _gm_system_prompt(_base_ctx(["비요른"]))
    assert "1인 진입" in prompt
    assert "20화" in prompt
    assert "44화" in prompt


def test_prompt_full_team_recommended_44hwa() -> None:
    """4+인 → 팀 권장 hint."""
    prompt = _gm_system_prompt(
        _base_ctx(["비요른", "에르웬", "투르윈", "셰인"])
    )
    assert "팀 구성" in prompt
    assert "44화" in prompt


def test_prompt_two_persons_no_hint() -> None:
    """2-3인 → narrative 중립 (★ hint 없음)."""
    prompt = _gm_system_prompt(_base_ctx(["비요른", "에르웬"]))
    assert "1인 진입" not in prompt
    assert "팀 구성" not in prompt


def test_prompt_three_persons_no_hint() -> None:
    prompt = _gm_system_prompt(
        _base_ctx(["비요른", "에르웬", "투르윈"])
    )
    assert "1인 진입" not in prompt
    assert "팀 구성" not in prompt


def test_prompt_dead_solo_no_solo_hint() -> None:
    """살아있는 멤버 0 → 1인 hint 본격 X (★ alive count 정합)."""
    ctx = _base_ctx(["비요른"])
    ctx["v2_characters"]["비요른"]["hp"] = 0
    prompt = _gm_system_prompt(ctx)
    assert "1인 진입" not in prompt


def test_prompt_full_team_with_one_dead() -> None:
    """5인 중 1명 사망 → alive 4 본격 팀 hint 유지."""
    ctx = _base_ctx(["비요른", "에르웬", "투르윈", "셰인", "M4"])
    ctx["v2_characters"]["M4"]["hp"] = 0
    prompt = _gm_system_prompt(ctx)
    assert "팀 구성" in prompt
