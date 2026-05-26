"""Phase 9.15 guild-discount — 프라일 호감도 → recruit 비용 할인.

검증 본질 (★ 9.13 신전 정합 — 추가 dead consumer 방지):
- _guild_recruit_discount threshold (★ 25/50 정합)
- execute_recruit_from_guild 본격 effective_cost 적용
- 비용 부족 시 mutation X (★ atomic)
- 메시지 본격 할인 % 표시
- gm_agent explorer_guild_branch hint 본격 effective_cost + discount

본문 X — 추측 (★ docstring 명시):
- 9.13 신전 할인 수치 정합 (★ -20% / -50%)
"""

from __future__ import annotations

import random
from typing import Any

from service.game.gm_agent import _format_city_context
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    AFFINITY_THRESHOLD_TIER1,
    AFFINITY_THRESHOLD_TIER2,
    GUILD_CLERK_NPC_ID,
    GUILD_DISCOUNT_MULTIPLIER_TIER1,
    GUILD_DISCOUNT_MULTIPLIER_TIER2,
    RECRUIT_BASE_COST,
    _guild_recruit_discount,
    execute_recruit_from_guild,
)

# ─── 1. _guild_recruit_discount threshold ───


def test_discount_low_affinity_baseline() -> None:
    assert _guild_recruit_discount(0) == 1.0
    assert _guild_recruit_discount(24) == 1.0


def test_discount_tier1_at_25() -> None:
    assert _guild_recruit_discount(25) == GUILD_DISCOUNT_MULTIPLIER_TIER1
    assert _guild_recruit_discount(49) == GUILD_DISCOUNT_MULTIPLIER_TIER1


def test_discount_tier2_at_50() -> None:
    assert _guild_recruit_discount(50) == GUILD_DISCOUNT_MULTIPLIER_TIER2
    assert _guild_recruit_discount(100) == GUILD_DISCOUNT_MULTIPLIER_TIER2


def test_threshold_matches_9_13() -> None:
    """9.13 신전 정합 — 25 / 50 본격."""
    assert AFFINITY_THRESHOLD_TIER1 == 25
    assert AFFINITY_THRESHOLD_TIER2 == 50


# ─── 2. execute_recruit_from_guild wire ───


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


def _bjorn(stone: int = 10000) -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        stone=stone,
        grade=1,
    )


def test_recruit_zero_affinity_baseline() -> None:
    world = _village_world()
    actor = _bjorn()
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert result.success is True
    assert actor.stone == 10000 - RECRUIT_BASE_COST


def test_recruit_tier1_discount_25() -> None:
    """affinity 25 → -20% → 5000 → 4000."""
    world = _village_world()
    world.npc_affinities[GUILD_CLERK_NPC_ID] = 25
    actor = _bjorn()
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert result.success is True
    expected = int(RECRUIT_BASE_COST * 0.80)
    assert actor.stone == 10000 - expected


def test_recruit_tier2_discount_50() -> None:
    """affinity 50 → -50% → 5000 → 2500."""
    world = _village_world()
    world.npc_affinities[GUILD_CLERK_NPC_ID] = 50
    actor = _bjorn()
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert result.success is True
    expected = int(RECRUIT_BASE_COST * 0.50)
    assert actor.stone == 10000 - expected


def test_recruit_insufficient_after_discount_fails_atomic() -> None:
    """tier2 effective 2500, actor stone 2400 → fail + mutation X."""
    world = _village_world()
    world.npc_affinities[GUILD_CLERK_NPC_ID] = 50
    actor = _bjorn(stone=2400)
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert result.success is False
    assert "2400" in result.message
    assert "2500" in result.message
    assert actor.stone == 2400  # ★ atomic — mutation X
    assert len(party) == 1


def test_recruit_at_exact_discounted_cost_works() -> None:
    """tier2 2500 + actor stone 2500 → 성공, stone = 0."""
    world = _village_world()
    world.npc_affinities[GUILD_CLERK_NPC_ID] = 50
    actor = _bjorn(stone=2500)
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert result.success is True
    assert actor.stone == 0


def test_recruit_side_effect_shows_discounted_cost() -> None:
    world = _village_world()
    world.npc_affinities[GUILD_CLERK_NPC_ID] = 50
    actor = _bjorn()
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    expected = int(RECRUIT_BASE_COST * 0.50)
    assert any(
        s == f"stone_paid=비요른:-{expected}" for s in result.side_effects
    )


def test_recruit_message_shows_tier2_discount_pct() -> None:
    world = _village_world()
    world.npc_affinities[GUILD_CLERK_NPC_ID] = 50
    actor = _bjorn()
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert "-50%" in result.message


def test_recruit_message_shows_tier1_discount_pct() -> None:
    world = _village_world()
    world.npc_affinities[GUILD_CLERK_NPC_ID] = 25
    actor = _bjorn()
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert "-20%" in result.message


def test_recruit_baseline_no_discount_message() -> None:
    world = _village_world()
    actor = _bjorn()
    party = [actor]
    rng = random.Random(42)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert "boost" not in result.message


# ─── 3. gm_agent prompt 본격 effective_cost + discount ───


def _guild_ctx(affinity: int = 0) -> dict[str, Any]:
    return {
        "main_character_name": "비요른",
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "explorer_guild_branch",
            "city_id": "rascania",
        },
        "v2_world_state": {
            "max_party_members": 5,
            "party_members": ["비요른"],
            "npc_affinities": {GUILD_CLERK_NPC_ID: affinity},
        },
        "v2_characters": {
            "비요른": {
                "race": "바바리안",
                "hp": 100,
                "hp_max": 100,
                "level": 1,
                "grade": 1,
                "class_type": "warrior",
            },
        },
    }


def test_prompt_baseline_shows_full_cost() -> None:
    out = _format_city_context(_guild_ctx(affinity=10))
    assert f"비용 {RECRUIT_BASE_COST} 스톤" in out
    assert "비용 -" not in out


def test_prompt_tier1_shows_discounted_cost() -> None:
    out = _format_city_context(_guild_ctx(affinity=30))
    expected = int(RECRUIT_BASE_COST * 0.80)
    assert f"비용 {expected} 스톤" in out
    assert "비용 -20%" in out


def test_prompt_tier2_shows_discounted_cost() -> None:
    out = _format_city_context(_guild_ctx(affinity=70))
    expected = int(RECRUIT_BASE_COST * 0.50)
    assert f"비용 {expected} 스톤" in out
    assert "비용 -50%" in out
