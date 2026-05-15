"""Phase 9.9-a guild-recruit — 길드 모집 minimal 본격 unit.

검증 본질:
- WorldState.max_party_members default 5 (★ 본인 답)
- _create_recruit_character: random 종족 / level 1 / 기본 stat
- execute_recruit_from_guild:
  * realm=CITY + sub_area=explorer_guild_branch 검증
  * 빈자리 검증
  * 비용 검증 (★ 5000 스톤)
  * party + world.party_members append
  * side_effects: member_recruited / stone_paid
  * atomic (★ fail 시 mutation X)
- 길드 NPC 본격 (★ frail_guild_clerk in explorer_guild_branch)
- gm_agent prompt 본격 guild hint

본문 정합:
- 6화 mention만 (★ '동료를 구하거나'), namu §7.1
- 본 commit minimal — 9.9-b/c/d 후속
"""

from __future__ import annotations

import random
from typing import Any

from service.game.cities.rapdonia import RAPDONIA, RAPDONIA_NPCS
from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    GUILD_RECRUITABLE_RACES,
    RECRUIT_BASE_COST,
    _create_recruit_character,
    execute_recruit_from_guild,
)

# ─── 1. WorldState.max_party_members ───


def test_world_state_max_party_default_5() -> None:
    """본인 답 정합: 기본 5."""
    w = WorldState()
    assert w.max_party_members == 5


# ─── 2. GUILD_RECRUITABLE_RACES ───


def test_six_races_recruitable() -> None:
    """Race enum 정합 6 종족."""
    assert len(GUILD_RECRUITABLE_RACES) == 6
    assert "용인족" in GUILD_RECRUITABLE_RACES
    assert "바바리안" in GUILD_RECRUITABLE_RACES


def test_all_races_in_enum() -> None:
    enum_values = {r.value for r in Race}
    for race in GUILD_RECRUITABLE_RACES:
        assert race in enum_values


# ─── 3. _create_recruit_character ───


def test_recruit_random_race_in_pool() -> None:
    rng = random.Random(42)
    c = _create_recruit_character("인간", 1, 0, rng)
    assert c.race.value in GUILD_RECRUITABLE_RACES


def test_recruit_level_1_newbie() -> None:
    rng = random.Random(42)
    c = _create_recruit_character("인간", 1, 0, rng)
    assert c.level == 1
    assert c.experience == 0


def test_recruit_default_stat() -> None:
    rng = random.Random(42)
    c = _create_recruit_character("인간", 1, 0, rng)
    assert c.hp == 100
    assert c.hp_max == 100
    assert c.soul_power == 20
    assert c.soul_power_max == 20
    assert c.stone == 0


def test_recruit_reproducible_with_seed() -> None:
    a = _create_recruit_character("인간", 1, 0, random.Random(42))
    b = _create_recruit_character("인간", 1, 0, random.Random(42))
    assert a.name == b.name
    assert a.race == b.race


# ─── 4. execute_recruit_from_guild ───


def _guild_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="explorer_guild_branch",
        city_id="rapdonia",
    )


def _plaza_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="district_7_plaza",
        city_id="rapdonia",
    )


def _dungeon_loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


def _bjorn(stone: int = 10000) -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        stone=stone,
    )


def test_recruit_success_appends_member() -> None:
    world = WorldState(party_members=["비요른"])
    actor = _bjorn()
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert result.success is True
    assert len(party) == 2
    assert actor.stone == 10000 - RECRUIT_BASE_COST
    assert len(world.party_members) == 2
    assert party[1].name in world.party_members


def test_recruit_outside_city_fails() -> None:
    world = WorldState(party_members=["비요른"])
    actor = _bjorn()
    party = [actor]
    result = execute_recruit_from_guild(
        "비요른", party, world, _dungeon_loc()
    )
    assert result.success is False
    assert len(party) == 1


def test_recruit_wrong_sub_area_fails() -> None:
    world = WorldState(party_members=["비요른"])
    actor = _bjorn()
    party = [actor]
    result = execute_recruit_from_guild(
        "비요른", party, world, _plaza_loc()
    )
    assert result.success is False
    assert "지부" in result.message


def test_recruit_party_full_fails_atomic() -> None:
    world = WorldState(party_members=["비요른"])
    world.max_party_members = 1
    actor = _bjorn()
    party = [actor]
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc()
    )
    assert result.success is False
    assert "만석" in result.message
    assert len(party) == 1
    assert actor.stone == 10000  # ★ atomic — 비용 차감 X


def test_recruit_insufficient_stone_atomic() -> None:
    world = WorldState(party_members=["비요른"])
    actor = _bjorn(stone=100)
    party = [actor]
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc()
    )
    assert result.success is False
    assert "비용" in result.message
    assert len(party) == 1
    assert actor.stone == 100


def test_recruit_actor_not_in_party_fails() -> None:
    world = WorldState(party_members=["투르윈"])
    actor = Character(
        name="투르윈", race=Race.BARBARIAN, hp=150, hp_max=150, stone=10000
    )
    party = [actor]
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc()
    )
    assert result.success is False


def test_recruit_side_effects() -> None:
    world = WorldState(party_members=["비요른"])
    actor = _bjorn()
    party = [actor]
    rng = random.Random(0)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert any(
        s.startswith("member_recruited=") for s in result.side_effects
    )
    assert any(
        s == "stone_paid=비요른:-5000" for s in result.side_effects
    )


# ─── 5. 길드 NPC 본격 ───


def test_frail_guild_clerk_exists() -> None:
    ids = {n.id for n in RAPDONIA_NPCS}
    assert "frail_guild_clerk" in ids


def test_frail_in_explorer_guild_branch() -> None:
    frail = next(
        (n for n in RAPDONIA_NPCS if n.id == "frail_guild_clerk"), None
    )
    assert frail is not None
    assert frail.sub_area_id == "explorer_guild_branch"
    assert frail.is_canonical is False  # ★ placeholder


def test_explorer_guild_branch_has_npc() -> None:
    sub = next(
        s for s in RAPDONIA.sub_areas if s.id == "explorer_guild_branch"
    )
    assert "frail_guild_clerk" in sub.npc_ids


# ─── 6. gm_agent prompt hint ───


def _base_ctx() -> dict[str, Any]:
    return {
        "work_name": "1층 시뮬",
        "work_genre": "판타지",
        "world_setting": "라스카니아 라프도니아",
        "world_tone": "차분/생존",
        "world_rules": ["1층 어둠"],
        "main_character_name": "비요른",
        "main_character_role": "주인공",
        "supporting_characters": [],
        "current_location": "라프도니아",
        "current_turn": 0,
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "explorer_guild_branch",
            "city_id": "rapdonia",
        },
    }


def test_prompt_guild_empty_slot_shows_recruit_hint() -> None:
    ctx = _base_ctx()
    ctx["v2_world_state"] = {
        "max_party_members": 5,
        "party_members": ["비요른"],
    }
    prompt = _gm_system_prompt(ctx)
    assert "RECRUIT_FROM_GUILD" in prompt
    assert "빈자리 4" in prompt


def test_prompt_guild_full_party_shows_capacity() -> None:
    ctx = _base_ctx()
    ctx["v2_world_state"] = {
        "max_party_members": 2,
        "party_members": ["비요른", "에르웬"],
    }
    prompt = _gm_system_prompt(ctx)
    assert "정원 만석" in prompt
    assert "RECRUIT_FROM_GUILD" not in prompt


def test_prompt_non_guild_no_recruit_hint() -> None:
    ctx = _base_ctx()
    ctx["v2_initial_location"] = {
        "realm": "도시",
        "sub_area": "district_7_plaza",
        "city_id": "rapdonia",
    }
    prompt = _gm_system_prompt(ctx)
    assert "RECRUIT_FROM_GUILD" not in prompt
