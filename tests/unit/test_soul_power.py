"""Phase 8 MP — 22화 본문 정합 영혼력 +10 per level up mechanism unit 본격.

검증 본질 (★ docs/village_spec.md 본격 X — turn_handler_v2 mechanism):
- 22화 본문 quote: "캐릭터의 레벨이 상승했습니다. 영혼력이 +10 상승합니다"
- SOUL_POWER_GAIN_PER_LEVEL = 10
- _award_kill_exp level up → soul_power + soul_power_max += 10
- enter_next_floor 최초 진입 보너스 level up → 동일
- 종족별 시작값 보존 (★ 요정 60 / 바바리안 30 — init_from_plan)
- multi-level jump (★ 보스 800 exp = 1 → 4) = +30
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    SOUL_POWER_GAIN_PER_LEVEL,
    _award_kill_exp,
    enter_next_floor,
)

# ─── 1. SOUL_POWER_GAIN_PER_LEVEL 상수 ───


def test_gain_per_level_is_10_22hwa_canon() -> None:
    """22화 본문 직접 명시 '영혼력이 +10 상승합니다'."""
    assert SOUL_POWER_GAIN_PER_LEVEL == 10


# ─── 2. _award_kill_exp level up + soul_power ───


def _bjorn() -> Character:
    """바바리안 default (★ init_from_plan: soul_power=30, max=30).

    본 테스트 본격 Character() default (0) 사용 — mechanism 검증 본격
    종족별 시작값 보존 검증은 별도 test 본격.
    """
    return Character(name="비요른", race=Race.BARBARIAN)


def test_kill_level_up_grants_soul_power() -> None:
    """8등급 = 100 exp = level 2 → soul_power + max +10."""
    actor = _bjorn()
    world = WorldState()
    exp, lvled = _award_kill_exp(actor, "거대 슬라임", 8, world)
    assert lvled is True
    assert actor.level == 2
    assert actor.soul_power == SOUL_POWER_GAIN_PER_LEVEL == 10
    assert actor.soul_power_max == SOUL_POWER_GAIN_PER_LEVEL == 10


def test_no_level_up_no_soul_power_change() -> None:
    """9등급 = 50 exp = level 1 유지 → soul_power 변화 X."""
    actor = _bjorn()
    world = WorldState()
    pre_sp = actor.soul_power
    pre_max = actor.soul_power_max
    _, lvled = _award_kill_exp(actor, "고블린", 9, world)
    assert lvled is False
    assert actor.soul_power == pre_sp
    assert actor.soul_power_max == pre_max


def test_multi_level_jump_grants_proportional() -> None:
    """5등급 보스 = 800 exp = level 1 → 4 (★ +3 levels = +30 영혼력)."""
    actor = _bjorn()
    world = WorldState()
    exp, lvled = _award_kill_exp(actor, "bloody_castle_variant", 5, world)
    assert lvled is True
    assert actor.level == 4
    # 3 levels gained = 30 soul_power
    assert actor.soul_power == SOUL_POWER_GAIN_PER_LEVEL * 3 == 30
    assert actor.soul_power_max == 30


def test_starting_soul_power_preserved_on_level_up() -> None:
    """종족별 시작값 + level up gain 본격 누적 (★ 요정 60 + 10 = 70)."""
    fairy = Character(
        name="에르웬",
        race=Race.FAERIE,
        soul_power=60,
        soul_power_max=60,
    )
    world = WorldState()
    _award_kill_exp(fairy, "거대 슬라임", 8, world)
    assert fairy.level == 2
    assert fairy.soul_power == 60 + 10 == 70
    assert fairy.soul_power_max == 60 + 10 == 70


def test_side_effect_marker_soul_power_gain() -> None:
    """execute_attack 본격 side_effect marker 본격 'soul_power_gain=name:+N'."""
    from service.game.turn_handler_v2 import execute_attack

    actor = Character(
        name="투르윈",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        physical=15,
        strength=20,
        bone_strength=10,
        is_player=True,
    )
    world = WorldState()
    # 첫 처치: 9등급 50 exp → level 1 유지, marker X
    r1 = execute_attack(actor, "고블린", [actor], world)
    assert r1.success is True
    assert not any("soul_power_gain=" in e for e in r1.side_effects)
    # 두 번째 처치 (다른 종): 50 + 50 = 100 exp → level 2, marker O
    r2 = execute_attack(actor, "노움", [actor], world)
    assert r2.success is True
    assert any("level_up=투르윈:2" == e for e in r2.side_effects)
    assert any(
        f"soul_power_gain=투르윈:+{SOUL_POWER_GAIN_PER_LEVEL}" == e
        for e in r2.side_effects
    )


# ─── 3. enter_next_floor 최초 진입 보너스 level up ───


def test_enter_next_floor_first_party_grants_soul_power() -> None:
    """진입 보너스 +500 exp → level 4 → soul_power + max +30."""
    party = [
        Character(
            name="투르윈",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            soul_power=30,
            soul_power_max=30,
            is_player=True,
        ),
    ]
    world = WorldState()
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="동쪽 포탈 통로")
    result = enter_next_floor(party, world, loc)
    assert result.success is True
    member = party[0]
    assert member.level == 4
    assert member.soul_power == 30 + 30 == 60  # +3 levels
    assert member.soul_power_max == 30 + 30 == 60
    # side_effect marker
    assert any(
        "soul_power_gain=투르윈:+30" == e for e in result.side_effects
    )


def test_enter_next_floor_no_bonus_no_soul_power_change() -> None:
    """두 번째 진입 (★ first_entry_parties 본격 본격) — 보너스 X → soul_power X."""
    party = [
        Character(
            name="투르윈",
            race=Race.BARBARIAN,
            hp=150,
            hp_max=150,
            soul_power=30,
            soul_power_max=30,
            is_player=True,
        ),
    ]
    world = WorldState()
    world.first_entry_parties.add(2)  # ★ 이미 진입한 적 있음
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="동쪽 포탈 통로")
    result = enter_next_floor(party, world, loc)
    assert result.success is True
    member = party[0]
    # 보너스 X → level 1 + soul_power 30 그대로
    assert member.level == 1
    assert member.soul_power == 30
    assert member.soul_power_max == 30
