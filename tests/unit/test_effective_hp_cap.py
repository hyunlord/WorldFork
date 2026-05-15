"""Phase 9.11 effective-hp-cap — disability gameplay 영향 실현.

검증 본질 (★ 9.10 effective_hp_max property dead consumer 방지):
- WAIT_IN_VILLAGE HP 회복 cap = effective_hp_max (★ disability 적용)
- USE_ITEM 포션 회복 cap = effective_hp_max
- critical injury 회복 + disability transition → hp clamp invariant
- HEAL_AT_TEMPLE — disability 치료 → effective_hp_max 복구 자연 (★ 변경 X)
- ATTACK 변경 X (★ HP 감소만, cap 본격 X)

본문 정합 (★ 9.10 본문 정합 승계):
- 71/214화: 절단 narrative
- 117/268화: 회복 path
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Disability,
    Injury,
    Item,
    ItemCategory,
    Race,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    HP_RECOVERY_PER_DAY,
    POTION_HEAL_AMOUNT,
    execute_wait_in_village,
    use_item,
)


def _potion() -> Item:
    return Item(
        name="회복 포션",
        category=ItemCategory.CONSUMABLE,
        weight=1,
    )


def _village_world() -> WorldState:
    w = WorldState()
    w.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    return w


# ─── 1. WAIT_IN_VILLAGE HP 회복 cap ───


def test_wait_recovery_caps_at_effective() -> None:
    """기존 disability 적용 시 회복 cap = effective_hp_max."""
    world = _village_world()
    c = Character(name="비요른", race=Race.BARBARIAN, hp=70, hp_max=100)
    c.disabilities.append(
        Disability(body_part="arm", kind="amputation", hp_max_penalty=20)
    )
    # effective_hp_max = 80
    execute_wait_in_village("비요른", [c], world)
    assert c.hp == 80  # ★ 70 + 10 = 80 (★ 정확히 cap)


def test_wait_recovery_does_not_exceed_effective() -> None:
    """현재 hp + recovery > effective → cap 적용."""
    world = _village_world()
    c = Character(name="비요른", race=Race.BARBARIAN, hp=75, hp_max=100)
    c.disabilities.append(Disability(body_part="arm", hp_max_penalty=20))
    # effective = 80
    execute_wait_in_village("비요른", [c], world)
    assert c.hp == 80  # ★ 75 + 10 = 85 → clamp 80


def test_wait_no_disability_uses_hp_max() -> None:
    """disability X 시 기존 hp_max cap 유지."""
    world = _village_world()
    c = Character(name="비요른", race=Race.BARBARIAN, hp=90, hp_max=100)
    execute_wait_in_village("비요른", [c], world)
    assert c.hp == 100


def test_wait_full_hp_effective_no_change() -> None:
    """이미 effective_hp_max 본격 → 회복 hp_gain=0."""
    world = _village_world()
    c = Character(name="비요른", race=Race.BARBARIAN, hp=80, hp_max=100)
    c.disabilities.append(Disability(body_part="leg", hp_max_penalty=20))
    result = execute_wait_in_village("비요른", [c], world)
    assert c.hp == 80
    # hp_gain side_effect 본격 X (★ hp_gain=0)
    assert not any(
        s.startswith("hp_gain=비요른:") for s in result.side_effects
    )


# ─── 2. USE_ITEM 포션 cap ───


def test_potion_caps_at_effective_hp_max() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN, hp=40, hp_max=100)
    c.disabilities.append(Disability(body_part="leg", hp_max_penalty=20))
    c.inventory.items.append(_potion())
    result = use_item(c, "회복 포션")
    assert result.success is True
    # 40 + 50 = 90 → cap 80
    assert c.hp == 80


def test_potion_no_disability_uses_hp_max() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN, hp=40, hp_max=100)
    c.inventory.items.append(_potion())
    result = use_item(c, "회복 포션")
    assert result.success is True
    assert c.hp == 40 + POTION_HEAL_AMOUNT


def test_potion_full_effective_no_gain() -> None:
    """이미 effective 본격 → hp_gain=0."""
    c = Character(name="비요른", race=Race.BARBARIAN, hp=80, hp_max=100)
    c.disabilities.append(Disability(body_part="leg", hp_max_penalty=20))
    c.inventory.items.append(_potion())
    result = use_item(c, "회복 포션")
    assert result.success is True
    assert c.hp == 80
    assert any(s == "hp_gain=비요른:+0" for s in result.side_effects)


def test_potion_message_shows_effective_hp_max() -> None:
    """포션 message 본격 effective_hp_max 표시 (★ display 정합)."""
    c = Character(name="비요른", race=Race.BARBARIAN, hp=40, hp_max=100)
    c.disabilities.append(Disability(body_part="leg", hp_max_penalty=20))
    c.inventory.items.append(_potion())
    result = use_item(c, "회복 포션")
    assert "/80" in result.message  # ★ effective HP_max


# ─── 3. critical injury 회복 + disability transition hp clamp ───


def test_critical_recovery_clamps_hp_to_effective() -> None:
    """critical 회복 day → HP_RECOVERY 적용 후 disability 생성 → hp clamp."""
    world = _village_world()
    c = Character(name="비요른", race=Race.BARBARIAN, hp=95, hp_max=100)
    c.injuries.append(
        Injury(severity="critical", body_part="arm", recovery_days=1)
    )
    # day 진행:
    # 1. HP 회복: 95 + 10 = 105 → effective(=hp_max 100) cap → 100
    # 2. injury recovery_days 0 → disability arm 생성 (penalty 10)
    # 3. clamp: hp 100 > effective 90 → hp = 90
    execute_wait_in_village("비요른", [c], world)
    assert len(c.disabilities) == 1
    assert c.disabilities[0].body_part == "arm"
    assert c.hp == 90  # ★ clamp 적용


def test_critical_recovery_low_hp_no_clamp() -> None:
    """hp가 새 effective 본격 X 시 clamp 변경 X."""
    world = _village_world()
    c = Character(name="비요른", race=Race.BARBARIAN, hp=50, hp_max=100)
    c.injuries.append(
        Injury(severity="critical", body_part="arm", recovery_days=1)
    )
    # HP 회복: 50 + 10 = 60 → cap 100 → 60
    # disability arm (penalty 10) → effective 90
    # 60 ≤ 90 → clamp 변경 X
    execute_wait_in_village("비요른", [c], world)
    assert c.hp == 60


def test_critical_neck_recovery_severe_clamp() -> None:
    """neck disability penalty 25 — 가장 큰 clamp."""
    world = _village_world()
    c = Character(name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100)
    c.injuries.append(
        Injury(severity="critical", body_part="neck", recovery_days=1)
    )
    execute_wait_in_village("비요른", [c], world)
    assert len(c.disabilities) == 1
    # effective = 100 - 25 = 75
    assert c.hp == 75


# ─── 4. dead member 본격 회복 X (★ 9 회귀) ───


def test_wait_dead_member_no_recovery() -> None:
    world = _village_world()
    c = Character(name="비요른", race=Race.BARBARIAN, hp=0, hp_max=100)
    execute_wait_in_village("비요른", [c], world)
    assert c.hp == 0  # ★ 영구


# ─── 5. HP_RECOVERY 정합 ───


def test_hp_recovery_per_day_constant() -> None:
    """본 commit 변경 X — constant 본격."""
    assert HP_RECOVERY_PER_DAY == 10


def test_potion_heal_amount_constant() -> None:
    """본 commit 변경 X — constant 본격."""
    assert POTION_HEAL_AMOUNT == 50
