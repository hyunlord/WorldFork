"""V3 Phase 0 — 틱 루프 최소 (LLM 없이, 코드 결정적).

DESIGN_disposition_engine.md 2장. 동료 1명이 매 틱 성향별 기본 행동(default_action)으로
자율 이동/전투한다. LLM 호출 0 — 평소 틱은 코드 패턴이 즉각 결정. 기존 전투 로직
(combat.compute_critical_hit)을 재사용해 돌격 시 피해를 낸다.

Phase 0 검증: 같은 세계라도 성향이 다른 동료는 다른 궤적/행동을 보이는가(코드만).
파티(N명)·LLM 지시 해석은 Phase 1+.
"""

from __future__ import annotations

from collections.abc import Callable
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
    """틱 루프용 최소 적 — 위치/HP/공격력(반격은 enemy_step, combat primitive 재사용)."""

    name: str
    pos: tuple[int, int]
    hp: int = 30
    attack: int = 6


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


# 이동 보조 — 벽을 아는 한 칸 전진. blocked=None이면 Phase 0(_step_toward/away)과 동일.
Blocked = Callable[[tuple[int, int]], bool]


def _advance(
    src: tuple[int, int],
    dst: tuple[int, int],
    blocked: Blocked | None,
    *,
    away: bool = False,
) -> tuple[int, int]:
    """dst 쪽(또는 away면 반대)으로 한 칸 — 벽이면 수직 축으로 우회, 둘 다 막히면 정지.

    blocked 미지정 시 _step_toward/_step_away와 바이트 동일(Phase 0 궤적 불변).
    """
    x, y = src
    dx = 0 if x == dst[0] else (1 if dst[0] > x else -1)
    dy = 0 if y == dst[1] else (1 if dst[1] > y else -1)
    if away:
        dx, dy = -dx, -dy
        if dx == 0 and dy == 0:
            dx = 1  # 겹침 — 임의 방향(_step_away 정합)
    cands: list[tuple[int, int]] = []
    if dx != 0:  # x축 우선(_step_toward 규칙)
        cands.append((x + dx, y))
    if dy != 0:
        cands.append((x, y + dy))
    for c in cands:
        if blocked is None or not blocked(c):
            return c
    return src  # 모두 벽 → 제자리


@dataclass
class TickContext:
    """동료가 행동할 공유 세계(동료 제외) — 파티 전원이 같은 ctx를 본다(Phase 3 재사용)."""

    enemies: list[TickEnemy]
    player_pos: tuple[int, int] = (0, 0)
    player_hp: int = 100
    player_max_hp: int = 100
    unexplored_pos: tuple[int, int] | None = None
    blocked: Blocked | None = None  # 타일맵 충돌(None이면 무한 평면 — Phase 0 동작)


def _nearest(ctx: TickContext, pos: tuple[int, int]) -> TickEnemy | None:
    live = [e for e in ctx.enemies if e.hp > 0]
    return min(live, key=lambda e: _dist(pos, e.pos)) if live else None


def build_view_ctx(
    ctx: TickContext, comp: Companion, *, ally_in_danger: bool | None = None
) -> WorldView:
    """공유 ctx + 동료 → 인식(WorldView). 코드 계산(0토큰).

    ally_in_danger 미지정 시 플레이어 HP로 판단. 파티(Phase 3)는 동료 위기까지 포함해 전달.
    """
    enemy = _nearest(ctx, comp.pos)
    danger = (
        ally_in_danger
        if ally_in_danger is not None
        else ctx.player_hp <= ctx.player_max_hp * _DANGER_HP_RATIO
    )
    return WorldView(
        enemy_near=enemy is not None,
        enemy_distance=_dist(comp.pos, enemy.pos) if enemy else 99,
        unexplored=ctx.unexplored_pos is not None,
        ally_in_danger=danger,
    )


def act_companion(
    comp: Companion, ctx: TickContext, *, ally_in_danger: bool | None = None
) -> tuple[DispoAction, str]:
    """동료 1명의 한 행동 — 성향(또는 current_order)대로 ctx에 적용(LLM 없이).

    ★ Phase 1 order가 있으면 따르고, 없으면 default_action(성향 자율). 파티(Phase 3)는
    전원이 이 함수를 같은 ctx로 호출 — 평소 0토큰. ctx.enemies/unexplored_pos를 직접 변경.
    """
    view = build_view_ctx(ctx, comp, ally_in_danger=ally_in_danger)
    action = (
        comp.current_order
        if comp.current_order is not None
        else default_action(comp.disposition, view)
    )
    note = ""
    if action is DispoAction.CHARGE:
        enemy = _nearest(ctx, comp.pos)
        if enemy is not None:
            if _dist(comp.pos, enemy.pos) <= 1:
                berserk = comp.disposition.aggression >= _BERSERK_CRIT
                dmg = apply_critical_damage(comp.attack) if berserk else comp.attack
                enemy.hp -= dmg
                note = f"{enemy.name} 타격 {dmg}{' (강타)' if berserk else ''}"
            else:
                comp.pos = _advance(comp.pos, enemy.pos, ctx.blocked)
                note = "적에게 돌진"
    elif action is DispoAction.RANGED:
        enemy = _nearest(ctx, comp.pos)
        if enemy is not None:
            if _dist(comp.pos, enemy.pos) < _RANGED_KEEP:
                comp.pos = _advance(comp.pos, enemy.pos, ctx.blocked, away=True)
                note = "거리를 벌림"
            else:
                enemy.hp -= max(1, comp.attack // 2)
                note = f"{enemy.name} 원거리 사격"
    elif action is DispoAction.SCOUT:
        if ctx.unexplored_pos is not None:
            comp.pos = _advance(comp.pos, ctx.unexplored_pos, ctx.blocked)
            if comp.pos == ctx.unexplored_pos:
                ctx.unexplored_pos = None
                note = "정찰 완료"
            else:
                note = "앞서 정찰"
    elif action is DispoAction.RESCUE:
        comp.pos = _advance(comp.pos, ctx.player_pos, ctx.blocked)
        note = "위기의 아군에게"
    elif action is DispoAction.FOLLOW:
        if _dist(comp.pos, ctx.player_pos) > 1:
            comp.pos = _advance(comp.pos, ctx.player_pos, ctx.blocked)
        note = "플레이어 곁"
    return action, note


def build_view(world: TickWorld) -> WorldView:
    """단일 동료 인식(하위호환) — TickWorld → WorldView."""
    ctx = TickContext(
        world.enemies, world.player_pos, world.player_hp,
        world.player_max_hp, world.unexplored_pos,
    )
    return build_view_ctx(ctx, world.companion)


def step_tick(world: TickWorld) -> TickResult:
    """한 틱 진행(단일 동료) — act_companion 위임. 동작 불변(Phase 0)."""
    world.tick += 1
    ctx = TickContext(
        world.enemies, world.player_pos, world.player_hp,
        world.player_max_hp, world.unexplored_pos,
    )
    action, note = act_companion(world.companion, ctx)
    world.unexplored_pos = ctx.unexplored_pos  # 정찰 완료 반영(쓰기 back)
    return TickResult(world.tick, action, world.companion.pos, note)


def run_ticks(world: TickWorld, n: int) -> list[TickResult]:
    """n틱 진행 — 동료 자율 행동 궤적을 반환(검증용)."""
    return [step_tick(world) for _ in range(n)]
