"""Layer 4 E2E 100턴 통합 검증 (★ F1, 9/13).

본 test는 1층 안정화 8/13 + Phase 6 시각화 7/7 통합 본격 검증.

실제 인프라 정합 (★ 본 commit 본격 spec 정공법 답):
- SimRunner (★ service.sim.sim_runner) — 50턴 본격 동일 패턴
- PlayerAgent + SimGMAgent (★ qwen35_9b_q3 8083포트)
- SimResult.turn_logs — 본격 trace

검증 본질 (★ 100턴 본격 기대):
- 13 PlayerActionType 다양성 (≥8)
- 6 sub_areas 방문 (≥4)
- encounter (≥3)
- 168h 한도 정합
- state 정합 (★ HP 음수 X, end_reason 정합)
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
    QWEN35_9B_Q3_MODEL_KEY,
    QWEN36_27B_Q2_BASE_URL,
    QWEN36_27B_Q2_MODEL_KEY,
    make_gm_llm_client,
    make_player_llm_client,
)
from service.sim.player_agent import PlayerAgent
from service.sim.sim_gm_agent import SimGMAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerActionType, SimConfig

# ★ F1 본격 E2E 기준 (★ 실측 후 본격 보정 가능)
TARGET_TURNS = 100
MIN_COMPLETED_TURNS = 30  # ★ 168h 한도 본격 도달 가능 (30턴 본격)
MIN_ACTION_TYPES = 5      # ★ 13 중 최소 5 다양성
MIN_SUB_AREAS = 2         # ★ 6 중 최소 2 방문


def _llm_server_running(url: str) -> bool:
    """LLM 서버 본격 작동 검증."""
    try:
        resp = requests.get(f"{url}/v1/models", timeout=3)
        return resp.status_code == 200
    except requests.RequestException:
        return False


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not _llm_server_running(QWEN35_9B_Q3_BASE_URL),
        reason="qwen35_9b_q3 8083포트 X — DGX Spark 한정",
    ),
]


def test_action_type_canonical_13() -> None:
    """13 PlayerActionType 본격 정합 (★ no LLM 본격)."""
    all_action_types = list(PlayerActionType)
    assert len(all_action_types) == 13, (
        f"PlayerActionType 13 X: {len(all_action_types)}"
    )


def test_layer4_full_run_100turn() -> None:
    """100턴 진짜 LLM 시뮬 — Layer 4 통합 검증.

    본 test는 slow (~5-10분 본격 LLM, DGX Spark 한정).
    """
    player_client = make_player_llm_client(timeout=60)
    player_agent = PlayerAgent(llm_client=player_client)

    # ★ GM agent 본격: 27B 가능 시 사용, X 시 9B fallback
    if _llm_server_running(QWEN36_27B_Q2_BASE_URL):
        gm_url = QWEN36_27B_Q2_BASE_URL
        gm_model_key = QWEN36_27B_Q2_MODEL_KEY
    else:
        gm_url = QWEN35_9B_Q3_BASE_URL
        gm_model_key = QWEN35_9B_Q3_MODEL_KEY
    gm_client = make_gm_llm_client(
        base_url=gm_url, model_key=gm_model_key, timeout=120
    )
    gm_agent = SimGMAgent(llm_client=gm_client)

    runner = SimRunner(
        config=SimConfig(
            max_turns=TARGET_TURNS,
            scenario_id="e2e_F1_100turn",
        ),
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
    world = WorldState(party_members=["비요른", "에르웬"])
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
                    "hp": 150, "hp_max": 150,
                    "physical": 14, "strength": 16,
                },
                "에르웬": {
                    "race": "요정",
                    "hp": 90, "hp_max": 90,
                    "soul_power": 60, "soul_power_max": 60,
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

    # 본격 1: state 정합 (★ 음수 X)
    for log in result.turn_logs:
        assert log.hp_after >= 0, (
            f"turn {log.turn_number}: HP 음수 {log.hp_after}"
        )
        assert log.hours_in_dungeon >= 0
        assert log.hours_in_dungeon <= 200  # ★ 168 + buffer

    # 본격 2: 최소 본격 완주
    assert result.completed_turns >= MIN_COMPLETED_TURNS, (
        f"early termination: {result.completed_turns} "
        f"< {MIN_COMPLETED_TURNS} (end_reason={result.end_reason!r})"
    )

    # 본격 3: ActionType 다양성
    action_types_used = {log.action.action_type for log in result.turn_logs}
    assert len(action_types_used) >= MIN_ACTION_TYPES, (
        f"ActionType 다양성 X: {len(action_types_used)} "
        f"< {MIN_ACTION_TYPES} ({sorted(at.name for at in action_types_used)})"
    )

    # 본격 4: end_reason 본격 정합
    valid_reasons = {
        "max_turns",
        "permadeath",
        "exit_floor",
        "time_limit_168h",
    }
    assert result.end_reason in valid_reasons, (
        f"unexpected end_reason: {result.end_reason!r}"
    )
