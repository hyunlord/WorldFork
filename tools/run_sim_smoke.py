"""AI Playtester smoke runner — 50턴 시뮬 + 분석 + JSON 저장 + 다중 비교.

본 commit 4차: 통계 분석 + JSON 출력 진짜 실행 (★ MBNU 차단).
실행: python -m tools.run_sim_smoke
출력: /tmp/sim_smoke_result.json + /tmp/sim_smoke_analysis.json
"""

from __future__ import annotations

import sys
from pathlib import Path

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.analyzer import analyze_sim_result, format_analysis_text
from service.sim.comparator import compare_sims, format_comparison_text
from service.sim.json_export import (
    save_sim_analysis_json,
    save_sim_result_json,
)
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerAction, PlayerActionType, SimConfig


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


def _make_mock_actions() -> list[PlayerAction]:
    """1층 시나리오 mock — 다양 ActionType."""
    return [
        PlayerAction(
            action_type=PlayerActionType.ACTIVATE_LIGHT,
            actor_name="비요른",
            target="횃불",
        ),
        PlayerAction(
            action_type=PlayerActionType.MOVE,
            actor_name="비요른",
            target="북쪽 통로",
        ),
        PlayerAction(
            action_type=PlayerActionType.EXPLORE,
            actor_name="에르웬",
        ),
        PlayerAction(action_type=PlayerActionType.WAIT, actor_name="비요른"),
        PlayerAction(
            action_type=PlayerActionType.ABSORB_ESSENCE,
            actor_name="비요른",
            target="고블린 정수",
        ),
        PlayerAction(
            action_type=PlayerActionType.OFFER_TO_STONE,
            actor_name="비요른",
            target="green_mine",
        ),
        PlayerAction(
            action_type=PlayerActionType.ENTER_RIFT,
            actor_name="비요른",
            target="green_mine",
        ),
        PlayerAction(
            action_type=PlayerActionType.EXPLORE,
            actor_name="에르웬",
        ),
        PlayerAction(action_type=PlayerActionType.REST, actor_name="비요른"),
        PlayerAction(
            action_type=PlayerActionType.EXIT_RIFT,
            actor_name="비요른",
            target="green_mine",
        ),
    ]


def main() -> int:
    config = SimConfig(max_turns=50, scenario_id="floor1_smoke")

    # ─── 단일 시뮬 + 분석 ───
    runner = SimRunner(
        config=config,
        player_agent=MockPlayerAgent(mock_actions=_make_mock_actions()),
    )

    party = _make_test_party()
    world = _make_test_world()
    location = _make_test_location()

    print("=== AI Playtester 50턴 smoke + 분석 (★ 4차 commit) ===\n")
    result = runner.run(party=party, world=world, location=location)

    # 분석
    analysis = analyze_sim_result(result)
    print(format_analysis_text(analysis))

    # JSON 저장
    output_dir = Path("/tmp")
    save_sim_result_json(result, output_dir / "sim_smoke_result.json")
    save_sim_analysis_json(analysis, output_dir / "sim_smoke_analysis.json")
    print(f"\n[저장] {output_dir}/sim_smoke_result.json")
    print(f"[저장] {output_dir}/sim_smoke_analysis.json")

    # ─── 다중 시뮬 비교 (★ 5회) ───
    print("\n\n=== 5회 시뮬 비교 ===")
    analyses = [analysis]
    for i in range(2, 6):
        runner_i = SimRunner(
            config=SimConfig(
                max_turns=50, scenario_id=f"floor1_smoke_{i}"
            ),
            player_agent=MockPlayerAgent(mock_actions=_make_mock_actions()),
        )
        result_i = runner_i.run(
            party=_make_test_party(),
            world=_make_test_world(),
            location=_make_test_location(),
        )
        analyses.append(analyze_sim_result(result_i))

    comp = compare_sims(analyses)
    print(format_comparison_text(comp))

    return 0


if __name__ == "__main__":
    sys.exit(main())
