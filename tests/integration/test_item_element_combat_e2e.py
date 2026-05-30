"""무기 element → combat 약점 통합 테스트 (ItemRegistry element → _get_attack_elements)."""

from __future__ import annotations

import pytest

from service.canon.context import clear_entity_index
from service.sim.action_context import ActionContext
from service.sim.action_handlers import _get_attack_elements
from service.sim.combat import compute_damage_multiplier
from service.sim.enemy import enemy_from_dict
from service.sim.equipment import (
    Equipment,
    EquipmentSet,
    EquipmentSlot,
    equipment_from_dict,
    equipment_to_dict,
)


@pytest.fixture(autouse=True)
def _cleanup() -> object:
    clear_entity_index()
    yield
    clear_entity_index()


def test_equipment_element_roundtrip() -> None:
    """Equipment.element 직렬화 보존."""
    eq = Equipment(name="화염검", slot=EquipmentSlot.WEAPON, element="불")
    d = equipment_to_dict(eq)
    assert d["element"] == "불"
    assert equipment_from_dict(d).element == "불"


def test_equipment_from_dict_backward_compat() -> None:
    """기존 dict (element 미보유) → 빈 문자열."""
    eq = equipment_from_dict({"name": "검", "slot": "weapon", "attack_bonus": 5})
    assert eq.element == ""


def test_weapon_element_in_attack_elements() -> None:
    """장착 무기 element → _get_attack_elements."""
    weapon = Equipment(name="롱소드", slot=EquipmentSlot.WEAPON, element="불")
    ctx = ActionContext(
        current_hp=100, max_hp=100, inventory=[], location="1층",
        equipment=EquipmentSet(weapon=weapon),
    )
    elements = _get_attack_elements(ctx)
    assert "물리" in elements
    assert "불" in elements  # ★ ItemRegistry 파싱 element (name 키워드 아닌 .element)


def test_weapon_element_triggers_weakness() -> None:
    """불 무기 → undead 약점 1.5x (★ 13deef0 결합)."""
    weapon = Equipment(name="롱소드", slot=EquipmentSlot.WEAPON, element="불")
    ctx = ActionContext(
        current_hp=100, max_hp=100, inventory=[], location="1층",
        equipment=EquipmentSet(weapon=weapon),
    )
    elements = _get_attack_elements(ctx)
    undead = enemy_from_dict({"name": "스켈레톤", "enemy_type": "undead"})
    assert compute_damage_multiplier(undead, elements) == 1.5


def test_player_sensitivities_merge_into_total() -> None:
    """소비 아이템 누적(player_sensitivities)이 total_sensitivities에 병합."""
    ctx = ActionContext(
        current_hp=100, max_hp=100, inventory=[], location="1층",
        player_sensitivities={"냉기": 3},
        absorbed_essences=[{
            "essence_name": "X", "stat_bundle": {}, "skills": [], "grade": None,
            "resistances": {}, "etc_abilities": [], "attack_elements": [],
            "sensitivities": {"냉기": 2},
        }],
    )
    # essence 2 + player(소비) 3 = 5
    assert ctx.total_sensitivities == {"냉기": 5}


@pytest.mark.asyncio
async def test_use_sensitivity_item_consumes_and_grants() -> None:
    """감응도 소비 아이템 사용 → sensitivity_add delta + 소비 (★ registry 소비처)."""
    from service.canon.context import clear_item_registry, set_item_registry
    from service.canon.items import ItemRegistry
    from service.canon.schema import CanonFacts, Mechanism
    from service.sim.action_handlers import handle_use_item

    set_item_registry(ItemRegistry(CanonFacts(
        essences=[], characters=[], locations=[], races=[],
        mechanisms=[Mechanism(name="빙정", category="magic",
                              description="냉기 감응도를 영구적으로 +3 상승.")],
    )))
    try:
        ctx = ActionContext(
            current_hp=100, max_hp=100, inventory=["빙정"], location="1층",
            user_input="빙정 사용",
        )
        result = await handle_use_item(ctx)
        assert result.sensitivity_add == {"냉기": 3}
        assert "빙정" in result.inventory_remove
        assert "냉기 감응도" in result.narrative
    finally:
        clear_item_registry()
