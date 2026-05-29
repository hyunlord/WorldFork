"""handle_attack — enemy weakness/면역이 narrative+damage에 발현 통합 테스트."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_attack
from service.sim.enemy import Enemy, EnemyType, enemy_to_dict


@pytest.fixture(autouse=True)
def _mock_27b_narrative(monkeypatch: pytest.MonkeyPatch) -> object:
    """27B combat narrative mock → template 경로 검증 (LLM mock 원칙)."""
    clear_entity_index()
    monkeypatch.setattr(
        "service.sim.freeform_handler.compose_combat_narrative",
        lambda *a, **k: "",
    )
    yield
    clear_entity_index()


def _ctx(enemy: Enemy, weapon_name: str | None = None) -> ActionContext:
    from service.sim.equipment import Equipment, EquipmentSet, EquipmentSlot
    equipment = None
    if weapon_name:
        weapon = Equipment(
            name=weapon_name, slot=EquipmentSlot.WEAPON, attack_bonus=0,
        )
        equipment = EquipmentSet(weapon=weapon)
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층",
        encounters=[enemy_to_dict(enemy)],
        user_input="공격",
        equipment=equipment,
    )


@pytest.mark.asyncio
async def test_undead_holy_weapon_weakness_narrative() -> None:
    """언데드 + 신성 무기 → 약점 적중 (weakness narrative)."""
    enemy = Enemy(
        name="스켈레톤", hp=200, max_hp=200, attack=5, defense=0,
        enemy_type=EnemyType.UNDEAD, weakness_types=["신성력", "불"],
    )
    ctx = _ctx(enemy, weapon_name="성스러운 검")
    result = await handle_attack(ctx)
    # 신성력 weakness → 1.5x, 적이 생존(hp 200) → 약점 narrative
    assert "약점" in result.narrative


@pytest.mark.asyncio
async def test_spirit_physical_immune_narrative() -> None:
    """영체 + 물리 무기 → 면역 narrative."""
    enemy = Enemy(
        name="원혼", hp=100, max_hp=100, attack=5, defense=0,
        enemy_type=EnemyType.SPIRIT,
    )
    ctx = _ctx(enemy)  # 무기 없음 → 물리
    result = await handle_attack(ctx)
    assert "통과" in result.narrative or "통하지" in result.narrative


@pytest.mark.asyncio
async def test_encounters_roundtrip_derives_weakness() -> None:
    """encounters dict → enemy_from_dict 경유 weakness 유도 발현."""
    # enemy_type만 지정, weakness_types 미지정 → 자동 유도
    enemy_dict = {
        "name": "예티", "hp": 200, "max_hp": 200, "attack": 5,
        "defense": 0, "enemy_type": "cold_beast", "is_hostile": True,
    }
    from service.sim.equipment import Equipment, EquipmentSet, EquipmentSlot
    weapon = Equipment(name="전격의 창", slot=EquipmentSlot.WEAPON, attack_bonus=0)
    ctx = ActionContext(
        current_hp=100, max_hp=100, inventory=[], location="1층",
        encounters=[enemy_dict], user_input="공격",
        equipment=EquipmentSet(weapon=weapon),
    )
    result = await handle_attack(ctx)
    # cold_beast → 전격 weakness 자동 유도 + 전격 무기 → 약점
    assert "약점" in result.narrative
