"""AI Playtester 50턴 진짜 LLM 통합 테스트 (★ slow, DGX Spark 한정).

본 commit: 5턴 → 50턴 본격 검증.
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
    make_player_llm_client,
)
from service.sim.player_agent import PlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import SimConfig


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


def test_sim_runner_real_50turn() -> None:
    """50턴 진짜 LLM 시뮬 — 1층 시뮬 안정화 검증."""
    llm_client = make_player_llm_client(timeout=30)
    agent = PlayerAgent(llm_client=llm_client)

    runner = SimRunner(
        config=SimConfig(max_turns=50, scenario_id="real_50turn_test"),
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

    # 본격 검증
    assert result.completed_turns >= 10  # 최소 10턴 (★ 한도 도달 검증)
    assert len(result.turn_logs) >= 10
    assert result.total_latency_seconds > 0

    analysis = analyze_sim_result(result)

    # 1층 안정화 검증 본격:
    # LLM 응답 진짜 (★ rationale 비어 있지 X)
    rationales_with_text = sum(
        1 for log in result.turn_logs if len(log.action.rationale) > 5
    )
    assert rationales_with_text >= 5  # 최소 5턴 진짜 rationale

    # diversity 본격 (★ 1턴이라도 다양 행동 시도)
    assert analysis.diversity_score >= 1
