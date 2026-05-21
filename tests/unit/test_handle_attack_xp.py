"""Phase D step 6d — handle_attack XP grant tests."""

from __future__ import annotations

import asyncio

from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_attack
from service.sim.enemy import Enemy, enemy_to_dict


def _enemy(name: str = "고블린", grade: int = 1, race: str = "고블린", hp: int = 1) -> dict:
    return enemy_to_dict(
        Enemy(name=name, hp=hp, max_hp=20, attack=2, defense=1, grade=grade, race=race)
    )


def _ctx(
    encounters: list[dict] | None = None,
    defeated: list[str] | None = None,
    player_level: int = 4,
    player_xp: int = 0,
) -> ActionContext:
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층",
        encounters=encounters or [],
        user_input="공격",
        player_level=player_level,
        player_xp=player_xp,
        max_essences=player_level,
        defeated_monster_types=list(defeated or []),
    )


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def test_first_kill_grants_xp() -> None:
    ctx = _ctx(encounters=[_enemy("고블린", grade=1)])
    result = run(handle_attack(ctx))
    assert result.xp_gain == 1
    assert "고블린" in result.defeated_monsters_add


def test_repeat_kill_zero_xp() -> None:
    ctx = _ctx(encounters=[_enemy("고블린", grade=1)], defeated=["고블린"])
    result = run(handle_attack(ctx))
    assert result.xp_gain == 0
    assert result.defeated_monsters_add == []


def test_guardian_modifier() -> None:
    ctx = _ctx(encounters=[_enemy("1층 수호자", grade=3)])
    result = run(handle_attack(ctx))
    assert result.xp_gain == 3 + 3  # grade=3, +guardian bonus 3


def test_stratum_boss_high_xp() -> None:
    ctx = _ctx(encounters=[_enemy("계층군주 드레드피어", grade=1)])
    result = run(handle_attack(ctx))
    assert result.xp_gain == 1 + 99 + 15


def test_level_up_when_xp_threshold_crossed() -> None:
    # L4→L5 threshold = 130, 현재 xp=129, grade=1 enemy → xp+1=130
    ctx = _ctx(encounters=[_enemy("새 몬스터", grade=1, race="새 몬스터")], player_xp=129)
    result = run(handle_attack(ctx))
    assert result.level_up is True
    assert result.new_level == 5


def test_no_level_up_when_xp_below_threshold() -> None:
    ctx = _ctx(encounters=[_enemy("고블린", grade=1)], player_xp=0)
    result = run(handle_attack(ctx))
    assert result.level_up is False
    assert result.new_level is None


def test_no_target_no_xp() -> None:
    ctx = _ctx(encounters=[])
    result = run(handle_attack(ctx))
    assert result.xp_gain == 0
    assert result.success is False
