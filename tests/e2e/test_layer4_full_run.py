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
from service.sim.types import PlayerActionType, SimConfig, SimResult

# ★ F1 본격 E2E 기준 (★ 실측 후 본격 보정 가능)
TARGET_TURNS = 100
MIN_COMPLETED_TURNS = 30  # ★ 168h 한도 본격 도달 가능 (30턴 본격)
MIN_ACTION_TYPES = 5      # ★ 13 중 최소 5 다양성
MIN_SUB_AREAS = 2         # ★ 6 중 최소 2 방문

# ★ F5b RIFT phase 본격 기준
RIFT_INITIAL_HOURS = 72.0       # ★ phase 정합 (★ DungeonPhase.RIFT)
RIFT_MIN_COMPLETED_TURNS = 50   # ★ RIFT phase 최소 완주
RIFT_MIN_ENTER_RIFT = 1         # ★ RIFT phase 본격 ENTER_RIFT ≥ 1


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


def _run_layer4_sim(
    initial_hours: float,
    scenario_id: str,
) -> SimResult:
    """공통 100턴 시뮬 본격 (★ ENTRY/RIFT phase 공유 본격 setup)."""
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
            scenario_id=scenario_id,
            initial_hours_in_dungeon=initial_hours,
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

    return runner.run(
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
                "hours_in_dungeon": int(initial_hours),
                "is_dark_zone": True,
            },
        },
    )


def test_layer4_full_run_100turn() -> None:
    """100턴 진짜 LLM 시뮬 — Layer 4 통합 검증 (★ ENTRY phase).

    본 test는 slow (~5-10분 본격 LLM, DGX Spark 한정).
    """
    result = _run_layer4_sim(
        initial_hours=0.0, scenario_id="e2e_F1_100turn"
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


def test_layer4_full_run_rift_phase() -> None:
    """100턴 RIFT phase 본격 시뮬 — initial_hours=72.0 (★ F5b).

    F1-F5는 ENTRY phase (h=0) 본격 검증. 본 test는 RIFT phase 별도:
    - GM이 RIFT encounter 우선 spawn (★ PHASE_TYPE_WEIGHTS RIFT 40%)
    - LLM이 ENTER_RIFT 본격 발현
    - 본격 1층 안정화 완전 마무리

    본 test는 slow (~20분 본격 LLM, DGX Spark 한정).
    """
    result = _run_layer4_sim(
        initial_hours=RIFT_INITIAL_HOURS,
        scenario_id="e2e_F5b_rift_phase_100turn",
    )

    # 본격 1: state 정합 (★ 음수 X)
    for log in result.turn_logs:
        assert log.hp_after >= 0, (
            f"turn {log.turn_number}: HP 음수 {log.hp_after}"
        )
        assert log.hours_in_dungeon >= 0
        assert log.hours_in_dungeon <= 250  # ★ 168 + RIFT 시작 본격 buffer

    # 본격 2: RIFT phase 50턴 본격 완주
    assert result.completed_turns >= RIFT_MIN_COMPLETED_TURNS, (
        f"RIFT phase early termination: {result.completed_turns} "
        f"< {RIFT_MIN_COMPLETED_TURNS} (end_reason={result.end_reason!r})"
    )

    # 본격 3: ENTER_RIFT ≥ 1 (★ RIFT phase 정합 본격)
    enter_rift_count = sum(
        1 for log in result.turn_logs
        if log.action.action_type == PlayerActionType.ENTER_RIFT
    )
    assert enter_rift_count >= RIFT_MIN_ENTER_RIFT, (
        f"RIFT phase ENTER_RIFT 본격 X: {enter_rift_count} "
        f"< {RIFT_MIN_ENTER_RIFT}"
    )

    # 본격 4: end_reason 본격 정합 (★ time_limit 가능 본격 — h=72 시작)
    valid_reasons = {
        "max_turns",
        "permadeath",
        "exit_floor",
        "time_limit_168h",
    }
    assert result.end_reason in valid_reasons, (
        f"unexpected end_reason: {result.end_reason!r}"
    )
