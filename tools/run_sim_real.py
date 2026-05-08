"""AI Playtester — 진짜 LLM 호출 50턴 시뮬.

본 commit 본격 (★ 5턴 → 50턴):
- qwen35_9b_q3 9B Q3 (★ 8083포트) 진짜 호출
- 50턴 본격 시뮬 (★ 1층 풀 진행)
- 진행 시간 측정 + 작품 매칭 검증 출력
- SimResult + 분석 + JSON 저장

실행: python -m tools.run_sim_real
출력: /tmp/sim_real_50turn_result.json + analysis.json

요구:
- qwen35_9b_q3 8083포트 진짜 작동 (★ DGX Spark)
- 예상 시간 ~64s (★ 50 X 1.28s, 직전 5턴 입증)
"""

from __future__ import annotations

import sys
import time
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
            f"{QWEN35_9B_Q3_BASE_URL}/v1/models",
            timeout=5,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def main() -> int:
    print("=== AI Playtester 50턴 진짜 LLM 시뮬 (★ qwen35_9b_q3) ===\n")

    if not _check_llm_server():
        print(f"[ERROR] LLM 서버 X ({QWEN35_9B_Q3_BASE_URL})")
        return 1

    print(f"[INFO] LLM 서버 작동 OK ({QWEN35_9B_Q3_BASE_URL})\n")

    llm_client = make_player_llm_client()
    player_agent = PlayerAgent(llm_client=llm_client)

    config = SimConfig(
        max_turns=50,
        scenario_id="floor1_real_50turn",
        player_llm_model="qwen35_9b_q3",
        gm_llm_model="qwen36_27b_q2",
    )
    runner = SimRunner(config=config, player_agent=player_agent)

    party = _make_test_party()
    world = _make_test_world()
    location = _make_test_location()
    game_ctx = _build_game_context()

    print("[시뮬] 50턴 시작 (예상 ~64s)...")
    start = time.monotonic()
    result = runner.run(
        party=party,
        world=world,
        location=location,
        game_context=game_ctx,
    )
    elapsed = time.monotonic() - start
    per_turn = elapsed / max(result.completed_turns, 1)
    print(
        f"[시뮬] 완료 — {elapsed:.1f}s ({per_turn:.2f}s/turn)\n"
    )

    analysis = analyze_sim_result(result)
    print(format_analysis_text(analysis))

    output_dir = Path("/tmp")
    save_sim_result_json(result, output_dir / "sim_real_50turn_result.json")
    save_sim_analysis_json(
        analysis, output_dir / "sim_real_50turn_analysis.json"
    )
    print(f"\n[저장] {output_dir}/sim_real_50turn_result.json")
    print(f"[저장] {output_dir}/sim_real_50turn_analysis.json")

    print("\n[작품 매칭 검증]")
    print(f"  생존 (영구사망 X): {'O' if analysis.survived_to_end else 'X'}")
    print(f"  균열 시도: {'O' if analysis.floor_exit_attempted else 'X'}")
    print(f"  빛 관리: {'O' if analysis.light_management_used else 'X'}")
    print(f"  diversity: {analysis.diversity_score}/13 ActionType")
    most = (
        analysis.most_used_action.value if analysis.most_used_action else "X"
    )
    print(f"  최다 행동: {most}")
    print(
        f"  미궁 시간: {analysis.final_hours_in_dungeon}h / 168h"
    )

    print("\n[샘플 turn_logs (처음 5개)]")
    for log in result.turn_logs[:5]:
        status = "OK" if log.success else "X"
        print(
            f"  [{status}] 턴 {log.turn_number} [{log.actor_name}] "
            f"{log.action.action_type.value:>16} → "
            f"{log.action.rationale[:60]}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
