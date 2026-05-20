"""Phase D step 6b — multi-enemy turn loop primitives."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from service.sim.enemy import Enemy, enemy_to_dict
from service.sim.enemy_ai import plan_enemy_turn
from service.sim.equipment import Equipment, equipment_to_dict
from service.sim.status import StatusEffect, apply_status_effects, extract_status_from_text


@dataclass
class CombatTurnLog:
    actor: str
    action_name: str
    damage_dealt: int = 0
    damage_received: int = 0
    target_name: str = ""
    status_applied: list[str] = field(default_factory=list)
    enemy_resolved: bool = False
    notes: str = ""


def execute_player_attack(
    enemies: list[Enemy],
    target_idx: int,
    player_attack: int,
    user_input: str,
) -> tuple[list[Enemy], CombatTurnLog]:
    """플레이어가 target_idx 번 enemy를 공격."""
    if target_idx >= len(enemies):
        return enemies, CombatTurnLog(
            actor="player", action_name="attack", notes="no target"
        )

    enemies = list(enemies)
    target = enemies[target_idx]

    base = max(1, player_attack - target.defense)
    multiplier = 1.0
    for race in target.weakness_races:
        if race in user_input:
            multiplier = 1.5
            break
    damage = max(1, int(base * multiplier))
    target.hp = max(0, target.hp - damage)
    enemies[target_idx] = target

    return enemies, CombatTurnLog(
        actor="player",
        action_name="공격",
        damage_dealt=damage,
        target_name=target.name,
        enemy_resolved=(target.hp <= 0),
    )


def execute_enemy_turn(
    enemies: list[Enemy],
    player_hp: int,
    player_max_hp: int,
    player_defense: int,
    player_status: list[StatusEffect],
) -> tuple[list[Enemy], int, list[StatusEffect], list[CombatTurnLog]]:
    """살아 있는 enemy들이 플레이어를 공격.

    return: (enemies, new_player_hp, new_player_status, logs)
    """
    actions = plan_enemy_turn(enemies)
    logs: list[CombatTurnLog] = []
    new_hp = player_hp
    new_status = list(player_status)
    enemies_mut = list(enemies)

    for action in actions:
        enemy = next((e for e in enemies_mut if e.name == action.enemy_name), None)
        if enemy is None or enemy.hp <= 0:
            continue

        # 회복 ability
        if any(kw in action.ability_name for kw in ("복원", "회복", "재생")):
            heal = max(5, enemy.max_hp // 5)
            enemy.hp = min(enemy.max_hp, enemy.hp + heal)
            logs.append(CombatTurnLog(
                actor=enemy.name,
                action_name=action.ability_name,
                target_name=enemy.name,
                notes=f"hp +{heal}",
            ))
            continue

        # 공격
        damage = max(1, enemy.attack - player_defense)
        new_hp = max(0, new_hp - damage)
        applied = extract_status_from_text(action.ability_name)
        new_status.extend(applied)
        logs.append(CombatTurnLog(
            actor=enemy.name,
            action_name=action.ability_name,
            damage_received=damage,
            target_name="player",
            status_applied=[s.type.value for s in applied],
        ))

    # status 적용 (poison/bleed/burn → hp 추가 감소)
    new_hp, new_status = apply_status_effects(new_hp, player_max_hp, new_status)

    return enemies_mut, new_hp, new_status, logs


def cleanup_dead_enemies(
    enemies: list[Enemy],
    item_pool: list[Equipment] | None = None,
) -> tuple[list[Enemy], list[str], list[dict[str, object]]]:
    """죽은 enemy 제거 + drop 수집.

    return: (living, essence_drops, equipment_drops)
    """
    living: list[Enemy] = []
    essence_drops: list[str] = []
    equipment_drops: list[dict[str, object]] = []

    for e in enemies:
        if e.hp > 0:
            living.append(e)
            continue
        if e.essence_drop:
            essence_drops.append(e.essence_drop)
        if e.grade is not None and e.grade >= 5 and item_pool:
            if random.random() < 0.30:
                eq = random.choice(item_pool)
                equipment_drops.append(enemy_to_dict(e) if False else equipment_to_dict(eq))

    return living, essence_drops, equipment_drops


def find_target_index(enemies: list[Enemy], user_input: str) -> int:
    """user_input에서 enemy name을 찾아 index 반환. 없으면 0."""
    for i, e in enumerate(enemies):
        if e.name in user_input:
            return i
    return 0
