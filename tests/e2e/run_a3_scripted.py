"""Scripted A3 보스 사이클 E2E — LLM 무관 결정적 trace 생성.

본격 mechanism 검증 본격 (★ Mock/Player/GM 우회 — turn_handler 직접 호출):
- ENTER_RIFT (force_variant=True) → location mutate
- MOVE bc_ch1 → bc_ch2 → ... → bc_ch5 (★ boss spawn)
- ATTACK loop (★ HP=0까지)
- EXIT_RIFT (★ DUNGEON 복귀)

산출: tests/e2e/trace_A3_scripted.json — run_e2e_trace.py와 동일 format.

usage:
  python -m tests.e2e.run_a3_scripted [--out PATH] [--rift bloody_castle]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS
from service.game.state_v2 import (
    Character,
    Inventory,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    enter_rift,
    execute_attack,
    exit_rift,
    move_to_sub_area,
)
from service.sim.sim_runner import _location_snapshot, _world_snapshot


def _location_from_enter(
    location: Location,
    rift_id: str,
    side_effects: list[str],
) -> None:
    """enter_rift side_effects 본격 location mutation (★ sim_runner와 동일)."""
    location.realm = Realm.RIFT
    location.rift_id = rift_id
    for eff in side_effects:
        if eff.startswith("target_rift_sub_area="):
            location.rift_sub_area = eff.split("=", 1)[1]
        elif eff.startswith("target_rift_is_variant="):
            location.rift_is_variant = eff.split("=", 1)[1] == "True"


def _location_from_move(
    location: Location,
    side_effects: list[str],
) -> None:
    """move_to_sub_area side_effects 본격 location mutation."""
    if location.realm != Realm.RIFT:
        return
    for eff in side_effects:
        if eff.startswith("target_rift_sub_area="):
            location.rift_sub_area = eff.split("=", 1)[1]


def _location_from_exit(location: Location) -> None:
    """exit_rift 후 location 1층 복귀."""
    location.realm = Realm.DUNGEON
    location.rift_id = None
    location.rift_sub_area = None
    location.rift_is_variant = False


def _capture(
    turn_number: int,
    actor_name: str,
    action_type: str,
    action_target: str | None,
    success: bool,
    message: str,
    side_effects: list[str],
    actor: Character,
    world: WorldState,
    location: Location,
    hp_before: int,
) -> dict[str, Any]:
    """run_e2e_trace.py turn_logs 항목과 동일 schema."""
    return {
        "turn": turn_number,
        "actor": actor_name,
        "action_type": action_type,
        "action_target": action_target,
        "success": success,
        "message": message,
        "side_effects": list(side_effects),
        "hp_before": hp_before,
        "hp_after": actor.hp,
        "essence_slots_used": actor.essence_slots_used(),
        "has_active_light": actor.has_active_light(),
        "hours_in_dungeon": world.hours_in_dungeon,
        "world_snapshot": _world_snapshot(world),
        "location_snapshot": _location_snapshot(location),
    }


def run_scripted(rift_id: str, max_attacks: int = 30) -> dict[str, Any]:
    """ENTER → MOVE × chamber 수 → ATTACK × max_attacks → EXIT 사이클.

    Returns: trace dict (run_e2e_trace.py와 동일 format).
    """
    rift_def = FLOOR1_RIFT_DEFS[rift_id]

    # ★ 강한 attacker — boss 처치 보장 (단, 1회로 죽이지는 않을 만큼)
    attacker = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=200,
        hp_max=200,
        strength=30,  # damage = 30 + physical = 60
        physical=30,
        is_player=True,
    )
    attacker.inventory = Inventory(weight_max=10000)
    party = [attacker]

    world = WorldState(
        active_rifts=[rift_id],
        party_members=[attacker.name],
        hours_in_dungeon=72,
    )
    location = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="비석 공동",
    )

    turn_logs: list[dict[str, Any]] = []
    turn_no = 0

    # ── 1. ENTER_RIFT (force_variant=True) ──
    turn_no += 1
    hp_before = attacker.hp
    r = enter_rift(party, world, rift_id, force_variant=True)
    if r.success:
        _location_from_enter(location, rift_id, r.side_effects)
    turn_logs.append(
        _capture(
            turn_no,
            attacker.name,
            "ENTER_RIFT",
            rift_id,
            r.success,
            r.message,
            r.side_effects,
            attacker,
            world,
            location,
            hp_before,
        )
    )
    if not r.success:
        return _finalize(world, turn_logs, attacker, "enter_rift_failed")

    # ── 2. MOVE chain: entrance → boss_chamber ──
    # entrance_id에서 시작, connections 본격 BFS-like sequential 본격 (★ namu
    # 본격 chamber 본격 linear 본격 본격 본격, 1층 4 균열 모두 본격 본격).
    visited: set[str] = {location.rift_sub_area} if location.rift_sub_area else set()
    target_chamber = rift_def.boss_chamber_id

    while location.rift_sub_area != target_chamber:
        current_id = location.rift_sub_area
        if current_id is None:
            return _finalize(world, turn_logs, attacker, "no_current_chamber")
        current_sa = next(
            (sa for sa in rift_def.sub_areas if sa.id == current_id),
            None,
        )
        if current_sa is None:
            return _finalize(world, turn_logs, attacker, "current_chamber_undefined")

        # 다음 chamber: boss_chamber 우선, 아니면 unvisited 첫번째
        next_id: str | None = None
        if target_chamber in current_sa.connections:
            next_id = target_chamber
        else:
            for cid in current_sa.connections:
                if cid not in visited:
                    next_id = cid
                    break
        if next_id is None:
            return _finalize(
                world, turn_logs, attacker, "no_next_chamber_to_boss"
            )

        turn_no += 1
        hp_before = attacker.hp
        r = move_to_sub_area(party, world, location, next_id)
        if r.success:
            _location_from_move(location, r.side_effects)
            visited.add(next_id)
        turn_logs.append(
            _capture(
                turn_no,
                attacker.name,
                "MOVE",
                next_id,
                r.success,
                r.message,
                r.side_effects,
                attacker,
                world,
                location,
                hp_before,
            )
        )
        if not r.success:
            return _finalize(world, turn_logs, attacker, "move_failed")

    # ── 3. ATTACK loop until boss defeated ──
    attacks_used = 0
    while (
        world.active_boss_encounter is not None and attacks_used < max_attacks
    ):
        turn_no += 1
        attacks_used += 1
        hp_before = attacker.hp
        # weakness element 본격 본격 본격 — 약점 있으면 본격 본격
        boss = world.active_boss_encounter
        attack_element = boss.weakness_element
        r = execute_attack(
            attacker,
            boss.boss_name,
            party,
            world,
            attack_element=attack_element,
        )
        turn_logs.append(
            _capture(
                turn_no,
                attacker.name,
                "ATTACK",
                boss.boss_name,
                r.success,
                r.message,
                r.side_effects,
                attacker,
                world,
                location,
                hp_before,
            )
        )

    if world.active_boss_encounter is not None:
        return _finalize(world, turn_logs, attacker, "max_attacks_reached")

    # ── 4. EXIT_RIFT ──
    turn_no += 1
    hp_before = attacker.hp
    r = exit_rift(party, world, rift_id)
    if r.success:
        _location_from_exit(location)
    turn_logs.append(
        _capture(
            turn_no,
            attacker.name,
            "EXIT_RIFT",
            rift_id,
            r.success,
            r.message,
            r.side_effects,
            attacker,
            world,
            location,
            hp_before,
        )
    )

    return _finalize(world, turn_logs, attacker, "complete")


def _finalize(
    world: WorldState,
    turn_logs: list[dict[str, Any]],
    attacker: Character,
    end_reason: str,
) -> dict[str, Any]:
    return {
        "config": {
            "harness": "scripted",
            "scenario_id": "A3_scripted_bloody_castle_variant",
        },
        "end_reason": end_reason,
        "completed_turns": len(turn_logs),
        "final_hours_in_dungeon": world.hours_in_dungeon,
        "final_hp_by_actor": {attacker.name: attacker.hp},
        "final_inventory": {
            attacker.name: [
                {"name": it.name, "category": it.category.value}
                for it in attacker.inventory.items
            ],
        },
        "turn_logs": turn_logs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scripted A3 보스 사이클 E2E trace 생성"
    )
    parser.add_argument(
        "--rift",
        default="bloody_castle",
        choices=tuple(FLOOR1_RIFT_DEFS.keys()),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("tests/e2e/trace_A3_scripted.json"),
    )
    parser.add_argument("--max-attacks", type=int, default=30)
    args = parser.parse_args()

    print(f"Scripted A3 보스 사이클 — 균열: {args.rift} 본격 시작...")
    start = time.monotonic()
    trace = run_scripted(args.rift, max_attacks=args.max_attacks)
    elapsed = time.monotonic() - start
    trace["elapsed_seconds"] = round(elapsed, 2)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n본격 trace 저장: {args.out}")
    print(f"  end_reason: {trace['end_reason']}")
    print(f"  completed_turns: {trace['completed_turns']}")
    print(f"  elapsed: {elapsed:.2f}s")

    return 0 if trace["end_reason"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
