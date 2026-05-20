"""Phase D step 6b — handle_attack multi-enemy + status + handle_equip tests."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index, clear_item_registry
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_attack, handle_equip, handle_unequip
from service.sim.enemy import Enemy, enemy_to_dict
from service.sim.equipment import Equipment, EquipmentSet, EquipmentSlot


def _ctx(
    encounters: list[dict[str, object]] | None = None,
    inventory: list[str] | None = None,
    user_input: str = "공격",
    status_effects: list[dict[str, object]] | None = None,
    equipment: EquipmentSet | None = None,
) -> ActionContext:
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=list(inventory or []),
        location="1층",
        encounters=list(encounters or []),
        user_input=user_input,
        status_effects=list(status_effects or []),
        equipment=equipment,
    )


def _goblin(
    hp: int = 30, attack: int = 8, defense: int = 3, grade: int | None = 2
) -> dict[str, object]:
    return enemy_to_dict(Enemy(
        name="고블린",
        hp=hp,
        max_hp=30,
        attack=attack,
        defense=defense,
        grade=grade,
        essence_drop="고블린 정수",
        weakness_races=[],
        abilities=["기본 공격"],
    ))


def _orc(hp: int = 50) -> dict[str, object]:
    return enemy_to_dict(Enemy(
        name="오크",
        hp=hp,
        max_hp=50,
        attack=12,
        defense=5,
        grade=3,
        abilities=["강타"],
    ))


@pytest.fixture(autouse=True)
def _clean() -> object:
    clear_entity_index()
    clear_item_registry()
    yield
    clear_entity_index()
    clear_item_registry()


# ── handle_attack ─────────────────────────────────────────────────────────────


async def test_attack_no_encounters() -> None:
    result = await handle_attack(_ctx())
    assert result.success is False
    assert result.fail_reason == "no_target"


async def test_attack_single_enemy_damage() -> None:
    ctx = _ctx(encounters=[_goblin(hp=30, defense=3)])
    result = await handle_attack(ctx)
    assert result.success is True
    assert result.encounter_resolved is False
    assert result.encounters_update is not None
    hp = result.encounters_update[0].get("hp")
    assert isinstance(hp, int)
    assert hp == 23  # base 10 - def 3 = 7 damage


async def test_attack_single_enemy_resolved() -> None:
    ctx = _ctx(encounters=[_goblin(hp=5, defense=0)])
    result = await handle_attack(ctx)
    assert result.encounter_resolved is True
    assert result.encounters_update is None
    assert "고블린 정수" in result.inventory_add


async def test_attack_multi_enemy_enemy_turn_runs() -> None:
    ctx = _ctx(encounters=[_goblin(hp=30), _orc(hp=50)])
    result = await handle_attack(ctx)
    # 고블린 생존 → 오크도 행동 → hp 감소
    assert result.hp_change < 0


async def test_attack_multi_enemy_target_by_name() -> None:
    ctx = _ctx(encounters=[_goblin(hp=30), _orc(hp=50)], user_input="오크를 공격")
    result = await handle_attack(ctx)
    # 오크가 먼저 타격 — 오크 hp < 50
    assert result.encounters_update is not None
    orc = next((e for e in result.encounters_update if e.get("name") == "오크"), None)
    assert orc is not None
    assert int(orc.get("hp", 50)) < 50  # type: ignore[arg-type]


async def test_attack_status_carried_forward() -> None:
    poison_dict: dict[str, object] = {
        "type": "poison", "duration": 3, "intensity": 3, "source": "독"
    }
    ctx = _ctx(encounters=[_goblin(hp=30)], status_effects=[poison_dict])
    result = await handle_attack(ctx)
    # status_update 가 있어야 하고 (poison 지속 또는 만료)
    assert result.status_update is not None


async def test_attack_essence_drop_on_resolve() -> None:
    ctx = _ctx(encounters=[_goblin(hp=5, defense=0)])
    result = await handle_attack(ctx)
    assert "고블린 정수" in result.inventory_add


# ── handle_equip ──────────────────────────────────────────────────────────────


async def test_equip_no_registry() -> None:
    ctx = _ctx(inventory=["철검"])
    result = await handle_equip(ctx)
    assert result.success is False
    assert result.fail_reason == "no_registry"


async def test_equip_empty_inventory() -> None:
    ctx = _ctx(inventory=[])
    result = await handle_equip(ctx)
    assert result.success is False


# ── handle_unequip ────────────────────────────────────────────────────────────


async def test_unequip_no_equipment() -> None:
    ctx = _ctx(user_input="무기 해제")
    result = await handle_unequip(ctx)
    assert result.success is False
    assert result.fail_reason == "no_equipment"


async def test_unequip_removes_weapon() -> None:
    weapon = Equipment(name="철검", slot=EquipmentSlot.WEAPON, attack_bonus=5)
    eq_set = EquipmentSet(weapon=weapon)
    ctx = _ctx(user_input="철검 해제", equipment=eq_set)
    result = await handle_unequip(ctx)
    assert result.success is True
    assert "철검" in result.inventory_add
    assert result.equipment_update is not None
    assert result.equipment_update.get("weapon") is None
