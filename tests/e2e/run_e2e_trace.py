"""E2E trace 캡처 + 잔여 finding 자동 검출 (★ F1, production caller).

usage:
  python -m tests.e2e.run_e2e_trace [--turns 100] [--out trace.json]

산출:
- trace.json: 전 턴 본격 trace + 통합 통계
- 잔여 finding 자동 검출:
  * F2 차단: end_reason / state error / 조기 종료
  * F3 균형: HP 곡선 + 정수 누적
  * F4 다양성: ActionType / sub_area / actor
  * F5 본문: 168h 한도 / encounter / 시간 정합
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

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


def _llm_alive(url: str) -> bool:
    import requests

    try:
        return requests.get(f"{url}/v1/models", timeout=3).status_code == 200
    except requests.RequestException:
        return False


def run_trace(target_turns: int = 100) -> tuple[SimResult, float]:
    """본 commit 본격 100턴 시뮬 (★ Player 9B + GM 27B if alive)."""
    player_client = make_player_llm_client(timeout=60)
    player_agent = PlayerAgent(llm_client=player_client)

    if _llm_alive(QWEN36_27B_Q2_BASE_URL):
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
            max_turns=target_turns,
            scenario_id=f"F1_e2e_{target_turns}turn",
            # ★ F3: initial_hours=0 (★ ENTRY phase 시작, 전 phase 본격 test)
            # default 72.0 (RIFT phase 시작) X — LLM이 본격 RIFT 위주만 응답
            initial_hours_in_dungeon=0.0,
        ),
        player_agent=player_agent,
        gm_agent=gm_agent,
    )

    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=150, hp_max=150,
            physical=14, strength=16, bone_strength=12,
            is_player=True,
        ),
        "에르웬": Character(
            name="에르웬",
            race=Race.FAERIE,
            hp=90, hp_max=90,
            soul_power=60, soul_power_max=60,
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

    game_context: dict[str, Any] = {
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
    }

    start = time.monotonic()
    result = runner.run(
        party=party,
        world=world,
        location=location,
        game_context=game_context,
    )
    elapsed = time.monotonic() - start
    return result, elapsed


def detect_findings(result: SimResult) -> dict[str, Any]:
    """잔여 F2-F5 자동 검출 (★ 실측 본격)."""
    logs = result.turn_logs

    # F2 — 차단 검출
    f2: dict[str, Any] = {
        "completed_turns": result.completed_turns,
        "end_reason": result.end_reason,
        "max_turns": result.total_turns,
        "early_termination_lt_30": result.completed_turns < 30,
        "gm_fallback_count": result.gm_fallback_count,
        "player_fallback_count": result.player_fallback_count,
        "gm_retry_count": result.gm_retry_count,
        "player_retry_count": result.player_retry_count,
    }

    # F3 — 균형 검출
    f3: dict[str, Any] = {}
    if logs:
        hp_curve: dict[str, list[int]] = {}
        for log in logs:
            hp_curve.setdefault(log.actor_name, []).append(log.hp_after)
        f3 = {
            "hp_curve_by_actor": {
                name: {
                    "min": min(curve),
                    "max": max(curve),
                    "final": curve[-1],
                }
                for name, curve in hp_curve.items()
            },
            "essences_max": max(log.essence_slots_used for log in logs),
            "final_hp_by_actor": dict(result.final_hp_by_actor),
            "essences_absorbed_by_actor": dict(
                result.essences_absorbed_by_actor
            ),
        }

    # F4 — 다양성 검출
    action_counter: Counter[str] = Counter(
        log.action.action_type.name for log in logs
    )
    actor_counter: Counter[str] = Counter(log.actor_name for log in logs)
    light_active_count = sum(1 for log in logs if log.has_active_light)
    f4: dict[str, Any] = {
        "action_types_used": len(action_counter),
        "action_types_total": len(list(PlayerActionType)),
        "action_counter": dict(action_counter.most_common()),
        "actor_counter": dict(actor_counter),
        "light_active_turn_count": light_active_count,
    }

    # F5 — 본문 정합 검출
    f5: dict[str, Any] = {
        "final_hours_in_dungeon": result.final_hours_in_dungeon,
        "hours_consumed": result.final_hours_in_dungeon,
        "max_hours_limit_168": 168,
        "reached_time_limit": result.end_reason == "time_limit_168h",
        "rift_entered": "ENTER_RIFT" in action_counter,
        "rift_exited": "EXIT_RIFT" in action_counter,
        "absorb_essence_count": action_counter.get("ABSORB_ESSENCE", 0),
        "attack_count": action_counter.get("ATTACK", 0),
        "offer_to_stone_count": action_counter.get("OFFER_TO_STONE", 0),
        "communicate_count": action_counter.get("COMMUNICATE", 0),
    }

    return {
        "F2_차단": f2,
        "F3_균형": f3,
        "F4_다양성": f4,
        "F5_본문_정합": f5,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="E2E trace 캡처 + finding 검출"
    )
    parser.add_argument("--turns", type=int, default=100)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("tests/e2e/trace_F1.json"),
    )
    args = parser.parse_args()

    print(f"E2E {args.turns}턴 시뮬 본격 시작...")
    print(f"  Player: {QWEN35_9B_Q3_BASE_URL} (9B Q3)")
    if _llm_alive(QWEN36_27B_Q2_BASE_URL):
        print(f"  GM:     {QWEN36_27B_Q2_BASE_URL} (27B Q2)")
    else:
        print(f"  GM:     {QWEN35_9B_Q3_BASE_URL} (9B Q3 fallback)")
    print()

    result, elapsed = run_trace(args.turns)
    findings = detect_findings(result)

    print(f"\n시뮬 시간: {elapsed:.1f}s ({elapsed / 60:.1f}분)")
    print(f"completed_turns: {result.completed_turns}/{result.total_turns}")
    print(f"end_reason: {result.end_reason}")
    print()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    output: dict[str, Any] = {
        "config": {
            "target_turns": args.turns,
            "scenario_id": f"F1_e2e_{args.turns}turn",
        },
        "elapsed_seconds": round(elapsed, 1),
        "completed_turns": result.completed_turns,
        "end_reason": result.end_reason,
        "final_hp_by_actor": dict(result.final_hp_by_actor),
        "final_hours_in_dungeon": result.final_hours_in_dungeon,
        "findings": findings,
        "turn_logs": [
            {
                "turn": log.turn_number,
                "actor": log.actor_name,
                "action_type": log.action.action_type.name,
                "action_target": log.action.target,
                "success": log.success,
                "hp_before": log.hp_before,
                "hp_after": log.hp_after,
                "essence_slots_used": log.essence_slots_used,
                "has_active_light": log.has_active_light,
                "hours_in_dungeon": log.hours_in_dungeon,
            }
            for log in result.turn_logs
        ],
    }
    args.out.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"본격 trace 저장: {args.out}")

    # 본격 finding 본격 보고
    print("\n=== 잔여 finding 자동 검출 ===")
    for fname, fdata in findings.items():
        print(f"\n{fname}:")
        for k, v in fdata.items():
            if isinstance(v, dict) and len(v) > 4:
                print(f"  {k}: <{len(v)} entries>")
            else:
                print(f"  {k}: {v}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
