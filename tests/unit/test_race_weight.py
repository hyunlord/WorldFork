"""Phase 9.9-c race-weight — 종족 가중치 + 상성 + 호감도 boost 본격 unit.

검증 본질:
- GUILD_RECRUITABLE_RACES 6 종족 (★ 본문 43화 정합)
- RACE_BASE_WEIGHT (★ 인간 50, 용인족 1, 바바리안 4)
- _race_relation_multiplier:
  * 같은 종족 → ×2
  * 양방향 적대 (바바리안 ↔ 요정) — 9화
  * 단방향 적대 (인간 → 바바리안) — 44/97/119화 본인 답
  * 친화 (바바리안 ↔ 드워프) — 8화
  * 중립 default
- _affinity_boost_multiplier:
  * ≥50 → 용인족 ×10
  * ≥25 → 바바리안/용인족 ×2
  * 그 외 ×1.0
- _compute_race_weights / _weighted_random_race
- _create_recruit_character signature (actor_race, affinity, rng)
- execute_recruit_from_guild 본격 actor race + 호감도 wire
- gm_agent prompt 호감도 boost hint

본문 정합 strict:
- 43화: 6 종족
- 9화: 바바리안 ↔ 요정 적대
- 8화: 바바리안 ↔ 드워프 호방 친화
- 44/97/119화: 인간 → 바바리안 단방향 차별
- 123화: 용인족 캐릭터 차단 + 바바리안 채팅방 0명
"""

from __future__ import annotations

import random
from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    FRIENDLY_MULTIPLIER,
    GUILD_CLERK_NPC_ID,
    GUILD_RECRUITABLE_RACES,
    HOSTILE_MULTIPLIER,
    NEUTRAL_MULTIPLIER,
    RACE_BASE_WEIGHT,
    RARE_RACE_AFFINITY_MULTIPLIER,
    SAME_RACE_MULTIPLIER,
    UNCOMMON_RACE_AFFINITY_MULTIPLIER,
    _affinity_boost_multiplier,
    _compute_race_weights,
    _create_recruit_character,
    _race_relation_multiplier,
    _weighted_random_race,
    execute_recruit_from_guild,
)

# ─── 1. 6 종족 list (★ 본문 43화) ───


def test_six_races_43hwa() -> None:
    """43화 본문 정합 — 6 종족."""
    assert len(GUILD_RECRUITABLE_RACES) == 6
    assert set(GUILD_RECRUITABLE_RACES) == {
        "인간",
        "드워프",
        "수인",
        "요정",
        "바바리안",
        "용인족",
    }


# ─── 2. RACE_BASE_WEIGHT ───


def test_human_weight_50() -> None:
    assert RACE_BASE_WEIGHT["인간"] == 50


def test_barbarian_uncommon_4_123hwa() -> None:
    """123화 본문 정합 — 바바리안 채팅방 0명."""
    assert RACE_BASE_WEIGHT["바바리안"] == 4


def test_dragonkin_rare_1_123hwa() -> None:
    """123화 본문 정합 — 용인족 캐릭터 선택 차단."""
    assert RACE_BASE_WEIGHT["용인족"] == 1


def test_all_races_have_weight() -> None:
    for r in GUILD_RECRUITABLE_RACES:
        assert r in RACE_BASE_WEIGHT
        assert RACE_BASE_WEIGHT[r] > 0


# ─── 3. _race_relation_multiplier (★ 본문 strict) ───


def test_same_race_x2() -> None:
    assert _race_relation_multiplier("인간", "인간") == SAME_RACE_MULTIPLIER
    assert _race_relation_multiplier(
        "바바리안", "바바리안"
    ) == SAME_RACE_MULTIPLIER


def test_barbarian_faerie_hostile_bidirectional_9hwa() -> None:
    """9화 본문 정합 — 바바리안 ↔ 요정 적대 (★ 양방향)."""
    assert _race_relation_multiplier("바바리안", "요정") == HOSTILE_MULTIPLIER
    assert _race_relation_multiplier("요정", "바바리안") == HOSTILE_MULTIPLIER


def test_barbarian_dwarf_friendly_8hwa() -> None:
    """8화 본문 정합 — 바바리안 ↔ 드워프 호방 (★ 양방향)."""
    assert (
        _race_relation_multiplier("바바리안", "드워프")
        == FRIENDLY_MULTIPLIER
    )
    assert (
        _race_relation_multiplier("드워프", "바바리안")
        == FRIENDLY_MULTIPLIER
    )


def test_human_barbarian_hostile_oneway_44hwa() -> None:
    """44/97/119화 본문 + 본인 답 — 인간 → 바바리안 단방향."""
    assert (
        _race_relation_multiplier("인간", "바바리안") == HOSTILE_MULTIPLIER
    )
    # 바바리안 → 인간 = 중립 (★ 본문 strict, 본인 답)
    assert (
        _race_relation_multiplier("바바리안", "인간") == NEUTRAL_MULTIPLIER
    )


def test_neutral_default() -> None:
    assert _race_relation_multiplier("인간", "드워프") == NEUTRAL_MULTIPLIER
    assert _race_relation_multiplier("수인", "요정") == NEUTRAL_MULTIPLIER


# ─── 4. _affinity_boost_multiplier ───


def test_rare_boost_dragonkin_50() -> None:
    """affinity ≥ 50 + 용인족 → ×10."""
    assert (
        _affinity_boost_multiplier("용인족", 50)
        == RARE_RACE_AFFINITY_MULTIPLIER
    )


def test_uncommon_boost_barbarian_25() -> None:
    """affinity ≥ 25 + 바바리안 → ×2."""
    assert (
        _affinity_boost_multiplier("바바리안", 25)
        == UNCOMMON_RACE_AFFINITY_MULTIPLIER
    )


def test_uncommon_boost_dragonkin_25_to_49() -> None:
    """affinity 25-49 + 용인족 → ×2 (★ ×10 본격 X)."""
    assert (
        _affinity_boost_multiplier("용인족", 25)
        == UNCOMMON_RACE_AFFINITY_MULTIPLIER
    )
    assert (
        _affinity_boost_multiplier("용인족", 49)
        == UNCOMMON_RACE_AFFINITY_MULTIPLIER
    )


def test_no_boost_low_affinity() -> None:
    assert _affinity_boost_multiplier("바바리안", 20) == 1.0
    assert _affinity_boost_multiplier("용인족", 0) == 1.0


def test_no_boost_common_race() -> None:
    """인간/드워프 본격 boost 본격 X (★ 호감도 높아도)."""
    assert _affinity_boost_multiplier("인간", 100) == 1.0
    assert _affinity_boost_multiplier("드워프", 100) == 1.0
    assert _affinity_boost_multiplier("요정", 100) == 1.0
    assert _affinity_boost_multiplier("수인", 100) == 1.0


# ─── 5. _compute_race_weights ───


def test_barbarian_actor_dwarf_friendly() -> None:
    """바바리안 actor → 드워프 ×1.5 (★ 친화)."""
    weights = _compute_race_weights("바바리안", 0)
    assert weights["드워프"] == 15 * 1.5


def test_barbarian_actor_faerie_hostile() -> None:
    """바바리안 actor → 요정 ×0.3 (★ 적대)."""
    weights = _compute_race_weights("바바리안", 0)
    assert weights["요정"] == 15 * 0.3


def test_barbarian_actor_same_race_x2() -> None:
    weights = _compute_race_weights("바바리안", 0)
    assert weights["바바리안"] == 4 * 2.0


def test_human_actor_barbarian_hostile() -> None:
    """인간 actor → 바바리안 ×0.3 (★ 44화 단방향)."""
    weights = _compute_race_weights("인간", 0)
    assert weights["바바리안"] == 4 * 0.3
    assert weights["인간"] == 50 * 2.0  # ★ 같은 종족


def test_high_affinity_boosts_dragonkin() -> None:
    low = _compute_race_weights("인간", 0)
    high = _compute_race_weights("인간", 50)
    assert (
        high["용인족"] == low["용인족"] * RARE_RACE_AFFINITY_MULTIPLIER
    )


# ─── 6. _weighted_random_race ───


def test_weighted_random_deterministic_with_seed() -> None:
    weights = _compute_race_weights("인간", 0)
    a = _weighted_random_race(weights, random.Random(42))
    b = _weighted_random_race(weights, random.Random(42))
    assert a == b


def test_weighted_random_returns_valid_race() -> None:
    weights = _compute_race_weights("인간", 0)
    race = _weighted_random_race(weights, random.Random(42))
    assert race in GUILD_RECRUITABLE_RACES


def test_weighted_random_zero_total_fallback() -> None:
    """모든 가중치 0 → fallback 인간."""
    weights = {r: 0.0 for r in GUILD_RECRUITABLE_RACES}
    race = _weighted_random_race(weights, random.Random(0))
    assert race == "인간"


# ─── 7. _create_recruit_character ───


def test_create_recruit_signature() -> None:
    """signature (actor_race, affinity, rng)."""
    rng = random.Random(42)
    c = _create_recruit_character("인간", 0, rng)
    assert c.race.value in GUILD_RECRUITABLE_RACES
    assert c.level == 1
    assert c.grade == 1
    assert c.class_type == "warrior"


def test_create_recruit_barbarian_pool_includes_self() -> None:
    """바바리안 actor + affinity=50 → 바바리안 등장 가능 (★ 본인 답 1번)."""
    races_seen: set[str] = set()
    for seed in range(200):
        rng = random.Random(seed)
        c = _create_recruit_character("바바리안", 50, rng)
        races_seen.add(c.race.value)
    assert "바바리안" in races_seen


# ─── 8. execute_recruit_from_guild wire ───


def _guild_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="explorer_guild_branch",
        city_id="rapdonia",
    )


def test_recruit_uses_actor_race_and_affinity() -> None:
    world = WorldState(party_members=["비요른"])
    world.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    world.npc_affinities[GUILD_CLERK_NPC_ID] = 50
    actor = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        stone=10000,
    )
    party = [actor]
    rng = random.Random(0)
    result = execute_recruit_from_guild(
        "비요른", party, world, _guild_loc(), rng=rng
    )
    assert result.success is True
    assert len(party) == 2
    assert party[1].race.value in GUILD_RECRUITABLE_RACES


# ─── 9. gm_agent prompt hint ───


def _base_ctx() -> dict[str, Any]:
    return {
        "work_name": "1층",
        "work_genre": "판타지",
        "world_setting": "라프도니아",
        "world_tone": "차분",
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


def test_prompt_low_affinity_baseline_hint() -> None:
    ctx = _base_ctx()
    ctx["v2_world_state"] = {
        "max_party_members": 5,
        "party_members": ["비요른"],
        "npc_affinities": {GUILD_CLERK_NPC_ID: 10},
    }
    prompt = _gm_system_prompt(ctx)
    assert "RECRUIT_FROM_GUILD" in prompt
    assert "프라일 호감도 10" in prompt
    assert "×10" not in prompt
    assert "×2" not in prompt


def test_prompt_uncommon_boost_25() -> None:
    ctx = _base_ctx()
    ctx["v2_world_state"] = {
        "max_party_members": 5,
        "party_members": ["비요른"],
        "npc_affinities": {GUILD_CLERK_NPC_ID: 30},
    }
    prompt = _gm_system_prompt(ctx)
    assert "바바리안/용인족 확률 ×2" in prompt


def test_prompt_rare_boost_50() -> None:
    ctx = _base_ctx()
    ctx["v2_world_state"] = {
        "max_party_members": 5,
        "party_members": ["비요른"],
        "npc_affinities": {GUILD_CLERK_NPC_ID: 60},
    }
    prompt = _gm_system_prompt(ctx)
    assert "용인족 등장 확률 ×10" in prompt
