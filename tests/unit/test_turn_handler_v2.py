"""Stage 7 schema 진짜 mutate 테스트 (★ production 사용 본격).

본 commit 본질:
- Character.light_state mutate
- Character.consume_essence_at_position 호출
- Character.has_active_light 호출
- WorldState.active_bounties mutate
- WorldState.hours_in_dungeon 누적
- HP 변동 + 영구사망
- FloatingEssence 30분 자연 소멸
"""

from __future__ import annotations

from service.game.state_v2 import (
    BountyEntry,
    Character,
    Essence,
    EssenceColor,
    EssenceGrade,
    EssenceOrigin,
    EssenceType,
    FloatingEssence,
    LightSource,
    LightSourceType,
    LightStateOnCharacter,
    Race,
    WorldState,
)
from service.game.turn_handler_v2 import (
    activate_light_source,
    advance_time,
    apply_damage,
    attempt_essence_absorb,
    issue_bounty,
    resolve_bounty,
)


def _torch() -> LightSource:
    return LightSource(
        name="횃불",
        light_type=LightSourceType.TORCH,
        duration_hours=72.0,
        cooldown_hours=None,
        radius_meters=10.0,
        cost_stones=10000,
        is_consumable=False,
    )


def _spirit_lantern() -> LightSource:
    return LightSource(
        name="정령 등불",
        light_type=LightSourceType.SPIRIT,
        duration_hours=10.0,
        cooldown_hours=2.0,
        radius_meters=10.0,
        cost_stones=0,
        is_consumable=False,
        requires_race="요정",
    )


def _flare() -> LightSource:
    return LightSource(
        name="조명탄",
        light_type=LightSourceType.FLARE,
        duration_hours=None,
        cooldown_hours=None,
        radius_meters=50.0,
        cost_stones=0,
        is_consumable=True,
    )


def _essence(name: str = "고블린 정수") -> Essence:
    return Essence(
        name=name,
        grade=EssenceGrade.GRADE_9,
        color=EssenceColor.GREEN,
        essence_type=EssenceType.DPS_MELEE,
        origin=EssenceOrigin.MONSTER_DROP,
        monster_source="고블린",
    )


# ─── activate_light_source ───


def test_activate_torch_for_barbarian() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    result = activate_light_source(c, _torch())
    assert result.success
    assert c.light_state.active_source_name == "횃불"
    assert c.light_state.remaining_duration_hours == 72.0
    assert c.has_active_light()


def test_activate_spirit_lantern_human_blocked() -> None:
    c = Character(name="인간", race=Race.HUMAN)
    result = activate_light_source(c, _spirit_lantern())
    assert not result.success
    assert "요정" in result.message
    assert not c.has_active_light()


def test_activate_spirit_lantern_faerie_success() -> None:
    c = Character(name="에르웬", race=Race.FAERIE)
    result = activate_light_source(c, _spirit_lantern())
    assert result.success
    assert c.has_active_light()


def test_activate_flare_consumable_decrements() -> None:
    c = Character(name="X", race=Race.HUMAN)
    c.light_state = LightStateOnCharacter(consumables={"조명탄": 3})
    result = activate_light_source(c, _flare())
    assert result.success
    assert c.light_state.consumables["조명탄"] == 2


def test_activate_flare_no_stock_blocked() -> None:
    c = Character(name="X", race=Race.HUMAN)
    c.light_state = LightStateOnCharacter(consumables={"조명탄": 0})
    result = activate_light_source(c, _flare())
    assert not result.success


# ─── advance_time ───


def test_advance_time_torch_decrements() -> None:
    c = Character(name="X", race=Race.HUMAN)
    c.light_state = LightStateOnCharacter(
        active_source_name="횃불",
        remaining_duration_hours=72.0,
    )
    world = WorldState(hours_in_dungeon=0)
    result = advance_time([c], world, elapsed_hours=10.0)
    assert result.success
    assert c.light_state.remaining_duration_hours == 62.0
    assert world.hours_in_dungeon == 10


def test_advance_time_torch_burnout() -> None:
    c = Character(name="X", race=Race.HUMAN)
    c.light_state = LightStateOnCharacter(
        active_source_name="횃불",
        remaining_duration_hours=5.0,
    )
    world = WorldState()
    result = advance_time([c], world, elapsed_hours=10.0)
    assert result.success
    assert c.light_state.active_source_name is None
    assert c.light_state.remaining_duration_hours == 0.0
    assert not c.has_active_light()


def test_advance_time_spirit_burnout_triggers_cooldown() -> None:
    c = Character(name="에르웬", race=Race.FAERIE)
    c.light_state = LightStateOnCharacter(
        active_source_name="정령 등불",
        remaining_duration_hours=5.0,
    )
    world = WorldState()
    result = advance_time([c], world, elapsed_hours=6.0)
    assert result.success
    assert c.light_state.active_source_name is None
    assert c.light_state.cooldown_remaining_hours == 2.0


def test_advance_time_cooldown_recovers() -> None:
    c = Character(name="에르웬", race=Race.FAERIE)
    c.light_state = LightStateOnCharacter(cooldown_remaining_hours=2.0)
    world = WorldState()
    result = advance_time([c], world, elapsed_hours=2.0)
    assert result.success
    assert c.light_state.cooldown_remaining_hours == 0.0


def test_advance_time_dead_character_skipped() -> None:
    c = Character(name="X", race=Race.HUMAN)
    c.hp = 0
    c.light_state = LightStateOnCharacter(
        active_source_name="횃불",
        remaining_duration_hours=10.0,
    )
    world = WorldState()
    advance_time([c], world, elapsed_hours=5.0)
    assert c.light_state.remaining_duration_hours == 10.0


# ─── attempt_essence_absorb ───


def test_absorb_essence_can_reach_success() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    fe = FloatingEssence(
        essence=_essence(),
        spawned_at_hours=10,
        location_sub_area="북쪽 통로",
    )
    result = attempt_essence_absorb(
        c, fe, can_reach=True, current_hours=10, current_minutes=10
    )
    assert result.success
    assert c.essence_slots_used() == 1


def test_absorb_essence_no_reach_fails() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    fe = FloatingEssence(
        essence=_essence(),
        spawned_at_hours=10,
        location_sub_area="X",
    )
    result = attempt_essence_absorb(
        c, fe, can_reach=False, current_hours=10, current_minutes=10
    )
    assert not result.success
    assert c.essence_slots_used() == 0


def test_absorb_essence_decayed_fails() -> None:
    """30분 지나면 자연 소멸 — 흡수 X (★ 13/14화)."""
    c = Character(name="비요른", race=Race.BARBARIAN)
    fe = FloatingEssence(
        essence=_essence(),
        spawned_at_hours=10,
        location_sub_area="X",
    )
    result = attempt_essence_absorb(
        c, fe, can_reach=True, current_hours=10, current_minutes=30
    )
    assert not result.success
    assert "자연 소멸" in result.message


# ─── issue/resolve bounty ───


def test_issue_bounty_appended() -> None:
    world = WorldState()
    bounty = BountyEntry(
        target_name="에르웬",
        amount_stones=20000,
        issuer_name="간부",
        issuer_faction="수정 연합",
    )
    result = issue_bounty(world, bounty)
    assert result.success
    assert len(world.active_bounties) == 1


def test_resolve_bounty_removes_target() -> None:
    world = WorldState()
    world.active_bounties = [
        BountyEntry(target_name="에르웬", amount_stones=10000, issuer_name="X"),
        BountyEntry(target_name="비요른", amount_stones=5000, issuer_name="Y"),
    ]
    result = resolve_bounty(world, "에르웬")
    assert result.success
    assert len(world.active_bounties) == 1
    assert world.active_bounties[0].target_name == "비요른"


def test_resolve_bounty_no_match() -> None:
    world = WorldState()
    world.active_bounties = [
        BountyEntry(target_name="X", amount_stones=10000, issuer_name="Y"),
    ]
    result = resolve_bounty(world, "없는 이름")
    assert not result.success


# ─── apply_damage ───


def test_apply_damage_normal() -> None:
    c = Character(name="X", race=Race.HUMAN, hp=100, hp_max=100)
    result = apply_damage(c, 30)
    assert result.success
    assert c.hp == 70
    assert c.is_alive()


def test_apply_damage_lethal() -> None:
    """HP 0 → 영구사망."""
    c = Character(name="X", race=Race.HUMAN, hp=20, hp_max=100)
    result = apply_damage(c, 50)
    assert result.success
    assert c.hp == 0
    assert not c.is_alive()
    assert "영구사망" in result.message


def test_apply_damage_dead_character_blocked() -> None:
    c = Character(name="X", race=Race.HUMAN, hp=0)
    result = apply_damage(c, 10)
    assert not result.success
