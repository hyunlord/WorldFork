"""4회 model combination 비교 (★ B commit 본격 입증).

본인 결정 본격:
- 9B (player) + 27B (gm) — A.5 baseline (★ 4/13)
- 27B (player) + 27B (gm) — root cause 3 본격 답
- 27B (player) + 9B (gm) — 비교 본질
- 9B (player) + 9B (gm) — baseline 본격

실행: python -m tools.run_sim_real_compare_models
출력: /tmp/sim_compare_4way_*.json + matrix table

요구:
- 8082 (27B Q2) + 8083 (9B Q3) 둘 다 진짜 작동
- 시간 ~25-35분 (★ 4회 50턴)
- 비용 0 (★ 정액제 로컬)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import requests

from core.llm.client import LLMClient
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.analyzer import analyze_sim_result
from service.sim.comparator import (
    ModelCombination,
    ModelComparisonResult,
    build_model_comparison_result,
    compare_model_combinations,
)
from service.sim.json_export import (
    save_sim_analysis_json,
    save_sim_result_json,
)
from service.sim.llm_factory import (
    QWEN35_9B_Q3_BASE_URL,
    QWEN35_9B_Q3_MODEL_KEY,
    QWEN36_27B_Q2_BASE_URL,
    QWEN36_27B_Q2_MODEL_KEY,
    make_gm_9b,
    make_gm_llm_client,
    make_player_27b,
    make_player_llm_client,
)
from service.sim.player_agent import PlayerAgent
from service.sim.sim_gm_agent import SimGMAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import SimConfig

COMBINATIONS: list[ModelCombination] = [
    ModelCombination(
        player_model=QWEN35_9B_Q3_MODEL_KEY,
        gm_model=QWEN36_27B_Q2_MODEL_KEY,
        label="9B Player + 27B GM",
    ),
    ModelCombination(
        player_model=QWEN36_27B_Q2_MODEL_KEY,
        gm_model=QWEN36_27B_Q2_MODEL_KEY,
        label="27B Player + 27B GM",
    ),
    ModelCombination(
        player_model=QWEN36_27B_Q2_MODEL_KEY,
        gm_model=QWEN35_9B_Q3_MODEL_KEY,
        label="27B Player + 9B GM",
    ),
    ModelCombination(
        player_model=QWEN35_9B_Q3_MODEL_KEY,
        gm_model=QWEN35_9B_Q3_MODEL_KEY,
        label="9B Player + 9B GM",
    ),
]


def _check_servers() -> bool:
    for url, label in [
        (QWEN36_27B_Q2_BASE_URL, "8082 (27B Q2)"),
        (QWEN35_9B_Q3_BASE_URL, "8083 (9B Q3)"),
    ]:
        try:
            r = requests.get(f"{url}/v1/models", timeout=3)
            if r.status_code != 200:
                print(f"[ERROR] {label} 응답 X")
                return False
        except requests.RequestException:
            print(f"[ERROR] {label} 접속 X")
            return False
    return True


def _make_player_for(model_key: str) -> LLMClient:
    if model_key == QWEN36_27B_Q2_MODEL_KEY:
        return make_player_27b()
    return make_player_llm_client()


def _make_gm_for(model_key: str) -> LLMClient:
    if model_key == QWEN35_9B_Q3_MODEL_KEY:
        return make_gm_9b()
    return make_gm_llm_client()


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
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": False,
                "essence_slots_used": 0,
            },
            "에르웬": {
                "hp": 90,
                "hp_max": 90,
                "race": "FAERIE",
                "has_active_light": False,
                "essence_slots_used": 0,
            },
        },
        "v2_world_state": {
            "hours_in_dungeon": 0,
            "party_members": ["비요른", "에르웬"],
            "current_round": 1,
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "진입점",
            "visibility_meters": 10,
            "has_light": False,
        },
    }


def main() -> int:
    print("=" * 80)
    print("B commit — 9B vs 27B Player 4회 비교 매트릭스 본격")
    print("=" * 80)
    print()

    if not _check_servers():
        return 1

    print("[INFO] 8082 + 8083 둘 다 작동 OK\n")

    output_dir = Path("/tmp")
    results: list[ModelComparisonResult] = []

    for i, combo in enumerate(COMBINATIONS, 1):
        print(f"\n{'=' * 80}")
        print(f"[{i}/{len(COMBINATIONS)}] {combo.label}")
        print(f"{'=' * 80}")

        player_llm = _make_player_for(combo.player_model)
        gm_llm = _make_gm_for(combo.gm_model)

        player_agent = PlayerAgent(llm_client=player_llm)
        gm_agent = SimGMAgent(llm_client=gm_llm)

        config = SimConfig(
            max_turns=50,
            player_llm_model=combo.player_model,
            gm_llm_model=combo.gm_model,
        )
        runner = SimRunner(
            config=config,
            player_agent=player_agent,
            gm_agent=gm_agent,
        )

        start = time.monotonic()
        result = runner.run(
            party=_make_test_party(),
            world=_make_test_world(),
            location=_make_test_location(),
            game_context=_build_game_context(),
        )
        runtime = time.monotonic() - start

        analysis = analyze_sim_result(result)
        slug = combo.label.replace(" ", "_").replace("+", "and")
        save_sim_result_json(
            result, output_dir / f"sim_compare_{slug}_result.json"
        )
        save_sim_analysis_json(
            analysis, output_dir / f"sim_compare_{slug}_analysis.json"
        )

        print(f"  diversity: {analysis.diversity_score}/13")
        print(f"  runtime: {runtime:.1f}s")
        print(
            f"  완료 턴: {analysis.completed_turns}/{analysis.total_turns}"
        )
        print(f"  생존: {'O' if analysis.survived_to_end else 'X'}")
        # ★ A.6 + F commit GM metrics
        print(
            f"  GM retry: {result.gm_retry_count}회, "
            f"fallback: {result.gm_fallback_count}회, "
            f"phase_mismatch: {result.gm_phase_mismatch_count}회"
        )
        # ★ E commit Player metrics (A.6 mirror)
        print(
            f"  Player retry: {result.player_retry_count}회, "
            f"fallback: {result.player_fallback_count}회"
        )
        print(
            f"  균열 시도: "
            f"{'O' if analysis.floor_exit_attempted else 'X'}"
        )
        print(
            f"  빛 관리: "
            f"{'O' if analysis.light_management_used else 'X'}"
        )
        most = (
            analysis.most_used_action.value
            if analysis.most_used_action
            else "?"
        )
        print(f"  최다: {most}")

        comparison_result = build_model_comparison_result(
            combo,
            analysis,
            runtime,
            gm_cost_usd=result.total_gm_llm_cost,
        )
        results.append(comparison_result)

    print("\n\n")
    print(compare_model_combinations(results))

    print("\n## B commit 본격 입증 진단 (★ root cause 3)\n")

    a5_baseline = next(
        r for r in results if r.combo.label == "9B Player + 27B GM"
    )
    p27_g27 = next(
        r for r in results if r.combo.label == "27B Player + 27B GM"
    )

    print(
        f"A.5 baseline (★ 9B Player): "
        f"diversity {a5_baseline.diversity_score}/13"
    )
    print(
        f"본 commit (★ 27B Player): "
        f"diversity {p27_g27.diversity_score}/13"
    )
    delta = p27_g27.diversity_score - a5_baseline.diversity_score
    print(f"증가: {delta} ActionType")

    if p27_g27.diversity_score >= 8:
        print("\n[OK] root cause 3 본격 답 입증 (★ 9B 한계 진짜 X)")
    elif p27_g27.diversity_score >= 6:
        print("\n[WARN] root cause 3 부분 답 (★ 27B도 ceiling 본격)")
    else:
        print("\n[INFO] root cause 3 미답 (★ 모델 X, 본질 다른 곳)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
