"""AI Playtester smoke 실행 (★ Tier 2 D12, 2차 commit production caller).

본인 본질:
- 진짜 LLM PlayerAgent (★ qwen35_9b_q3) + SimRunner.run() 1턴
- 본 CLI = PlayerAgent의 진짜 production caller (★ Stage 7 학습 정합)
- 실행: python -m tools.run_sim_smoke
- 요구: localhost:8083 9B Q3 서버 가동 중

3차 commit 후속:
- 50턴 자동 시뮬
- 다른 ActionType 본격 mutate
"""

from __future__ import annotations

from core.llm.local_client import get_qwen35_9b_q3
from service.game.init_from_plan import (
    init_v2_characters_from_plan,
    init_world_state_from_plan,
)
from service.pipeline.types import CharacterPlan, Plan, WorldSetting
from service.sim.player_agent import PlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import SimConfig


def _build_smoke_plan() -> Plan:
    """1층 미궁 진입 시작 Plan."""
    return Plan(
        work_name="barbarian_v2",
        work_genre="판타지",
        main_character=CharacterPlan(
            name="비요른",
            role="바바리안 부족장",
            description="주인공",
        ),
        supporting_characters=[
            CharacterPlan(
                name="에르웬",
                role="요정 정령사",
                description="동료",
            ),
        ],
        world=WorldSetting(
            setting_name="라스카니아",
            genre="판타지",
            tone="진지",
            rules=["미궁 존재"],
        ),
        opening_scene="비요른은 1층 수정동굴 진입점에서 깨어난다.",
        initial_choices=["진입"],
        ip_masking_applied=True,
    )


def main() -> None:
    """1턴 진짜 시뮬 (★ PlayerAgent → action → turn_handler mutate)."""
    plan = _build_smoke_plan()
    party = init_v2_characters_from_plan(plan)
    world = init_world_state_from_plan(plan)

    config = SimConfig(scenario_id="smoke_floor1", max_turns=1)
    client = get_qwen35_9b_q3()
    player_agent = PlayerAgent(client)

    runner = SimRunner(config=config, player_agent=player_agent)
    result = runner.run(party=party, world=world)

    print(f"[sim] {result.sim_id}")
    print(f"[config] {result.config_summary}")
    print(f"[completed] {result.completed_turns}/{result.total_turns}")
    print(f"[end_reason] {result.end_reason}")
    print(f"[hours_in_dungeon] {result.final_hours_in_dungeon}")

    for log in result.turn_logs:
        action_type = log.action.action_type.value
        print(
            f"[turn {log.turn_number}] {log.actor_name} → {action_type} "
            f"(target={log.action.target}) — {log.message}"
        )
        if log.action.rationale:
            print(f"  rationale: {log.action.rationale[:100]}")
        for fx in log.side_effects:
            print(f"  • {fx}")

    print(f"[latency] {result.total_latency_seconds:.2f}s")


if __name__ == "__main__":
    main()
