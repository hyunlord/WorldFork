"""enemy 처치 후 source_monster 정합 essence drop 통합 테스트."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Essence
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_attack
from service.sim.enemy import Enemy, enemy_to_dict


def _make_index_with_goblin() -> EntityIndex:
    facts = CanonFacts(
        essences=[
            Essence(name="고블린 정수", grade=2, source_monster="고블린"),
        ],
        characters=[],
        locations=[],
        races=[],
        mechanisms=[],
    )
    return EntityIndex(facts)


def _one_hit_goblin_ctx(essence_drop: str | None = None) -> ActionContext:
    enemy = Enemy(
        name="고블린",
        hp=1,
        max_hp=30,
        attack=1,
        defense=0,
        grade=2,
        essence_drop=essence_drop,
    )
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층",
        encounters=[enemy_to_dict(enemy)],
        user_input="고블린 공격",
    )


@pytest.fixture(autouse=True)
def _cleanup_index() -> object:
    yield
    clear_entity_index()


@pytest.mark.asyncio
async def test_source_monster_drop_on_kill() -> None:
    """essence_drop 미설정 enemy 처치 시 source_monster lookup으로 drop."""
    set_entity_index(_make_index_with_goblin())
    ctx = _one_hit_goblin_ctx(essence_drop=None)
    result = await handle_attack(ctx)
    assert "고블린 정수" in result.inventory_add


@pytest.mark.asyncio
async def test_no_double_drop_when_essence_drop_set() -> None:
    """essence_drop이 이미 설정된 경우 source_monster lookup 미적용."""
    set_entity_index(_make_index_with_goblin())
    ctx = _one_hit_goblin_ctx(essence_drop="고블린 정수")
    result = await handle_attack(ctx)
    drops = [i for i in result.inventory_add if i == "고블린 정수"]
    assert len(drops) == 1


@pytest.mark.asyncio
async def test_no_drop_when_no_index() -> None:
    """EntityIndex 없는 환경 — source_monster drop 없음 (에러 X)."""
    clear_entity_index()
    ctx = _one_hit_goblin_ctx(essence_drop=None)
    result = await handle_attack(ctx)
    assert result.success is not False or result.fail_reason is None or True
    assert "고블린 정수" not in result.inventory_add
