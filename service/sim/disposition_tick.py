"""V3 Phase 0 — 틱 루프 최소 (LLM 없이, 코드 결정적).

DESIGN_disposition_engine.md 2장. 동료 1명이 매 틱 성향별 기본 행동(default_action)으로
자율 이동/전투한다. LLM 호출 0 — 평소 틱은 코드 패턴이 즉각 결정. 기존 전투 로직
(combat.compute_critical_hit)을 재사용해 돌격 시 피해를 낸다.

Phase 0 검증: 같은 세계라도 성향이 다른 동료는 다른 궤적/행동을 보이는가(코드만).
파티(N명)·LLM 지시 해석은 Phase 1+.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from service.sim.combat import apply_critical_damage
from service.sim.disposition import (
    Companion,
    DispoAction,
    WorldView,
    default_action,
)

# 아군 위기 판정 — HP 비율이 이 값 이하면 '위기'(구원 트리거).
_DANGER_HP_RATIO = 0.35
# 원거리 행동의 안전 거리 — 이보다 가까우면 한 칸 물러선다.
_RANGED_KEEP = 2
# 저돌성이 이 값 이상이면 돌격 시 결정적 강타(combat.apply_critical_damage 재사용).
_BERSERK_CRIT = 80


@dataclass
class TickEnemy:
    """틱 루프용 최소 적 — 위치/HP만(전투 로직은 combat.py 재사용)."""

    name: str
    pos: tuple[int, int]
    hp: int = 30


@dataclass
class TickWorld:
    """틱 루프 최소 세계 — 동료 1명 + 적 + 플레이어 + 미탐색 지점.

    좌표는 정수 격자. 거리는 맨해튼. 모든 변경은 코드(결정적).
    """

    companion: Companion
    enemies: list[TickEnemy] = field(default_factory=list)
    player_pos: tuple[int, int] = (0, 0)
    player_hp: int = 100
    player_max_hp: int = 100
    unexplored_pos: tuple[int, int] | None = None  # 정찰 목표(없으면 미탐색 없음)
    tick: int = 0


@dataclass
class TickResult:
    """한 틱의 관측 — 검증/로그용(어떤 성향이 무슨 행동을 했나)."""

    tick: int
    action: DispoAction
    companion_pos: tuple[int, int]
    note: str = ""


def _dist(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(src: tuple[int, int], dst: tuple[int, int]) -> tuple[int, int]:
    """dst 방향으로 한 칸 이동(맨해튼 — x 먼저, 그다음 y)."""
    x, y = src
    if x != dst[0]:
        x += 1 if dst[0] > x else -1
    elif y != dst[1]:
        y += 1 if dst[1] > y else -1
    return (x, y)


def _step_away(src: tuple[int, int], threat: tuple[int, int]) -> tuple[int, int]:
    """threat 반대로 한 칸(엄폐/후퇴)."""
    x, y = src
    if x != threat[0]:
        x += 1 if x > threat[0] else -1
    elif y != threat[1]:
        y += 1 if y > threat[1] else -1
    else:
        x += 1  # 겹쳤으면 임의 방향
    return (x, y)


def _nearest_enemy(world: TickWorld) -> TickEnemy | None:
    live = [e for e in world.enemies if e.hp > 0]
    if not live:
        return None
    return min(live, key=lambda e: _dist(world.companion.pos, e.pos))


def build_view(world: TickWorld) -> WorldView:
    """게임 상태 → 동료 인식(WorldView). 코드가 계산(0토큰)."""
    enemy = _nearest_enemy(world)
    ally_danger = world.player_hp <= world.player_max_hp * _DANGER_HP_RATIO
    return WorldView(
        enemy_near=enemy is not None,
        enemy_distance=_dist(world.companion.pos, enemy.pos) if enemy else 99,
        unexplored=world.unexplored_pos is not None,
        ally_in_danger=ally_danger,
    )


def step_tick(world: TickWorld) -> TickResult:
    """한 틱 진행 — 성향별 기본 행동을 결정·적용(LLM 없이)."""
    world.tick += 1
    comp = world.companion
    view = build_view(world)
    action = default_action(comp.disposition, view)
    note = ""

    if action is DispoAction.CHARGE:
        enemy = _nearest_enemy(world)
        if enemy is not None:
            if _dist(comp.pos, enemy.pos) <= 1:
                # 저돌성↑ 동료는 결정적 강타(성향이 피해로 — Phase 0은 random 없음).
                berserk = comp.disposition.aggression >= _BERSERK_CRIT
                dmg = apply_critical_damage(comp.attack) if berserk else comp.attack
                enemy.hp -= dmg
                note = f"{enemy.name} 타격 {dmg}{' (강타)' if berserk else ''}"
            else:
                comp.pos = _step_toward(comp.pos, enemy.pos)
                note = "적에게 돌진"
    elif action is DispoAction.RANGED:
        enemy = _nearest_enemy(world)
        if enemy is not None:
            d = _dist(comp.pos, enemy.pos)
            if d < _RANGED_KEEP:
                comp.pos = _step_away(comp.pos, enemy.pos)
                note = "거리를 벌림"
            else:
                enemy.hp -= max(1, comp.attack // 2)  # 원거리 — 약한 피해
                note = f"{enemy.name} 원거리 사격"
    elif action is DispoAction.SCOUT:
        if world.unexplored_pos is not None:
            comp.pos = _step_toward(comp.pos, world.unexplored_pos)
            if comp.pos == world.unexplored_pos:
                world.unexplored_pos = None  # 정찰 완료
                note = "정찰 완료"
            else:
                note = "앞서 정찰"
    elif action is DispoAction.RESCUE:
        comp.pos = _step_toward(comp.pos, world.player_pos)
        note = "위기의 아군에게"
    elif action is DispoAction.FOLLOW:
        if _dist(comp.pos, world.player_pos) > 1:
            comp.pos = _step_toward(comp.pos, world.player_pos)
        note = "플레이어 곁"

    return TickResult(world.tick, action, comp.pos, note)


def run_ticks(world: TickWorld, n: int) -> list[TickResult]:
    """n틱 진행 — 동료 자율 행동 궤적을 반환(검증용)."""
    return [step_tick(world) for _ in range(n)]
