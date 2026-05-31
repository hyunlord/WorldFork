"""Phase D step 6b — multi-enemy turn loop primitives."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from service.canon.races import Race
from service.sim.combat_helpers import apply_race_dodge
from service.sim.enemy import Enemy, EnemyType, enemy_to_dict
from service.sim.enemy_ai import plan_enemy_turn
from service.sim.equipment import Equipment, equipment_to_dict
from service.sim.status import StatusEffect, apply_status_effects, extract_status_from_text
from service.util.korean import eul_reul

# (threshold, message, is_critical)
HP_THRESHOLDS: list[tuple[float, str, bool]] = [
    (0.50, "「캐릭터의 생명력이 50% 이하입니다.」", False),
    (0.20, "「캐릭터의 생명력이 20% 이하입니다.」", False),
    (
        0.05,
        "「경고: 캐릭터의 생명력이 5% 미만입니다. 조속히 치료하지 않을 시, 캐릭터가 사망에 이를 수 있습니다.」",  # noqa: E501
        True,
    ),
    (0.00, "「경고: 캐릭터의 생명력이 0%에 도달했습니다.」", True),
]


def check_hp_threshold_message(prev_hp: int, new_hp: int, max_hp: int) -> str | None:
    """이전 HP → 새 HP 변화 시 처음으로 넘은 threshold 메시지 반환.

    낮은 threshold가 우선(0% > 5% > 20% > 50% 순).
    """
    if max_hp <= 0:
        return None
    prev_ratio = prev_hp / max_hp
    new_ratio = new_hp / max_hp
    for threshold, message, _ in reversed(HP_THRESHOLDS):
        if prev_ratio > threshold >= new_ratio:
            return message
    return None


def format_kill_message(enemy_name: str, xp_gain: int) -> str:
    """처치 메시지 — 「{이름}을(를) 처치했습니다. EXP +N」."""
    particle = eul_reul(enemy_name)
    return f"「{enemy_name}{particle} 처치했습니다. EXP +{xp_gain}」"


def format_bonus_message(bonus_type: str, xp_bonus: int) -> str:
    """보너스 XP 메시지 — 「{타입} 처치 보너스. EXP +N」."""
    return f"「{bonus_type} 처치 보너스. EXP +{xp_bonus}」"


# ── 치명타 (★ audit-5 Fix 6 / wiki 008 / ep_0018 유연성 정합) ──
CRITICAL_BASE_CHANCE: float = 0.05   # 기본 5%
CRITICAL_MULTIPLIER: float = 2.0     # 2x


def compute_critical_hit(
    player_agility: int = 0,
    base_chance: float = CRITICAL_BASE_CHANCE,
    rand_func: Callable[[], float] = random.random,
) -> bool:
    """치명타 발동 여부 판정.

    본문 정합 (ep_0018): 유연성 → 치명타율 증가.
    공식: base + agility * 0.005, 상한 30%.
    """
    chance = min(0.30, base_chance + player_agility * 0.005)
    return rand_func() < chance


def apply_critical_damage(base_damage: int) -> int:
    """치명타 damage = base * CRITICAL_MULTIPLIER."""
    return int(base_damage * CRITICAL_MULTIPLIER)


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
    immune: bool = False         # 영체류 물리 면역 등
    weakness_hit: bool = False   # 약점 적중 (1.5x)
    critical_hit: bool = False   # 치명타 (2x)
    resist_reduced: int = 0      # ★ I-G1 player 저항 감산량
    resist_element: str = ""     # ★ I-G1 감산 element


def compute_damage_multiplier(
    enemy: Enemy,
    attack_elements: list[str] | None = None,
) -> float:
    """damage multiplier 계산 — wiki 009 본문 정합.

    영체류 + 물리 only → 0.0 (면역)
    weakness_types ∩ attack_elements → 1.5
    기본 → 1.0
    """
    elements: set[str] = set(attack_elements) if attack_elements else {"물리"}

    if enemy.enemy_type == EnemyType.SPIRIT:
        non_physical = elements - {"물리"}
        if not non_physical:
            return 0.0

    weak_set = set(enemy.weakness_types)
    if weak_set & elements:
        return 1.5

    return 1.0


# 감응도 1당 element 위력 +2% (★ canon "속성 위력 보정")
SENSITIVITY_SCALE: float = 0.02


def apply_sensitivity_bonus(
    base_element_damage: int,
    attack_elements: list[str] | None,
    sensitivities: dict[str, int] | None,
) -> int:
    """공격 element 감응도 → 데미지 위력 보정.

    attack_elements 중 물리 외 element의 최대 감응도로 보정:
      damage × (1 + sensitivity × SENSITIVITY_SCALE).
    물리 단독(감응도 무관) 또는 감응도 0 → 보정 없음.
    """
    if not attack_elements or not sensitivities or base_element_damage <= 0:
        return base_element_damage
    best = max(
        (sensitivities.get(el, 0) for el in attack_elements if el != "물리"),
        default=0,
    )
    if best <= 0:
        return base_element_damage
    return max(1, int(base_element_damage * (1.0 + best * SENSITIVITY_SCALE)))


def execute_player_attack(
    enemies: list[Enemy],
    target_idx: int,
    player_attack: int,
    user_input: str,
    attack_elements: list[str] | None = None,
    player_agility: int = 0,
    rand_func: Callable[[], float] = random.random,
    attack_sensitivities: dict[str, int] | None = None,
) -> tuple[list[Enemy], CombatTurnLog]:
    """플레이어가 target_idx 번 enemy를 공격."""
    if target_idx >= len(enemies):
        return enemies, CombatTurnLog(
            actor="player", action_name="attack", notes="no target"
        )

    enemies = list(enemies)
    target = enemies[target_idx]

    base = max(1, player_attack - target.defense)
    multiplier = compute_damage_multiplier(target, attack_elements)

    # weakness_races — user_input 텍스트 매칭 (기존 동작 보존)
    if multiplier < 1.5:
        for race in target.weakness_races:
            if race in user_input:
                multiplier = max(multiplier, 1.5)
                break

    if multiplier == 0.0:
        enemies[target_idx] = target
        return enemies, CombatTurnLog(
            actor="player",
            action_name="공격",
            damage_dealt=0,
            target_name=target.name,
            enemy_resolved=False,
            immune=True,
        )

    damage = max(1, int(base * multiplier))

    # ★ 감응도 — element 공격 위력 보정 (물리 단독 시 무관)
    damage = apply_sensitivity_bonus(damage, attack_elements, attack_sensitivities)

    # 치명타 check — 면역 X 시에만 (★ ep_0018 유연성 정합)
    is_critical = compute_critical_hit(player_agility, rand_func=rand_func)
    if is_critical:
        damage = apply_critical_damage(damage)

    target.hp = max(0, target.hp - damage)
    enemies[target_idx] = target

    return enemies, CombatTurnLog(
        actor="player",
        action_name="공격",
        damage_dealt=damage,
        target_name=target.name,
        enemy_resolved=(target.hp <= 0),
        weakness_hit=(multiplier > 1.0),
        critical_hit=is_critical,
    )


def execute_enemy_turn(
    enemies: list[Enemy],
    player_hp: int,
    player_max_hp: int,
    player_defense: int,
    player_status: list[StatusEffect],
    player_race: Race | None = None,
    player_resistances: dict[str, int] | None = None,
    player_reflect: float = 0.0,
) -> tuple[list[Enemy], int, list[StatusEffect], list[CombatTurnLog]]:
    """살아 있는 enemy들이 플레이어를 공격.

    return: (enemies, new_player_hp, new_player_status, logs)
    player_race: race 회피 확률 적용용 (드워프 5%, 요정 10%)
    player_resistances: ★ I-G1 element 저항 dict — enemy element 정합 감산
    player_reflect: ★ 피해 반사율 — 받은 피해의 일부를 공격 enemy에게 (확률적 보복)
    """
    from service.canon.effects import apply_resistance, get_enemy_attack_element

    resistances = player_resistances or {}
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

        # 공격 — apply_race_dodge로 회피 확률 적용
        base_damage = max(1, enemy.attack - player_defense)
        if player_race is not None:
            final_damage, dodged = apply_race_dodge(player_race, base_damage)
        else:
            final_damage, dodged = base_damage, False
        if dodged:
            logs.append(CombatTurnLog(
                actor=enemy.name,
                action_name=action.ability_name,
                damage_received=0,
                target_name="player",
                notes="dodged",
            ))
            continue
        # ★ I-G1 — enemy element 정합 player 저항 감산
        element = get_enemy_attack_element(enemy.enemy_type.value)
        final_damage, resist_reduced = apply_resistance(
            final_damage, element, resistances
        )
        new_hp = max(0, new_hp - final_damage)
        # ★ 피해 반사 — 받은 피해의 일부를 공격 enemy에게 (확률적 보복 passive)
        reflected = 0
        if player_reflect > 0 and final_damage > 0:
            reflected = max(1, int(final_damage * player_reflect))
            enemy.hp = max(0, enemy.hp - reflected)
        applied = extract_status_from_text(action.ability_name)
        new_status.extend(applied)
        logs.append(CombatTurnLog(
            actor=enemy.name,
            action_name=action.ability_name,
            damage_received=final_damage,
            target_name="player",
            status_applied=[s.type.value for s in applied],
            resist_reduced=resist_reduced,
            resist_element=element if resist_reduced > 0 else "",
            notes=f"반사 {reflected}" if reflected > 0 else "",
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
