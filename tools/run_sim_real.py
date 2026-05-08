"""AI Playtester — 진짜 LLM 호출 시뮬.

본 commit 본격:
- qwen35_9b_q3 9B Q3 (★ 8083포트) 진짜 호출
- 5턴 짧은 시뮬 (★ 비용/지연 검증, 50턴은 후속)
- LLM 응답 → JSON parsing → PlayerAction
- turn_handler 진짜 mutate
- SimResult + 분석 + JSON 저장

실행: python -m tools.run_sim_real

요구:
- qwen35_9b_q3 8083포트 진짜 작동 (★ DGX Spark)
- 진짜 호출 X면 connection error (★ 자연스러운 fallback)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.analyzer import analyze_sim_result, format_analysis_text
from service.sim.json_export import (
    save_sim_analysis_json,
    save_sim_result_json,
)
from service.sim.llm_factory import (
    QWEN35_9B_Q3_BASE_URL,
    make_player_llm_client,
)
from service.sim.player_agent import PlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import SimConfig


def _make_test_party() -> dict[str, Character]:
    return {
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


def _make_test_world() -> WorldState:
    return WorldState(
        current_round=1,
        hours_in_dungeon=0,
        is_dark_zone=True,
        party_members=["비요른", "에르웬"],
    )


def _make_test_location() -> Location:
    return Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="진입점",
        visibility_meters=10,
        has_light=False,
    )


def _build_game_context() -> dict[str, Any]:
    """게임 컨텍스트 mock — 본 commit 단순.

    후속 commit이 진짜 init_from_plan + build_game_context 통합.
    """
    return {
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
            "에르웬": {
                "race": "요정",
                "hp": 90,
                "hp_max": 90,
                "physical": 8,
                "mental": 12,
                "special": 14,
                "strength": 8,
                "agility": 12,
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
            "active_rifts": [],
        },
    }


def _check_llm_server() -> bool:
    """8083포트 진짜 작동 검증."""
    try:
        resp = requests.get(
            f"{QWEN35_9B_Q3_BASE_URL}/v1/models",
            timeout=5,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def main() -> int:
    print("=== AI Playtester 진짜 LLM 시뮬 (★ qwen35_9b_q3 9B Q3) ===\n")

    if not _check_llm_server():
        print(f"[ERROR] LLM 서버 X ({QWEN35_9B_Q3_BASE_URL})")
        print("[INFO] DGX Spark에서 qwen35_9b_q3 8083포트 시작 필요")
        return 1

    print(f"[INFO] LLM 서버 작동 OK ({QWEN35_9B_Q3_BASE_URL})\n")

    llm_client = make_player_llm_client()
    player_agent = PlayerAgent(llm_client=llm_client)

    config = SimConfig(
        max_turns=5,
        scenario_id="floor1_real_5turn",
        player_llm_model="qwen35_9b_q3",
        gm_llm_model="qwen36_27b_q2",
    )
    runner = SimRunner(config=config, player_agent=player_agent)

    party = _make_test_party()
    world = _make_test_world()
    location = _make_test_location()
    game_ctx = _build_game_context()

    print("[시뮬] 5턴 시작...\n")
    result = runner.run(
        party=party,
        world=world,
        location=location,
        game_context=game_ctx,
    )

    analysis = analyze_sim_result(result)
    print(format_analysis_text(analysis))

    output_dir = Path("/tmp")
    save_sim_result_json(result, output_dir / "sim_real_result.json")
    save_sim_analysis_json(analysis, output_dir / "sim_real_analysis.json")
    print(f"\n[저장] {output_dir}/sim_real_result.json")
    print(f"[저장] {output_dir}/sim_real_analysis.json")

    print("\n[LLM 호출 검증]")
    print(f"  지연: {result.total_latency_seconds:.2f}s")
    print(f"  완료 턴: {result.completed_turns}/{result.total_turns}")
    print(f"  종료: {result.end_reason}")

    if result.turn_logs:
        print("\n[첫 턴 진짜 응답]")
        first = result.turn_logs[0]
        print(f"  actor: {first.actor_name}")
        print(f"  action: {first.action.action_type.value}")
        print(f"  target: {first.action.target}")
        print(f"  rationale: {first.action.rationale[:100]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
