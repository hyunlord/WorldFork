"""AI GM 슬라이스 Phase 3 — 내러티브 턴 전투(좌표 없는 라운드 구조).

★ 공간 tick 루프(disposition_tick의 좌표/이동/사거리)는 쓰지 않는다. 서사 전투는 한 라운드 =
플레이어 행동 + 카이라(아이나르) 성향 행동 + 적 행동. 새 전투 메커니즘을 만들지 않고 기존
프리미티브만 재사용한다: 명중·치명타(combat), 출혈(status BLEED), 드롭(loot 마석/정수),
성향 해석(disposition_command). GM은 라운드당 1회, 확정된 결과를 '서술만' 한다(코드가 먼저).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from core.llm.local_client import LocalLLMClient
from service.sim.combat import apply_critical_damage, compute_critical_hit
from service.sim.disposition import Companion, DispoAction
from service.sim.disposition_command import CommandResponse, interpret_command
from service.sim.loot import Inventory, award_drop
from service.sim.status import StatusEffect, StatusType, apply_status_effects

# 무기 → 기본 피해(빌드 차별: 도끼 균형 / 망치 고화력 / 대검 치명 의존). 미지정은 맨손.
_WEAPON_ATTACK: dict[str, int] = {"양손도끼": 16, "양손망치": 22, "대검": 14}
_DEFAULT_ATTACK = 10
_PLAYER_HIT = 0.85
_PLAYER_AGILITY = 12  # compute_critical_hit → 치명타율 ~11%
_FOE_HIT = 0.70
_FOE_BLEED = 0.30
_BLEED_DURATION, _BLEED_INTENSITY = 2, 3

# 적 종류 → 전투 스틸 자산(public/assets/worldfork/ui_combat_monster_*).
_FOE_SPRITE: dict[str, str] = {
    "고블린": "goblin",
    "칼날늑대": "blade_wolf",
    "구울": "ghoul",
    "노움": "gnome",
}


@dataclass
class Foe:
    """내러티브 전투 적 — 좌표 없음(HP/공격력/드롭만)."""

    name: str
    hp: int
    max_hp: int
    attack: int = 8
    grade: int = 9
    essence_drop: str = ""

    @property
    def alive(self) -> bool:
        return self.hp > 0


def player_attack_damage(weapon: str) -> int:
    """무기 → 기본 피해(빌드 차별)."""
    return _WEAPON_ATTACK.get(weapon, _DEFAULT_ATTACK)


@dataclass
class RoundResult:
    """한 라운드의 확정 결과 — GM 서술 재료 + 세션 반영용."""

    lines: list[str] = field(default_factory=list)  # 확정 사실(서술 재료)
    player_hp: int = 0
    player_status: list[StatusEffect] = field(default_factory=list)
    foe_hp: int = 0
    kaira_reaction: CommandResponse | None = None
    foe_defeated: bool = False
    drops: list[str] = field(default_factory=list)
    illustration: str = "ui_combat_bjorn_action"  # 이벤트 기반 기본 스틸(GM 미지정 시 fallback)


def _kaira_damage(kaira: Companion, action: DispoAction) -> int:
    """카이라 성향 행동 → 피해. 돌격(저돌≥80 강타)/원거리(절반)/그 외 비전투(0)."""
    if action is DispoAction.CHARGE:
        if kaira.disposition.aggression >= 80:
            return apply_critical_damage(kaira.attack)
        return kaira.attack
    if action is DispoAction.RANGED:
        return max(1, kaira.attack // 2)
    return 0  # scout/rescue/follow/hold — 이 라운드 비전투


def resolve_round(
    *,
    player_action: str,
    weapon: str,
    player_hp: int,
    player_max_hp: int,
    player_status: list[StatusEffect],
    foe: Foe,
    kaira: Companion,
    inv: Inventory,
    situation: str,
    rand: Callable[[], float] = random.random,
    client: LocalLLMClient | None = None,
) -> RoundResult:
    """한 라운드 판정(코드) — 플레이어 → 카이라(성향) → 적 → 출혈 → 드롭.

    foe.hp/inv는 직접 변경(드롭 반영). player_hp/status는 반환값으로 돌려준다(불변 입력).
    ★ 카이라는 interpret_command(성향 마찰) — 플레이어 지시를 순응/변형/거부로 받아 행동.
    """
    lines: list[str] = []
    status = list(player_status)
    illustration = "ui_combat_bjorn_action"

    # 1) 플레이어 공격 — 명중 + 치명타(프리미티브)
    base = player_attack_damage(weapon)
    if rand() < _PLAYER_HIT:
        crit = compute_critical_hit(_PLAYER_AGILITY, rand_func=rand)
        dmg = apply_critical_damage(base) if crit else base
        foe.hp = max(0, foe.hp - dmg)
        lines.append(
            f"투르윈의 {weapon or '주먹'}이 {foe.name}에게 {dmg} 피해"
            f"{' (치명타!)' if crit else ''}"
        )
        illustration = "ui_combat_vfx_axe_strike" if crit else "ui_combat_bjorn_action"
    else:
        lines.append(f"투르윈의 공격이 {foe.name}을(를) 빗맞혔다")

    # 2) 카이라 성향 행동 — 플레이어 지시를 성향대로(순응/변형/거부) → 피해
    reaction = interpret_command(kaira, player_action, situation, client=client)
    if foe.alive:
        kd = _kaira_damage(kaira, reaction.action)
        if kd > 0:
            foe.hp = max(0, foe.hp - kd)
            lines.append(
                f"카이라「{reaction.reaction.value}」 {foe.name}에게 {kd} 피해 — {reaction.speech}"
            )
            if reaction.action is DispoAction.RANGED:
                illustration = "ui_combat_vfx_magic_missile"
        else:
            lines.append(f"카이라「{reaction.reaction.value}」 {reaction.speech}")

    # 3) 적 행동(생존 시) — 명중 + 피해 + 출혈(status BLEED)
    if foe.alive:
        if rand() < _FOE_HIT:
            fdmg = max(1, foe.attack)
            player_hp = max(0, player_hp - fdmg)
            lines.append(f"{foe.name}이(가) 투르윈에게 {fdmg} 피해")
            illustration = "ui_combat_monster_" + _FOE_SPRITE.get(foe.name, "goblin")
            if rand() < _FOE_BLEED:
                status.append(
                    StatusEffect(
                        StatusType.BLEED, _BLEED_DURATION, _BLEED_INTENSITY, foe.name
                    )
                )
                lines.append("투르윈: 「출혈」 부여")
        else:
            lines.append(f"{foe.name}의 공격이 빗나갔다")

    # 4) 출혈 지속 피해(status 프리미티브)
    if status:
        before = player_hp
        player_hp, status = apply_status_effects(player_hp, player_max_hp, status)
        if player_hp < before:
            lines.append(f"투르윈: 「출혈」 {before - player_hp} 지속 피해")

    # 5) 처치 → 드롭(loot 프리미티브: 마석→소지금/인벤, 정수→인벤)
    drops: list[str] = []
    defeated = not foe.alive
    if defeated:
        lines.append(f"「{foe.name}을(를) 쓰러뜨렸다.」")
        drops = award_drop(inv, grade=foe.grade, essence=foe.essence_drop)
        illustration = "ui_combat_vfx_axe_strike"

    return RoundResult(
        lines=lines,
        player_hp=player_hp,
        player_status=status,
        foe_hp=foe.hp,
        kaira_reaction=reaction,
        foe_defeated=defeated,
        drops=drops,
        illustration=illustration,
    )
