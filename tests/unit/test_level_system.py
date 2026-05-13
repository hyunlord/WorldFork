"""Phase 8 B — 레벨 + 경험치 시스템 unit 본격.

검증 본질:
- LEVEL_EXP_THRESHOLDS monotonic + LEVEL_TO_ESSENCE_SLOT_MAX monotonic
- level_for_exp / slot_max_for_level / next_level_threshold
- Character.essence_slot_max() 본격 level driven (★ 7e finding level 1=5 정합)
- _award_kill_exp:
  * first kill → base exp + species 등록
  * second kill → 0 exp ("딱 한번")
  * different species → exp 누적
  * level up → actor.level + essence_slot_max 본격
  * 보스 (★ variant boss_id) species 별도
"""

from __future__ import annotations

from service.game.state_v2 import (
    LEVEL_EXP_THRESHOLDS,
    LEVEL_TO_ESSENCE_SLOT_MAX,
    Character,
    Race,
    WorldState,
    level_for_exp,
    next_level_threshold,
    slot_max_for_level,
)
from service.game.turn_handler_v2 import (
    MONSTER_EXP_BY_GRADE,
    _award_kill_exp,
)


# ─── 1. Threshold / slot table ───


def test_exp_thresholds_monotonic() -> None:
    for i in range(len(LEVEL_EXP_THRESHOLDS) - 1):
        assert LEVEL_EXP_THRESHOLDS[i] < LEVEL_EXP_THRESHOLDS[i + 1]


def test_slot_table_monotonic_non_decreasing() -> None:
    keys = sorted(LEVEL_TO_ESSENCE_SLOT_MAX.keys())
    for i in range(len(keys) - 1):
        assert (
            LEVEL_TO_ESSENCE_SLOT_MAX[keys[i]]
            <= LEVEL_TO_ESSENCE_SLOT_MAX[keys[i + 1]]
        )


def test_level_1_slot_5_matches_7e_finding() -> None:
    """7e finding: essence_slot_max(level=1) == 5 (★ 본문 1차 자료)."""
    assert slot_max_for_level(1) == 5


def test_slot_max_caps_at_top_level() -> None:
    top = max(LEVEL_TO_ESSENCE_SLOT_MAX.keys())
    assert slot_max_for_level(top + 5) == LEVEL_TO_ESSENCE_SLOT_MAX[top]


def test_slot_max_clamps_below_1() -> None:
    """level 0 / 음수 → level 1 slot (★ 방어)."""
    assert slot_max_for_level(0) == LEVEL_TO_ESSENCE_SLOT_MAX[1]
    assert slot_max_for_level(-5) == LEVEL_TO_ESSENCE_SLOT_MAX[1]


# ─── 2. level_for_exp ───


def test_level_for_exp_zero_is_1() -> None:
    assert level_for_exp(0) == 1


def test_level_for_exp_at_each_threshold() -> None:
    for i, thr in enumerate(LEVEL_EXP_THRESHOLDS):
        assert level_for_exp(thr) == i + 1


def test_level_for_exp_just_below_threshold() -> None:
    assert level_for_exp(99) == 1  # 100 = level 2
    assert level_for_exp(249) == 2  # 250 = level 3


def test_level_for_exp_caps_at_max_level() -> None:
    assert level_for_exp(99_999_999) == len(LEVEL_EXP_THRESHOLDS)


# ─── 3. next_level_threshold ───


def test_next_threshold_at_level_1() -> None:
    assert next_level_threshold(1) == LEVEL_EXP_THRESHOLDS[1]


def test_next_threshold_at_max_returns_self() -> None:
    max_lv = len(LEVEL_EXP_THRESHOLDS)
    assert next_level_threshold(max_lv) == LEVEL_EXP_THRESHOLDS[-1]


# ─── 4. Character.essence_slot_max() level driven ───


def test_character_slot_max_level_1_returns_5() -> None:
    c = Character(name="투르윈", race=Race.HUMAN)
    assert c.level == 1
    assert c.essence_slot_max() == 5


def test_character_slot_max_grows_with_level() -> None:
    c = Character(name="투르윈", race=Race.HUMAN, level=5)
    assert c.essence_slot_max() == LEVEL_TO_ESSENCE_SLOT_MAX[5]


# ─── 5. _award_kill_exp ───


def _actor() -> Character:
    return Character(name="투르윈", race=Race.BARBARIAN)


def test_first_kill_grants_base_exp() -> None:
    actor = _actor()
    world = WorldState()
    exp, leveled = _award_kill_exp(actor, "고블린", 9, world)
    assert exp == MONSTER_EXP_BY_GRADE[9] == 50
    assert leveled is False
    assert actor.experience == 50
    assert actor.level == 1
    assert "고블린" in world.first_killed_species


def test_second_kill_same_species_zero() -> None:
    """'딱 한번' mechanism — 같은 species 두 번째 0 exp."""
    actor = _actor()
    world = WorldState()
    _award_kill_exp(actor, "고블린", 9, world)
    exp, leveled = _award_kill_exp(actor, "고블린", 9, world)
    assert exp == 0
    assert leveled is False
    assert actor.experience == 50  # 첫 보상만 유지


def test_different_species_each_grants() -> None:
    actor = _actor()
    world = WorldState()
    _award_kill_exp(actor, "고블린", 9, world)
    exp, _ = _award_kill_exp(actor, "노움", 9, world)
    assert exp == 50
    assert actor.experience == 100
    assert {"고블린", "노움"} <= world.first_killed_species


def test_level_up_on_threshold_8grade() -> None:
    """8등급 first kill = 100 exp → level 1 → 2."""
    actor = _actor()
    world = WorldState()
    exp, leveled = _award_kill_exp(actor, "거대 슬라임", 8, world)
    assert exp == 100
    assert leveled is True
    assert actor.level == 2
    # slot_max 본격 자동 증가 (★ level 본격)
    assert actor.essence_slot_max() == LEVEL_TO_ESSENCE_SLOT_MAX[2]


def test_no_level_up_below_threshold_9grade() -> None:
    """9등급 1회 = 50 exp → level 1 유지."""
    actor = _actor()
    world = WorldState()
    _award_kill_exp(actor, "고블린", 9, world)
    assert actor.level == 1
    assert actor.essence_slot_max() == 5


def test_boss_high_grade_jumps_levels() -> None:
    """5등급 변종 보스 1회 = 800 exp → level 1 → 4 (★ 본격 jump)."""
    actor = _actor()
    world = WorldState()
    exp, leveled = _award_kill_exp(actor, "bloody_castle_variant", 5, world)
    assert exp == MONSTER_EXP_BY_GRADE[5] == 800
    assert leveled is True
    assert actor.level == 4  # threshold 500 → 1000 사이


def test_boss_variant_vs_normal_separate_species() -> None:
    """variant / normal boss는 다른 species id (★ boss_id 본격 variant-aware)."""
    actor = _actor()
    world = WorldState()
    exp1, _ = _award_kill_exp(actor, "bloody_castle_variant", 5, world)
    exp2, _ = _award_kill_exp(actor, "bloody_castle_normal", 6, world)
    assert exp1 == 800
    assert exp2 == 400
    assert actor.experience == 1200


def test_layer_lord_grade_0_max_exp() -> None:
    """0등급 (계층군주) = 25600 exp → level 9."""
    actor = _actor()
    world = WorldState()
    exp, leveled = _award_kill_exp(actor, "어떤_계층군주", 0, world)
    assert exp == 25600
    assert leveled is True
    assert actor.level == 9


# ─── 6. WorldState first_killed_species 본격 default ───


def test_world_state_default_first_killed_empty() -> None:
    world = WorldState()
    assert world.first_killed_species == set()
