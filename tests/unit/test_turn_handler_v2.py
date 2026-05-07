"""turn_handler_v2.advance_time — 시간 흐름 진짜 mutate 검증.

본 commit 본질:
- Character.light_state 차감 / 정령 cooldown 진입 + 회복
- 사망자 skip
- WorldState.hours_in_dungeon 누적
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    LightStateOnCharacter,
    Race,
    WorldState,
)
from service.game.turn_handler_v2 import advance_time


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
    """정령 소진 → cooldown 2시간 (★ 11화)."""
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
