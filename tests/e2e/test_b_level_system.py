"""Phase 8 B E2E — 레벨 + 경험치 시스템 scripted trace.

검증 본질 (★ LLM 무관 결정적):
- ATTACK 처치 → first kill 시 exp drop + 본격 side_effect marker
- 같은 species 두 번째 사냥 → exp 0 ("딱 한번")
- exp 누적 → level up + essence_slot_max 본격 증가
- 보스 처치 본격 exp drop (★ A3 _defeat_boss 본격)
"""

from __future__ import annotations

from service.game.state_v2 import (
    LEVEL_TO_ESSENCE_SLOT_MAX,
    BossEncounter,
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    MONSTER_EXP_BY_GRADE,
    execute_attack,
)


def _strong_attacker(level: int = 1) -> Character:
    """attacker_dmg >= 30 본격 — 9등급 처치 가능 본격 stat."""
    return Character(
        name="투르윈",
        race=Race.BARBARIAN,
        level=level,
        hp=150,
        hp_max=150,
        physical=15,
        strength=20,
        bone_strength=10,
        is_player=True,
    )


def _loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


# ─── 1. 정상 monster first kill → exp ───


def test_scripted_first_kill_grants_exp_and_marker() -> None:
    """ATTACK 본격 9등급 첫 처치 → 50 exp + side_effect markers."""
    actor = _strong_attacker()
    world = WorldState()

    result = execute_attack(actor, "고블린", [actor], world)

    assert result.success is True
    assert actor.experience == MONSTER_EXP_BY_GRADE[9] == 50
    assert "고블린" in world.first_killed_species
    # side_effects 본격 exp marker
    assert any(
        "exp_gained=투르윈:50" == e for e in result.side_effects
    ), result.side_effects
    # 9등급 1회 = 50 < 100 → level up X
    assert actor.level == 1
    assert not any("level_up=" in e for e in result.side_effects)


def test_scripted_second_kill_same_species_zero() -> None:
    """같은 species 두 번째 사냥 → exp 0 marker X ('딱 한번')."""
    actor = _strong_attacker()
    world = WorldState()

    execute_attack(actor, "고블린", [actor], world)
    assert actor.experience == 50

    result = execute_attack(actor, "고블린", [actor], world)

    assert result.success is True
    assert actor.experience == 50  # 본격 변화 X
    assert not any("exp_gained=" in e for e in result.side_effects)


def test_scripted_different_species_each_grants() -> None:
    """노움 + 슬라임 + 고블린 — 3종 first kill 본격 / level up 본격 정합.

    threshold table 본격 정합:
    - kill 1 (고블린 9등급, 50 exp): 0 → 50, level 1 유지
    - kill 2 (노움 9등급, 50 exp): 50 → 100, level 1 → 2 (★ threshold 100 hit)
    - kill 3 (슬라임 9등급, 50 exp): 100 → 150, level 2 유지
    """
    actor = _strong_attacker()
    world = WorldState()

    r1 = execute_attack(actor, "고블린", [actor], world)
    r2 = execute_attack(actor, "노움", [actor], world)
    r3 = execute_attack(actor, "슬라임", [actor], world)

    assert actor.experience == 150
    assert world.first_killed_species >= {"고블린", "노움", "슬라임"}
    assert actor.level == 2

    # kill 1 = level up X
    assert not any("level_up=" in e for e in r1.side_effects), r1.side_effects
    # kill 2 = level up 본격 (★ 50 → 100 = threshold)
    assert any(
        "level_up=투르윈:2" == e for e in r2.side_effects
    ), r2.side_effects
    # kill 3 = 이미 level 2 → 추가 level up X
    assert not any("level_up=" in e for e in r3.side_effects), r3.side_effects


def test_scripted_level_up_slot_max_increases() -> None:
    """level 1 → 2 시 essence_slot_max 5 → 6."""
    actor = _strong_attacker()
    world = WorldState()
    assert actor.essence_slot_max() == 5

    execute_attack(actor, "고블린", [actor], world)
    execute_attack(actor, "노움", [actor], world)
    assert actor.level == 2
    assert actor.essence_slot_max() == LEVEL_TO_ESSENCE_SLOT_MAX[2] == 6


# ─── 2. 보스 처치 본격 exp (★ A3 _defeat_boss 본격) ───


def test_scripted_boss_kill_grants_exp() -> None:
    """5등급 변종 보스 1회 처치 → 800 exp + level 4."""
    actor = _strong_attacker()
    actor.physical = 100
    actor.strength = 600  # 본격 1타 처치 본격
    world = WorldState(
        active_boss_encounter=BossEncounter(
            rift_id="bloody_castle",
            boss_id="bloody_castle_variant",
            boss_name="캄브로미르",
            boss_grade=5,
            is_variant=True,
            hp=600,
            hp_max=600,
        )
    )

    result = execute_attack(actor, "캄브로미르", [actor], world)

    assert result.success is True
    assert actor.experience == MONSTER_EXP_BY_GRADE[5] == 800
    assert actor.level == 4  # threshold 500
    assert "bloody_castle_variant" in world.first_killed_species
    assert any("exp_gained=투르윈:800" == e for e in result.side_effects)
    assert any("level_up=투르윈:4" == e for e in result.side_effects)


def test_scripted_boss_variant_vs_normal_separate() -> None:
    """variant / normal boss는 별도 species — 각각 exp 본격."""
    actor = _strong_attacker()
    actor.physical = 100
    actor.strength = 600

    # 1차: variant 5등급
    world = WorldState(
        active_boss_encounter=BossEncounter(
            rift_id="bloody_castle",
            boss_id="bloody_castle_variant",
            boss_name="캄브로미르",
            boss_grade=5,
            is_variant=True,
            hp=600,
            hp_max=600,
        )
    )
    execute_attack(actor, "캄브로미르", [actor], world)
    assert actor.experience == 800

    # 2차: normal 6등급 (같은 rift 본격 different boss_id)
    world.active_boss_encounter = BossEncounter(
        rift_id="bloody_castle",
        boss_id="bloody_castle_normal",
        boss_name="블라테르",
        boss_grade=6,
        is_variant=False,
        hp=400,
        hp_max=400,
    )
    execute_attack(actor, "블라테르", [actor], world)
    assert actor.experience == 800 + MONSTER_EXP_BY_GRADE[6]
    assert {"bloody_castle_variant", "bloody_castle_normal"} <= (
        world.first_killed_species
    )
