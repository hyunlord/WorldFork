"""AI Playtester 진짜 LLM 통합 테스트 (★ slow 마커, DGX Spark 한정).

8083포트 작동 시만 진짜 호출.
CI / 일반 환경에서는 skip.
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
from service.sim.llm_factory import (
    QWEN35_9B_Q3_BASE_URL,
    make_player_llm_client,
)
from service.sim.player_agent import PlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerActionType, SimConfig


def _llm_server_running() -> bool:
    try:
        resp = requests.get(f"{QWEN35_9B_Q3_BASE_URL}/v1/models", timeout=3)
        return resp.status_code == 200
    except requests.RequestException:
        return False


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not _llm_server_running(),
        reason="qwen35_9b_q3 8083포트 X — DGX Spark 한정",
    ),
]


def test_player_agent_real_llm_returns_valid_action() -> None:
    """진짜 LLM 호출 → 유효 PlayerAction."""
    llm_client = make_player_llm_client(timeout=30)
    agent = PlayerAgent(llm_client=llm_client)

    ctx = {
        "v2_characters": {
            "비요른": {
                "race": "바바리안",
                "hp": 150,
                "hp_max": 150,
                "physical": 14,
                "mental": 14,
                "special": 8,
                "strength": 16,
                "agility": 10,
            },
        },
        "v2_initial_location": {
            "realm": "미궁",
            "floor": 1,
            "sub_area": "진입점",
            "visibility_meters": 10,
            "has_light": False,
        },
        "v2_world_state": {"hours_in_dungeon": 0, "is_dark_zone": True},
    }

    response = agent.generate_action("비요른", ctx)

    assert response.action.actor_name == "비요른"
    assert response.action.action_type in PlayerActionType
    assert response.latency_ms > 0
    assert response.raw_text


def test_sim_runner_real_5turn() -> None:
    """5턴 진짜 LLM 시뮬 — end-to-end."""
    llm_client = make_player_llm_client(timeout=30)
    agent = PlayerAgent(llm_client=llm_client)

    runner = SimRunner(
        config=SimConfig(max_turns=5, scenario_id="real_5turn_test"),
        player_agent=agent,
    )

    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            physical=14,
            strength=16,
            is_player=True,
        ),
    }
    world = WorldState(party_members=["비요른"])
    location = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="진입점",
        visibility_meters=10,
        has_light=False,
    )

    result = runner.run(
        party=party,
        world=world,
        location=location,
        game_context={
            "v2_characters": {
                "비요른": {
                    "race": "바바리안",
                    "hp": 150,
                    "hp_max": 150,
                    "physical": 14,
                    "mental": 14,
                    "special": 8,
                    "strength": 16,
                    "agility": 10,
                },
            },
            "v2_initial_location": {
                "realm": "미궁",
                "floor": 1,
                "sub_area": "진입점",
                "visibility_meters": 10,
                "has_light": False,
            },
            "v2_world_state": {
                "hours_in_dungeon": 0,
                "is_dark_zone": True,
            },
        },
    )

    assert result.completed_turns >= 1
    assert len(result.turn_logs) >= 1
    assert result.total_latency_seconds > 0
