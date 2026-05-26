"""Phase 9.9-d actor-grade-range — 본인 grade 본격 모집 grade range.

검증 본질:
- _max_recruit_grade 매핑 (★ (actor_grade + 1) // 2)
  * grade 1 → 1, grade 3 → 2, grade 5 → 3, grade 9 → 5
  * grade 0/음수 → 1 fallback
- _create_recruit_character signature 변경:
  (actor_race, actor_grade, guild_clerk_affinity, rng)
- 신참 grade = rng.randint(1, max_recruit_grade)
- execute_recruit_from_guild 본격 actor.grade 전달 wire
- gm_agent prompt 본격 grade range hint

본문 정합:
- 73화: 5등급 정수 2개 = 상위 탐험가
- 20화: 중층 = 6층 진입
- 28화: 6등급 마법사

추측 (본문 X — docstring 명시):
- (actor_grade + 1) // 2 공식
"""

from __future__ import annotations

import random
from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    ClassType,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    GUILD_CLERK_NPC_ID,
    _create_recruit_character,
    _max_recruit_grade,
    execute_recruit_from_guild,
)

# ─── 1. _max_recruit_grade 매핑 ───


def test_max_grade_1_returns_1() -> None:
    assert _max_recruit_grade(1) == 1


def test_max_grade_2_returns_1() -> None:
    """(2+1)//2 = 1."""
    assert _max_recruit_grade(2) == 1


def test_max_grade_3_returns_2() -> None:
    assert _max_recruit_grade(3) == 2


def test_max_grade_5_returns_3_73hwa() -> None:
    """73화 본문 정합 — 5등급 = 상위 탐험가 본격 신참 grade 3 본격 모집."""
    assert _max_recruit_grade(5) == 3


def test_max_grade_7_returns_4() -> None:
    assert _max_recruit_grade(7) == 4


def test_max_grade_9_returns_5() -> None:
    assert _max_recruit_grade(9) == 5


def test_max_grade_0_returns_1_fallback() -> None:
    """edge — 본인 grade 0 → 1 fallback."""
    assert _max_recruit_grade(0) == 1


def test_max_grade_negative_returns_1_fallback() -> None:
    assert _max_recruit_grade(-3) == 1


# ─── 2. _create_recruit_character signature + grade range ───


def test_signature_accepts_actor_grade() -> None:
    rng = random.Random(42)
    c = _create_recruit_character("인간", 1, 0, rng)
    assert c.race.value in {r.value for r in Race}
    assert c.class_type == ClassType.WARRIOR.value
    assert c.level == 1


def test_actor_grade_1_recruit_always_grade_1() -> None:
    """본인 1등급 → 신참 grade 1만 (★ randint(1,1))."""
    for seed in range(50):
        rng = random.Random(seed)
        c = _create_recruit_character("인간", 1, 0, rng)
        assert c.grade == 1


def test_actor_grade_5_recruit_grade_1_to_3() -> None:
    """본인 5등급 → 신참 grade 1~3 본격."""
    grades_seen: set[int] = set()
    for seed in range(100):
        rng = random.Random(seed)
        c = _create_recruit_character("인간", 5, 0, rng)
        grades_seen.add(c.grade)
    assert min(grades_seen) >= 1
    assert max(grades_seen) <= 3
    # 본인 답 정합 — 변동성 검증 (★ 1, 2, 3 다양)
    assert len(grades_seen) >= 2


def test_actor_grade_9_recruit_grade_1_to_5() -> None:
    grades_seen: set[int] = set()
    for seed in range(100):
        rng = random.Random(seed)
        c = _create_recruit_character("인간", 9, 0, rng)
        grades_seen.add(c.grade)
    assert min(grades_seen) >= 1
    assert max(grades_seen) <= 5


def test_actor_grade_0_recruit_grade_1_fallback() -> None:
    """edge — 본인 grade 0 → 신참 grade 1."""
    rng = random.Random(42)
    c = _create_recruit_character("인간", 0, 0, rng)
    assert c.grade == 1


# ─── 3. execute_recruit_from_guild caller wire ───


def _guild_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="explorer_guild_branch",
        city_id="rascania",
    )


def _village_world() -> WorldState:
    w = WorldState(party_members=["비요른"])
    w.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    return w


def test_low_grade_actor_recruits_grade_1() -> None:
    world = _village_world()
    actor = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        stone=10000,
        grade=1,
    )
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert result.success is True
    assert len(party) == 2
    assert party[1].grade == 1


def test_high_grade_actor_recruits_within_range() -> None:
    """본인 7등급 → 신참 grade 1~4 본격."""
    grades_seen: set[int] = set()
    for seed in range(50):
        world = _village_world()
        actor = Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            stone=10000,
            grade=7,
        )
        party = [actor]
        rng = random.Random(seed)
        result = execute_recruit_from_guild(
            "비요른", party, world, _guild_loc(), rng=rng
        )
        assert result.success is True
        grades_seen.add(party[1].grade)
    assert min(grades_seen) >= 1
    assert max(grades_seen) <= 4  # ★ (7+1)//2 = 4


def test_recruit_message_shows_grade() -> None:
    world = _village_world()
    actor = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        stone=10000,
        grade=5,
    )
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert result.success is True
    assert "등급" in result.message


# ─── 4. gm_agent prompt grade range hint ───


def _base_ctx() -> dict[str, Any]:
    return {
        "work_name": "1층",
        "work_genre": "판타지",
        "world_setting": "라스카니아",
        "world_tone": "차분",
        "world_rules": ["1층 어둠"],
        "main_character_name": "비요른",
        "main_character_role": "주인공",
        "supporting_characters": [],
        "current_location": "라스카니아",
        "current_turn": 0,
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "explorer_guild_branch",
            "city_id": "rascania",
        },
    }


def _ctx_with_leader_grade(grade: int) -> dict[str, Any]:
    ctx = _base_ctx()
    ctx["v2_world_state"] = {
        "max_party_members": 5,
        "party_members": ["비요른"],
        "npc_affinities": {GUILD_CLERK_NPC_ID: 10},
    }
    ctx["v2_characters"] = {
        "비요른": {
            "race": "바바리안",
            "hp": 100,
            "hp_max": 100,
            "level": 1,
            "experience": 0,
            "physical": 14,
            "strength": 16,
            "grade": grade,
            "class_type": "warrior",
        },
    }
    return ctx


def test_prompt_grade_1_shows_recruit_grade_1() -> None:
    prompt = _gm_system_prompt(_ctx_with_leader_grade(1))
    assert "비요른 1등급" in prompt
    assert "신참 grade 1~1" in prompt


def test_prompt_grade_5_shows_recruit_grade_1_to_3() -> None:
    prompt = _gm_system_prompt(_ctx_with_leader_grade(5))
    assert "비요른 5등급" in prompt
    assert "신참 grade 1~3" in prompt


def test_prompt_grade_9_shows_recruit_grade_1_to_5() -> None:
    prompt = _gm_system_prompt(_ctx_with_leader_grade(9))
    assert "신참 grade 1~5" in prompt


def test_prompt_missing_grade_defaults_to_1() -> None:
    """v2_characters 없을 때 leader_grade default 1 → max 1."""
    ctx = _base_ctx()
    ctx["v2_world_state"] = {
        "max_party_members": 5,
        "party_members": ["비요른"],
        "npc_affinities": {GUILD_CLERK_NPC_ID: 10},
    }
    prompt = _gm_system_prompt(ctx)
    assert "신참 grade 1~1" in prompt


def test_prompt_full_party_no_grade_hint() -> None:
    """파티 만석 → grade range hint 본격 X."""
    ctx = _ctx_with_leader_grade(5)
    ws = ctx["v2_world_state"]
    ws["party_members"] = ["비요른", "a", "b", "c", "d"]
    prompt = _gm_system_prompt(ctx)
    assert "신참 grade" not in prompt
    assert "만석" in prompt
