"""Phase D step 6b — enemy ability selection by HP/context."""

from __future__ import annotations

from dataclasses import dataclass

from service.sim.enemy import Enemy
from service.util.korean import i_ga

_DEFENSIVE_KEYWORDS = ("복원", "회복", "재생", "방어", "치유")


@dataclass
class EnemyAction:
    enemy_name: str
    ability_name: str
    target: str = "player"


def select_ability(enemy: Enemy) -> str:
    """HP 비율 기반 ability 선택.

    HP < 30%: 회복/방어 ability 우선
    HP < 50%: 마지막 ability (강공세)
    default : 첫 번째 ability
    """
    if not enemy.abilities:
        return "기본 공격"

    hp_ratio = enemy.hp / enemy.max_hp if enemy.max_hp > 0 else 1.0

    if hp_ratio < 0.3:
        for ab in enemy.abilities:
            if any(kw in ab for kw in _DEFENSIVE_KEYWORDS):
                return ab
        return enemy.abilities[0]

    if hp_ratio < 0.5:
        return enemy.abilities[-1]

    return enemy.abilities[0]


def plan_enemy_turn(enemies: list[Enemy]) -> list[EnemyAction]:
    """살아 있는 enemy마다 이번 턴 action 결정."""
    actions: list[EnemyAction] = []
    for e in enemies:
        if e.hp <= 0:
            continue
        ab = select_ability(e)
        actions.append(EnemyAction(
            enemy_name=e.name,
            ability_name=ab,
            target="player",
        ))
    return actions


def should_enemy_flee(enemy: Enemy, initial_count: int, current_count: int) -> bool:
    """도주 조건 판정 — ep_0008 동료 사망 / ep_0013 수적 열세 / ep_0054 전략적 후퇴.

    HP < 25% 이거나 초기 2마리 이상에서 절반 이하로 줄었을 때 도주.
    """
    if enemy.max_hp > 0:
        if enemy.hp / enemy.max_hp < 0.25:
            return True
    if initial_count >= 2 and current_count <= initial_count // 2:
        return True
    return False


def compose_flee_narrative(enemy_name: str) -> str:
    """도주 연출 메시지."""
    particle = i_ga(enemy_name)
    return f"{enemy_name}{particle} 뒤돌아 도망쳤다."
