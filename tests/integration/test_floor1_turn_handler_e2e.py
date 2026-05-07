"""1층 5턴 시나리오 — turn_handler_v2 진짜 mutate 통합 (★ Tier 2 D12).

직전 Stage 7 backout 본질 진짜 해소:
- ctx 노출만 X → 진짜 production code (turn_handler_v2)에서 schema mutate
"""

from __future__ import annotations

from service.game.floors.floor1_light import FLOOR1_LIGHT_SOURCES
from service.game.state_v2 import (
    BountyEntry,
    Character,
    Essence,
    EssenceColor,
    EssenceGrade,
    EssenceOrigin,
    EssenceType,
    FloatingEssence,
    Race,
    WorldState,
)
from service.game.turn_handler_v2 import (
    activate_light_source,
    advance_time,
    apply_damage,
    attempt_essence_absorb,
    issue_bounty,
)


def test_e2e_5turn_floor1_with_mutations() -> None:
    """1층 5턴 — schema 진짜 mutate end-to-end."""
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

    # 턴 1: 진입 (어둠) — 빛 X 검증
    assert not bjorn.has_active_light()
    assert not erwen.has_active_light()

    # 턴 2: 횃불 활성
    torch = next(ls for ls in FLOOR1_LIGHT_SOURCES if ls.name == "횃불")
    r = activate_light_source(bjorn, torch)
    assert r.success
    assert bjorn.has_active_light()

    # 턴 3: 시간 6h 흐름 → 횃불 66h 남음
    r = advance_time(party, world, elapsed_hours=6.0)
    assert r.success
    assert bjorn.light_state.remaining_duration_hours == 66.0
    assert world.hours_in_dungeon == 6

    # 턴 4: 정수 흡수 (★ 살이 닿음, 30분 안)
    fe = FloatingEssence(
        essence=Essence(
            name="고블린 정수",
            grade=EssenceGrade.GRADE_9,
            color=EssenceColor.GREEN,
            essence_type=EssenceType.DPS_MELEE,
            origin=EssenceOrigin.MONSTER_DROP,
            monster_source="고블린",
        ),
        spawned_at_hours=world.hours_in_dungeon,
        location_sub_area="북쪽 통로",
    )
    r = attempt_essence_absorb(
        bjorn,
        fe,
        can_reach=True,
        current_hours=world.hours_in_dungeon,
        current_minutes=5,
    )
    assert r.success
    assert bjorn.essence_slots_used() == 1

    # 턴 5: 현상금 발령 + HP 손상
    issue_bounty(
        world,
        BountyEntry(
            target_name="에르웬",
            amount_stones=20000,
            issuer_name="수정 연합 간부",
            issuer_faction="수정 연합",
        ),
    )
    assert len(world.active_bounties) == 1

    r = apply_damage(bjorn, 100)
    assert r.success
    assert bjorn.hp == 50
    assert bjorn.is_alive()

    # 마무리 — 모든 schema 진짜 mutate
    assert bjorn.light_state.active_source_name == "횃불"
    assert bjorn.essence_slots_used() == 1
    assert world.hours_in_dungeon == 6
    assert len(world.active_bounties) == 1
    assert bjorn.hp == 50


def test_e2e_player_permadeath_stops_game() -> None:
    """주인공 영구사망 본질 (★ 작품 본질 — 시신은 사물)."""
    bjorn = Character(
        name="비요른", race=Race.BARBARIAN, hp=10, is_player=True
    )

    r = apply_damage(bjorn, 50)
    assert r.success
    assert not bjorn.is_alive()
    assert "영구사망" in r.message

    r2 = apply_damage(bjorn, 10)
    assert not r2.success
