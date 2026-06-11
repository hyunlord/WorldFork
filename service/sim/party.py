"""V3 Phase 3 — 파티 확장 (3-4명 + 상호작용 + LLM 빈도 튜닝).

DESIGN_disposition_engine.md 2장(비용 핵심). 동료 1명(Phase 0-2)을 3-4명 파티로 확장.
평소 틱은 전원이 act_companion(코드, 0토큰)으로 자율 — 파티가 늘어도 LLM 호출은 0.
★ LLM은 '분기점'에서만: 플레이어 개입, 새 적 출현, 아군 위기, 동료 성향 충돌. detect_branch
(코드)가 분기점을 감지해 LLM 호출 시점을 좁힌다 — 파티 × 매 틱 LLM 폭발을 막는 핵심.

파티 제어: command_member(특정 동료) / command_all(전원). 동료 간 상호작용: 위기 동료는
유대 높은 동료가 구원(코드), 저돌 vs 신중의 의견 충돌은 분기점으로 감지(LLM 대화는 호출자).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from core.llm.local_client import LocalLLMClient
from service.sim.disposition import Companion, DispoAction, default_action
from service.sim.disposition_command import CommandResponse, apply_order, interpret_command
from service.sim.disposition_tick import (
    TickContext,
    TickEnemy,
    TickResult,
    act_companion,
    build_view_ctx,
)

# 아군 위기 HP 비율(구원/분기 트리거) — 단일 틱과 정합.
_DANGER_HP_RATIO = 0.35


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
    unexplored_pos: tuple[int, int] | None = None
    tick: int = 0
    _prev_live: int = 0  # NEW_ENEMY 감지용(직전 생존 적 수)

    def context(self) -> TickContext:
        return TickContext(
            self.enemies, self.player_pos, self.player_hp,
            self.player_max_hp, self.unexplored_pos,
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
    """파티 전원 한 틱 — 각자 성향(또는 명령)대로 자율(★ 코드, LLM 0토큰)."""
    world.tick += 1
    ctx = world.context()
    results: list[TickResult] = []
    for comp in world.companions:
        action, note = act_companion(
            comp, ctx, ally_in_danger=_ally_in_danger(world, comp)
        )
        results.append(TickResult(world.tick, action, comp.pos, f"{comp.name}: {note}"))
    world.unexplored_pos = ctx.unexplored_pos  # 정찰 완료 반영
    return results


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
