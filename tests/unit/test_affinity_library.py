"""Phase 9.7 affinity-library — NPC 호감도 + 도서관 서적 탐지 본격 unit.

검증 본질:
- WorldState.npc_affinities default empty
- execute_dialogue:
  * 마을 본격 NPC + 호감도 +5 (★ AFFINITY_DELTA_DIALOGUE)
  * cap 100 (★ AFFINITY_MAX, 643화 본문)
  * 마을 외 / unknown NPC fail
  * id 또는 한국어 name 본격 본격
  * side_effect: affinity_changed
- execute_library_search:
  * central_library 검증
  * 라그나 호감도 < threshold → stone 차감 (★ 3000)
  * 라그나 호감도 ≥ threshold → 무료 (★ 본인 답)
  * 비용 부족 → fail + atomic
  * empty target → fail
  * side_effects: library_search / stone_paid
- gm_agent prompt:
  * NPC + 호감도 표시 (★ DIALOGUE enabler)
  * central_library → fee / 면제 hint

본문 정합:
- 19화: '파르시티에브' 서적 탐지 마법, 사서 졸음, 키워드 본격 책 이끌림
- namu §4.3: 도서관 수수료 3천 스톤
- 643화: 호감도 100 MAX
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    AFFINITY_DELTA_DIALOGUE,
    AFFINITY_MAX,
    LIBRARIAN_NPC_ID,
    LIBRARY_FREE_AFFINITY_THRESHOLD,
    LIBRARY_SEARCH_FEE,
    execute_dialogue,
    execute_library_search,
)

# ─── 1. WorldState.npc_affinities ───


def test_world_state_npc_affinities_default_empty() -> None:
    w = WorldState()
    assert w.npc_affinities == {}


# ─── 2. execute_dialogue ───


def _plaza_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="district_7_plaza",
        city_id="rapdonia",
    )


def _dungeon_loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


def _actor() -> Character:
    return Character(
        name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100
    )


def test_dialogue_increases_affinity_by_5() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_dialogue(
        "비요른", "아이나르", [actor], world, _plaza_loc()
    )
    assert result.success is True
    assert world.npc_affinities["aenar"] == AFFINITY_DELTA_DIALOGUE


def test_dialogue_caps_at_max_100_643hwa() -> None:
    """643화 본문 정합 — 호감도 100 cap."""
    world = WorldState()
    world.npc_affinities["aenar"] = 99
    actor = _actor()
    execute_dialogue("비요른", "아이나르", [actor], world, _plaza_loc())
    assert world.npc_affinities["aenar"] == AFFINITY_MAX


def test_dialogue_outside_city_fails() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_dialogue(
        "비요른", "아이나르", [actor], world, _dungeon_loc()
    )
    assert result.success is False


def test_dialogue_unknown_npc_fails() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_dialogue(
        "비요른", "Nonexistent", [actor], world, _plaza_loc()
    )
    assert result.success is False


def test_dialogue_npc_id_target_works() -> None:
    """target = npc id 본격 본격."""
    world = WorldState()
    actor = _actor()
    result = execute_dialogue(
        "비요른", "aenar", [actor], world, _plaza_loc()
    )
    assert result.success is True
    assert world.npc_affinities["aenar"] == AFFINITY_DELTA_DIALOGUE


def test_dialogue_side_effect_marker() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_dialogue(
        "비요른", "아이나르", [actor], world, _plaza_loc()
    )
    assert any(
        s == "affinity_changed=aenar:0->5" for s in result.side_effects
    )


def test_dialogue_empty_target_fails() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_dialogue("비요른", "", [actor], world, _plaza_loc())
    assert result.success is False


def test_dialogue_actor_not_in_party_fails() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_dialogue(
        "투르윈", "아이나르", [actor], world, _plaza_loc()
    )
    assert result.success is False


# ─── 3. execute_library_search ───


def _library_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="central_library",
        city_id="rapdonia",
    )


def _actor_with_stone(stone: int) -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=100,
        hp_max=100,
        stone=stone,
    )


def test_library_search_low_affinity_charges_fee() -> None:
    """라그나 호감도 0 (★ default) → 수수료 3천 스톤 (★ namu §4.3)."""
    world = WorldState()
    actor = _actor_with_stone(5000)
    result = execute_library_search(
        "비요른", "역사", [actor], world, _library_loc()
    )
    assert result.success is True
    assert actor.stone == 5000 - LIBRARY_SEARCH_FEE


def test_library_search_high_affinity_free() -> None:
    """라그나 호감도 ≥ threshold → 무료 (★ 본인 답)."""
    world = WorldState()
    world.npc_affinities[LIBRARIAN_NPC_ID] = LIBRARY_FREE_AFFINITY_THRESHOLD
    actor = _actor_with_stone(100)  # 본격 본격 부족
    result = execute_library_search(
        "비요른", "역사", [actor], world, _library_loc()
    )
    assert result.success is True
    assert actor.stone == 100  # ★ 면제 본격 변화 X
    assert "면제" in result.message


def test_library_search_insufficient_stone_atomic() -> None:
    """비용 부족 → fail + mutation X (★ atomic)."""
    world = WorldState()
    actor = _actor_with_stone(100)
    pre_stone = actor.stone
    result = execute_library_search(
        "비요른", "역사", [actor], world, _library_loc()
    )
    assert result.success is False
    assert "수수료 부족" in result.message
    assert actor.stone == pre_stone


def test_library_search_wrong_sub_area_fails() -> None:
    world = WorldState()
    actor = _actor_with_stone(5000)
    result = execute_library_search(
        "비요른", "역사", [actor], world, _plaza_loc()
    )
    assert result.success is False


def test_library_search_outside_city_fails() -> None:
    world = WorldState()
    actor = _actor_with_stone(5000)
    result = execute_library_search(
        "비요른", "역사", [actor], world, _dungeon_loc()
    )
    assert result.success is False


def test_library_search_empty_target_fails() -> None:
    world = WorldState()
    actor = _actor_with_stone(5000)
    result = execute_library_search(
        "비요른", "", [actor], world, _library_loc()
    )
    assert result.success is False


def test_library_search_side_effects() -> None:
    world = WorldState()
    actor = _actor_with_stone(5000)
    result = execute_library_search(
        "비요른", "역사", [actor], world, _library_loc()
    )
    assert any(
        s == "library_search=비요른:역사" for s in result.side_effects
    )
    assert any(
        s == "stone_paid=비요른:-3000" for s in result.side_effects
    )


def test_library_search_free_no_stone_paid_marker() -> None:
    """면제 본격 stone_paid marker X."""
    world = WorldState()
    world.npc_affinities[LIBRARIAN_NPC_ID] = 80
    actor = _actor_with_stone(5000)
    result = execute_library_search(
        "비요른", "역사", [actor], world, _library_loc()
    )
    assert not any(
        s.startswith("stone_paid=") for s in result.side_effects
    )


# ─── 4. gm_agent prompt ───


def _base_ctx() -> dict[str, Any]:
    return {
        "work_name": "1층 시뮬",
        "work_genre": "판타지",
        "world_setting": "라스카니아 라프도니아",
        "world_tone": "차분/생존",
        "world_rules": ["1층 어둠 본격"],
        "main_character_name": "비요른",
        "main_character_role": "주인공",
        "supporting_characters": [],
        "current_location": "라프도니아",
        "current_turn": 0,
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "district_7_plaza",
            "city_id": "rapdonia",
        },
    }


def test_prompt_shows_npc_affinity_in_plaza() -> None:
    ctx = _base_ctx()
    ctx["v2_world_state"] = {"npc_affinities": {"aenar": 25}}
    prompt = _gm_system_prompt(ctx)
    assert "아이나르 (호감도 25)" in prompt
    assert "DIALOGUE" in prompt


def test_prompt_shows_default_affinity_0() -> None:
    """npc_affinities 본격 X → 0 default 표시."""
    ctx = _base_ctx()
    prompt = _gm_system_prompt(ctx)
    assert "아이나르 (호감도 0)" in prompt


def test_prompt_library_low_affinity_shows_fee() -> None:
    ctx = _base_ctx()
    ctx["v2_initial_location"] = {
        "realm": "도시",
        "sub_area": "central_library",
        "city_id": "rapdonia",
    }
    prompt = _gm_system_prompt(ctx)
    assert "LIBRARY_SEARCH" in prompt
    assert "수수료 3000 스톤" in prompt
    # ★ 'LIBRARY 수수료 면제' line 본격 본격 X (★ 호감도 본격)
    assert "수수료 면제" not in prompt


def test_prompt_library_high_affinity_shows_free() -> None:
    ctx = _base_ctx()
    ctx["v2_initial_location"] = {
        "realm": "도시",
        "sub_area": "central_library",
        "city_id": "rapdonia",
    }
    ctx["v2_world_state"] = {"npc_affinities": {LIBRARIAN_NPC_ID: 80}}
    prompt = _gm_system_prompt(ctx)
    assert "면제" in prompt
    assert "호감도 80" in prompt


def test_prompt_non_library_no_search_hint() -> None:
    ctx = _base_ctx()
    prompt = _gm_system_prompt(ctx)
    assert "LIBRARY_SEARCH" not in prompt
