"""50턴 GM + Player encounter 보강 후 다양성 본격 검증 (★ slow).

본 commit (★ A. encounter 빈도/다양/누적):
- C ceiling 4/13 진짜 해소 시도
- TTL 누적 + 직전 type 차단 + 빈도 ↑

진짜 입증 (★ DGX Spark):
- C baseline: move 56% + use_item 32% + explore 8% + activate_light 4%
- 본 commit: activate_light 48% + absorb_essence 44% + move 4% + use_item 4%
  → 새 ActionType ABSORB_ESSENCE 본격 발현 (★ GM essence spawn 흐름 진짜)

8+ 미달 finding (★ 정직):
- root cause 1 (★ GM 다양) + 4 (★ 빈도) + 5 (★ 누적) 직접 답했지만
- root cause 2 (★ Player 익숙 도피) + 3 (★ 9B 한계)는 미답
- = 후속 B commit (★ 27B Player) 본격 시점
"""

from __future__ import annotations

import pytest
import requests

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.analyzer import analyze_sim_result
from service.sim.llm_factory import (
    QWEN35_9B_Q3_BASE_URL,
    QWEN36_27B_Q2_BASE_URL,
    make_gm_llm_client,
    make_player_llm_client,
)
from service.sim.player_agent import PlayerAgent
from service.sim.sim_gm_agent import SimGMAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerActionType, SimConfig


def _alive(url: str) -> bool:
    try:
        return requests.get(f"{url}/v1/models", timeout=2).status_code == 200
    except requests.RequestException:
        return False


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not _alive(QWEN35_9B_Q3_BASE_URL)
        or not _alive(QWEN36_27B_Q2_BASE_URL),
        reason="8082 또는 8083 X — DGX Spark 한정",
    ),
]


def test_50turn_encounter_boost_absorb_emerges() -> None:
    """50턴 → ABSORB_ESSENCE 본격 발현 입증 (★ 새 ActionType, GM 흐름).

    diversity >= 4 (★ C ceiling 유지하지만 분포 본격 변화)
    ABSORB_ESSENCE 본격 발현 (★ GM essence spawn 흐름 진짜)
    """
    player_agent = PlayerAgent(llm_client=make_player_llm_client())
    gm_agent = SimGMAgent(llm_client=make_gm_llm_client())

    config = SimConfig(
        max_turns=50,
        scenario_id="encounter_boost_test",
        player_llm_model="qwen35_9b_q3",
        gm_llm_model="qwen36_27b_q2",
    )
    runner = SimRunner(
        config=config,
        player_agent=player_agent,
        gm_agent=gm_agent,
    )

    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            physical=14,
            strength=16,
            bone_strength=12,
            is_player=True,
        ),
        "에르웬": Character(
            name="에르웬",
            race=Race.FAERIE,
            hp=90,
            hp_max=90,
            soul_power=60,
            soul_power_max=60,
        ),
    }
    world = WorldState(
        current_round=1,
        hours_in_dungeon=0,
        is_dark_zone=True,
        party_members=["비요른", "에르웬"],
    )
    location = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="진입점",
        visibility_meters=10,
        has_light=False,
    )
    game_ctx = {
        "v2_characters": {
            n: {
                "hp": c.hp,
                "hp_max": c.hp_max,
                "race": c.race.value,
                "has_active_light": c.has_active_light(),
                "essence_slots_used": c.essence_slots_used(),
            }
            for n, c in party.items()
        },
        "v2_world_state": {
            "hours_in_dungeon": 0,
            "party_members": ["비요른", "에르웬"],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "진입점",
            "visibility_meters": 10,
            "has_light": False,
        },
    }

    result = runner.run(
        party=party,
        world=world,
        location=location,
        game_context=game_ctx,
    )
    analysis = analyze_sim_result(result)

    # 본격 입증 1: diversity ≥ 4 (★ C ceiling 유지)
    assert analysis.diversity_score >= 4, (
        f"diversity {analysis.diversity_score}/13 — C ceiling 4 회귀"
    )

    # 본격 입증 2: ABSORB_ESSENCE 본격 발현 (★ 본 commit 진짜 finding)
    used_types = {f.action_type for f in analysis.action_frequencies}
    assert PlayerActionType.ABSORB_ESSENCE in used_types, (
        "ABSORB_ESSENCE 미발현 — GM essence spawn 흐름 X"
    )
