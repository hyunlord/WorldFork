"""V3 Phase 3 — 파티 확장 (3-4명 + 상호작용 + LLM 빈도 튜닝).

DESIGN_disposition_engine.md 2장(비용 핵심). 동료 1명(Phase 0-2)을 3-4명 파티로 확장.
평소 틱은 전원이 act_companion(코드, 0토큰)으로 자율 — 파티가 늘어도 LLM 호출은 0.
★ LLM은 '분기점'에서만: 플레이어 개입, 새 적 출현, 아군 위기, 동료 성향 충돌. detect_branch
(코드)가 분기점을 감지해 LLM 호출 시점을 좁힌다 — 파티 × 매 틱 LLM 폭발을 막는 핵심.

파티 제어: command_member(특정 동료) / command_all(전원). 동료 간 상호작용: 위기 동료는
유대 높은 동료가 구원(코드), 저돌 vs 신중의 의견 충돌은 분기점으로 감지(LLM 대화는 호출자).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from core.llm.local_client import LocalLLMClient
from service.sim.disposition import Companion, DispoAction, default_action
from service.sim.disposition_command import CommandResponse, apply_order, interpret_command
from service.sim.disposition_tick import (
    Blocked,
    TickContext,
    TickEnemy,
    TickResult,
    _advance,
    _dist,
    act_companion,
    build_view_ctx,
)
from service.sim.status import StatusEffect, StatusType, apply_status_effects

# 아군 위기 HP 비율(구원/분기 트리거) — 단일 틱과 정합.
_DANGER_HP_RATIO = 0.35

# enemy_step 전투 상수 — 일방 전투 방지(빗맞음 가능) + 출혈 일부 부여.
_ENEMY_REACH = 1  # 근접 사정거리(맨해튼)
_ENEMY_HIT_CHANCE = 0.75  # 명중률(나머지는 빗맞음)
_ENEMY_BLEED_CHANCE = 0.25  # 명중 시 출혈 부여 확률
_BLEED_DURATION = 2
_BLEED_INTENSITY = 2


class BranchReason(StrEnum):
    """LLM을 부를 만한 분기점 — 코드가 감지(그 외 평소엔 LLM 0)."""

    NEW_ENEMY = "new_enemy"  # 새 적 출현
    ALLY_CRITICAL = "ally_critical"  # 아군(동료/플레이어) 위기
    CONFLICT = "conflict"  # 동료 간 성향 충돌(돌격 vs 신중)


@dataclass
class PartyWorld:
    """파티 세계 — 동료 3-4명이 같은 ctx를 공유."""

    companions: list[Companion]
    enemies: list[TickEnemy] = field(default_factory=list)
    player_pos: tuple[int, int] = (0, 0)
    player_hp: int = 100
    player_max_hp: int = 100
    player_status: list[StatusEffect] = field(default_factory=list)  # 플레이어 출혈 등
    unexplored_pos: tuple[int, int] | None = None
    blocked: Blocked | None = None  # 타일맵 충돌(None이면 무한 평면 — 테스트 기본)
    tick: int = 0
    _prev_live: int = 0  # NEW_ENEMY 감지용(직전 생존 적 수)

    @property
    def defeat(self) -> bool:
        """슬라이스 패배 — 플레이어(비요른) HP 0(자동 진행 정지). §6 세이브는 범위 밖."""
        return self.player_hp <= 0

    def context(self) -> TickContext:
        return TickContext(
            self.enemies, self.player_pos, self.player_hp,
            self.player_max_hp, self.unexplored_pos, self.blocked,
        )


def _ally_in_danger(world: PartyWorld, me: Companion) -> bool:
    """나 외의 아군(다른 동료 or 플레이어)이 위기인가 — 구원 판단(파티)."""
    if world.player_hp <= world.player_max_hp * _DANGER_HP_RATIO:
        return True
    return any(
        c is not me and c.hp <= c.max_hp * _DANGER_HP_RATIO for c in world.companions
    )


def detect_branch(world: PartyWorld) -> list[BranchReason]:
    """★ 분기점 감지(코드, 0토큰) — LLM을 부를 시점만 좁힌다(비용 핵심).

    new_enemy: 생존 적이 늘었다 / ally_critical: 아군 저HP / conflict: 미지시 동료들이
    전투서 돌격 vs 신중으로 갈린다. 평소엔 빈 리스트 → LLM 호출 0.
    """
    reasons: list[BranchReason] = []
    ctx = world.context()
    live = sum(1 for e in world.enemies if e.hp > 0)
    if live > world._prev_live:
        reasons.append(BranchReason.NEW_ENEMY)
    if any(c.hp <= c.max_hp * _DANGER_HP_RATIO for c in world.companions) or (
        world.player_hp <= world.player_max_hp * _DANGER_HP_RATIO
    ):
        reasons.append(BranchReason.ALLY_CRITICAL)
    if live > 0:
        actions = {
            default_action(c.disposition, build_view_ctx(ctx, c))
            for c in world.companions
            if c.current_order is None
        }
        if DispoAction.CHARGE in actions and (
            DispoAction.RANGED in actions or DispoAction.SCOUT in actions
        ):
            reasons.append(BranchReason.CONFLICT)
    world._prev_live = live
    return reasons


def party_step(world: PartyWorld) -> list[TickResult]:
    """파티 전원 한 틱 — 각자 성향(또는 명령)대로 자율(★ 코드, LLM 0토큰).

    전투불능(HP 0) 동료는 행동을 건너뛴다(제거/부활 없음 — 슬라이스).
    """
    world.tick += 1
    ctx = world.context()
    results: list[TickResult] = []
    for comp in world.companions:
        if comp.downed:
            continue
        action, note = act_companion(
            comp, ctx, ally_in_danger=_ally_in_danger(world, comp)
        )
        results.append(TickResult(world.tick, action, comp.pos, f"{comp.name}: {note}"))
    world.unexplored_pos = ctx.unexplored_pos  # 정찰 완료 반영
    return results


def _bleed(source: str) -> StatusEffect:
    """출혈 1건 — status.py BLEED 재사용(intensity/duration만 슬라이스 값)."""
    return StatusEffect(
        type=StatusType.BLEED,
        duration=_BLEED_DURATION,
        intensity=_BLEED_INTENSITY,
        source=source,
    )


@dataclass
class _Target:
    """적이 노릴 대상(동료 또는 비요른) — 위치/HP/상태에 통일 접근."""

    name: str
    is_player: bool
    comp: Companion | None  # 동료면 그 객체, 플레이어면 None

    def pos(self, world: PartyWorld) -> tuple[int, int]:
        if self.is_player:
            return world.player_pos
        assert self.comp is not None
        return self.comp.pos

    def hp(self, world: PartyWorld) -> int:
        if self.is_player:
            return world.player_hp
        assert self.comp is not None
        return self.comp.hp

    def hit(self, world: PartyWorld, dmg: int, bleed: bool) -> int:
        """피해 적용(0 클램프) + 선택적 출혈. 적용 후 HP 반환."""
        if self.is_player:
            world.player_hp = max(0, world.player_hp - dmg)
            if bleed:
                world.player_status.append(_bleed("적"))
            return world.player_hp
        assert self.comp is not None
        self.comp.hp = max(0, self.comp.hp - dmg)
        if bleed:
            self.comp.status.append(_bleed("적"))
        return self.comp.hp


def _live_targets(world: PartyWorld) -> list[_Target]:
    """살아있는 대상 — 전투불능 아닌 동료 + (생존 시) 비요른."""
    out: list[_Target] = [
        _Target(c.name, False, c) for c in world.companions if not c.downed
    ]
    if world.player_hp > 0:
        out.append(_Target("비요른", True, None))
    return out


def enemy_step(
    world: PartyWorld,
    *,
    rand: Callable[[], float] = random.random,
) -> list[str]:
    """적의 반격 한 틱 — party_step 다음에 호출(틱 순서: 파티 → 적).

    1) 파티/플레이어의 출혈 등 상태이상 적용(지속 피해). 2) 살아있는 적이 가장 가까운
    생존 대상(동료 or 비요른)을 근접 시 공격(명중 판정 — 빗맞음 가능, 피해, 일부 출혈),
    아니면 한 칸 접근(벽 인지). HP는 0에서 클램프. ★ V2 턴 루프는 부활하지 않는다.
    """
    notes: list[str] = []

    # 1) 상태이상(출혈) 지속 피해 — 동료 + 플레이어
    for comp in world.companions:
        if comp.status:
            before = comp.hp
            comp.hp, comp.status = apply_status_effects(comp.hp, comp.max_hp, comp.status)
            if comp.hp < before:
                notes.append(f"{comp.name}: 「출혈」 {before - comp.hp} 피해")
                if comp.downed:
                    notes.append(f"{comp.name}: 쓰러졌다")
    if world.player_status:
        pbefore = world.player_hp
        world.player_hp, world.player_status = apply_status_effects(
            world.player_hp, world.player_max_hp, world.player_status
        )
        if world.player_hp < pbefore:
            notes.append(f"비요른: 「출혈」 {pbefore - world.player_hp} 피해")

    # 2) 적 행동 — 근접 공격(명중/빗맞음/출혈) 또는 접근(벽 인지)
    for enemy in world.enemies:
        if enemy.hp <= 0:
            continue
        targets = _live_targets(world)
        if not targets:
            continue
        target = min(targets, key=lambda t: _dist(enemy.pos, t.pos(world)))
        if _dist(enemy.pos, target.pos(world)) <= _ENEMY_REACH:
            if rand() < _ENEMY_HIT_CHANCE:
                dmg = max(1, enemy.attack)
                bleed = rand() < _ENEMY_BLEED_CHANCE
                hp_after = target.hit(world, dmg, bleed)
                notes.append(f"{enemy.name} → {target.name} 명중 {dmg}")
                if bleed:
                    notes.append(f"{target.name}: 「출혈」 부여")
                if hp_after <= 0 and not target.is_player:
                    notes.append(f"{target.name}: 쓰러졌다")
            else:
                notes.append(f"{enemy.name} → {target.name} 빗나감")
        else:
            enemy.pos = _advance(enemy.pos, target.pos(world), world.blocked)
    return notes


def find_member(world: PartyWorld, name: str) -> Companion | None:
    return next((c for c in world.companions if c.name == name), None)


def command_member(
    world: PartyWorld,
    name: str,
    text: str,
    situation: str,
    *,
    client: LocalLLMClient | None = None,
) -> CommandResponse | None:
    """특정 동료에게 지시 — 그 동료 성향으로 해석·반영(Phase 1, 분기점=개입)."""
    comp = find_member(world, name)
    if comp is None:
        return None
    resp = interpret_command(comp, text, situation, client=client)
    apply_order(comp, resp)
    return resp


def command_all(
    world: PartyWorld,
    text: str,
    situation: str,
    *,
    client: LocalLLMClient | None = None,
) -> dict[str, CommandResponse]:
    """전원 지시 — 각 동료가 자기 성향으로 해석(같은 명령, 다른 반응)."""
    out: dict[str, CommandResponse] = {}
    for comp in world.companions:
        resp = interpret_command(comp, text, situation, client=client)
        apply_order(comp, resp)
        out[comp.name] = resp
    return out
