"""advance_time 진짜 production mutate 통합 (★ Tier 2 D12).

직전 Stage 7 backout 본질 진짜 해소:
- ctx 노출만 X → game_routes.process_turn에서 진짜 mutate
- advance_time이 v2 schema (Character.light_state + WorldState.hours_in_dungeon)
  진짜 변경
"""

from __future__ import annotations

from service.game.floors.floor1_light import FLOOR1_LIGHT_SOURCES
from service.game.state_v2 import (
    Character,
    LightStateOnCharacter,
    Race,
    WorldState,
)
from service.game.turn_handler_v2 import advance_time


def test_e2e_multi_turn_advance_mutates_v2_state() -> None:
    """5턴 시간 진행 — schema 진짜 mutate 누적."""
    bjorn = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        is_player=True,
    )
    erwen = Character(
        name="에르웬",
        race=Race.FAERIE,
        hp=90,
        hp_max=90,
    )
    party = [bjorn, erwen]
    world = WorldState(
        current_round=1,
        hours_in_dungeon=0,
        is_dark_zone=True,
        party_members=["비요른", "에르웬"],
    )

    # 횃불 활성 상태로 시작 (★ FLOOR1_LIGHT_SOURCES 진짜 import)
    torch = next(ls for ls in FLOOR1_LIGHT_SOURCES if ls.name == "횃불")
    bjorn.light_state = LightStateOnCharacter(
        active_source_name=torch.name,
        remaining_duration_hours=torch.duration_hours or 0.0,
    )

    # 5턴 진행 — 매 턴 1시간
    for _ in range(5):
        advance_time(party, world, elapsed_hours=1.0)

    assert world.hours_in_dungeon == 5
    assert bjorn.light_state.remaining_duration_hours == 67.0  # 72 - 5
    assert bjorn.has_active_light()  # 아직 활성


def test_e2e_dead_character_skipped_during_advance() -> None:
    """주인공 사망 (HP 0) 후 advance_time이 사망자 처리 X."""
    bjorn = Character(name="비요른", race=Race.BARBARIAN, is_player=True)
    bjorn.hp = 0
    bjorn.light_state = LightStateOnCharacter(
        active_source_name="횃불",
        remaining_duration_hours=10.0,
    )
    world = WorldState()

    advance_time([bjorn], world, elapsed_hours=5.0)

    # 사망자 mutate X
    assert bjorn.light_state.remaining_duration_hours == 10.0
    # 시간만 누적
    assert world.hours_in_dungeon == 5
