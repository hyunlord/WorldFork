"""AI Playtester — 진짜 LLM 50턴 X 3회 평균 비교.

본인 본질 (★ 다중 시뮬 본격):
- 동일 config로 3회 시뮬
- LLM stochastic 본질 진짜 검증
- 평균 / 분포 분석

실행: python -m tools.run_sim_real_compare
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
from service.sim.analyzer import analyze_sim_result
from service.sim.comparator import compare_sims, format_comparison_text
from service.sim.json_export import save_sim_analysis_json
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
    try:
        resp = requests.get(
            f"{QWEN35_9B_Q3_BASE_URL}/v1/models", timeout=5
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def main() -> int:
    print("=== AI Playtester 50턴 X 3회 비교 ===\n")

    if not _check_llm_server():
        print("[ERROR] LLM 서버 X")
        return 1

    print("[INFO] LLM 서버 작동 OK\n")

    llm_client = make_player_llm_client()
    player_agent = PlayerAgent(llm_client=llm_client)

    analyses = []
    output_dir = Path("/tmp")
    for i in range(1, 4):
        config = SimConfig(
            max_turns=50,
            scenario_id=f"floor1_real_50turn_{i}",
            player_llm_model="qwen35_9b_q3",
            gm_llm_model="qwen36_27b_q2",
        )
        runner = SimRunner(config=config, player_agent=player_agent)

        print(f"[시뮬 {i}/3] 시작 (예상 ~64s)...")
        result = runner.run(
            party=_make_test_party(),
            world=_make_test_world(),
            location=_make_test_location(),
            game_context=_build_game_context(),
        )
        analysis = analyze_sim_result(result)
        analyses.append(analysis)

        print(
            f"  완료 {analysis.completed_turns}/{analysis.total_turns} "
            f"end={analysis.end_reason} "
            f"diversity={analysis.diversity_score}/13 "
            f"latency={analysis.total_latency_seconds:.1f}s\n"
        )

        save_sim_analysis_json(
            analysis,
            output_dir / f"sim_real_50turn_run{i}_analysis.json",
        )

    comp = compare_sims(analyses)
    print(format_comparison_text(comp))

    return 0


if __name__ == "__main__":
    sys.exit(main())
