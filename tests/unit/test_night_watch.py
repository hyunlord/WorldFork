"""Phase 9.17-e — 불침번 + 분쟁 mutual defense (★ 6/7/10/27/111화 정합).

본 commit (★ B minimal):
- PlayerActionType.REST_AND_NIGHT_WATCH (★ 28 → 29)
- _recovery_pct_for_party_size (★ 1인 0 / 2인 80% / 3+ 100%)
- execute_rest_and_night_watch:
  * 던전 한정
  * 인원 수별 회복
  * effective_hp_max cap (★ 9.10 disability 정합)
  * trigger_encounter_after_rest side_effect
- ENGAGE_BANDIT mutual defense wire:
  * alive_members 합산 attack pool
  * 패배 시 damage 분담
  * mutual_defense side_effect
"""

from __future__ import annotations

import random

from service.game.state_v2 import (
    Character,
    Disability,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    BANDIT_FAME_GAIN_WIN,
    NIGHT_WATCH_HOURS,
    NIGHT_WATCH_RECOVERY_PCT_SOLO,
    NIGHT_WATCH_RECOVERY_PCT_THREE_PLUS,
    NIGHT_WATCH_RECOVERY_PCT_TWO,
    _recovery_pct_for_party_size,
    execute_engage_bandit,
    execute_rest_and_night_watch,
)
from service.sim.types import (
    ACTION_HOURS_DELTA,
    Encounter,
    EncounterType,
    PlayerActionType,
)

# ─── _recovery_pct_for_party_size ───


class TestRecoveryPctForPartySize:
    def test_zero_count(self) -> None:
        """alive=0 본격 본격 solo 본격 처리 (★ guard)."""
        assert _recovery_pct_for_party_size(0) == NIGHT_WATCH_RECOVERY_PCT_SOLO

    def test_solo_zero(self) -> None:
        assert _recovery_pct_for_party_size(1) == NIGHT_WATCH_RECOVERY_PCT_SOLO
        assert _recovery_pct_for_party_size(1) == 0.0

    def test_two_eighty(self) -> None:
        assert _recovery_pct_for_party_size(2) == NIGHT_WATCH_RECOVERY_PCT_TWO
        assert _recovery_pct_for_party_size(2) == 0.8

    def test_three_full(self) -> None:
        assert (
            _recovery_pct_for_party_size(3)
            == NIGHT_WATCH_RECOVERY_PCT_THREE_PLUS
        )

    def test_five_full(self) -> None:
        assert _recovery_pct_for_party_size(5) == 1.0


# ─── PlayerActionType + ACTION_HOURS_DELTA ───


class TestPlayerActionTypeRest:
    def test_rest_value(self) -> None:
        assert (
            PlayerActionType.REST_AND_NIGHT_WATCH.value
            == "rest_and_night_watch"
        )

    def test_total_count_29(self) -> None:
        assert len(list(PlayerActionType)) == 34

    def test_action_hours_delta(self) -> None:
        assert (
            ACTION_HOURS_DELTA[PlayerActionType.REST_AND_NIGHT_WATCH]
            == NIGHT_WATCH_HOURS
        )
        assert NIGHT_WATCH_HOURS == 6.0


# ─── execute_rest_and_night_watch ───


def _dungeon_loc() -> Location:
    return Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="floor1_corridor",
    )


def _bjorn(hp: int = 50, hp_max: int = 100) -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=hp,
        hp_max=hp_max,
    )


def _hans(hp: int = 30, hp_max: int = 100) -> Character:
    return Character(
        name="한스",
        race=Race.HUMAN,
        hp=hp,
        hp_max=hp_max,
    )


class TestExecuteRest:
    def test_outside_dungeon_fails(self) -> None:
        loc = Location(realm=Realm.CITY, sub_area="district_7_plaza")
        bjorn = _bjorn()
        result = execute_rest_and_night_watch(
            "비요른", "", [bjorn], loc, [], WorldState()
        )
        assert result.success is False
        assert "던전" in result.message

    def test_solo_no_recovery(self) -> None:
        """1인 본격 회복 0 (★ 6/7화 본문 정합)."""
        loc = _dungeon_loc()
        bjorn = _bjorn(hp=50)
        result = execute_rest_and_night_watch(
            "비요른", "", [bjorn], loc, [], WorldState()
        )
        assert result.success is True
        assert bjorn.hp == 50
        assert "1인" in result.message

    def test_two_person_80pct(self) -> None:
        """2인 본격 80% 회복 (★ 111화 인원 효율)."""
        loc = _dungeon_loc()
        bjorn = _bjorn(hp=50)
        hans = _hans(hp=30)
        result = execute_rest_and_night_watch(
            "비요른", "", [bjorn, hans], loc, [], WorldState()
        )
        assert result.success is True
        assert bjorn.hp == 80
        assert hans.hp == 80

    def test_three_plus_100pct(self) -> None:
        """3인+ 본격 100% 회복."""
        loc = _dungeon_loc()
        members = [
            Character(
                name=f"M{i}", race=Race.HUMAN, hp=50, hp_max=100
            )
            for i in range(3)
        ]
        result = execute_rest_and_night_watch(
            "M0", "", members, loc, [], WorldState()
        )
        assert result.success is True
        for m in members:
            assert m.hp == 100

    def test_does_not_decrease_hp(self) -> None:
        """이미 회복 목표 이상 본격 hp 변화 X (★ max() 본격)."""
        loc = _dungeon_loc()
        bjorn = _bjorn(hp=90)
        hans = _hans(hp=85)
        execute_rest_and_night_watch(
            "비요른", "", [bjorn, hans], loc, [], WorldState()
        )
        # 80% = 80, 본격 90/85 본격 본격 변화 X
        assert bjorn.hp == 90
        assert hans.hp == 85

    def test_no_alive_fails(self) -> None:
        loc = _dungeon_loc()
        dead = Character(name="비요른", race=Race.BARBARIAN, hp=0, hp_max=100)
        result = execute_rest_and_night_watch(
            "비요른", "", [dead], loc, [], WorldState()
        )
        assert result.success is False

    def test_effective_hp_max_cap_with_disability(self) -> None:
        """disability penalty 본격 effective_hp_max cap (★ 9.10 정합)."""
        loc = _dungeon_loc()
        bjorn = _bjorn(hp=50)
        bjorn.disabilities.append(
            Disability(
                body_part="arm", kind="amputation", hp_max_penalty=30
            )
        )
        # effective_hp_max = 100 - 30 = 70
        hans = _hans(hp=50)
        execute_rest_and_night_watch(
            "비요른", "", [bjorn, hans], loc, [], WorldState()
        )
        # 80% × 100 = 80, but effective_hp_max = 70 → cap at 70
        assert bjorn.hp == 70
        assert hans.hp == 80

    def test_dead_excluded_from_alive_count(self) -> None:
        """죽은 멤버 본격 alive 본격 미포함 (★ 1인 본격 회복 0 본격)."""
        loc = _dungeon_loc()
        bjorn = _bjorn(hp=50)
        dead = Character(
            name="한스", race=Race.HUMAN, hp=0, hp_max=100
        )
        execute_rest_and_night_watch(
            "비요른", "", [bjorn, dead], loc, [], WorldState()
        )
        # alive_count = 1 → recovery 0
        assert bjorn.hp == 50

    def test_action_type_in_result(self) -> None:
        loc = _dungeon_loc()
        result = execute_rest_and_night_watch(
            "비요른", "", [_bjorn()], loc, [], WorldState()
        )
        assert result.action_type == "rest_and_night_watch"

    def test_hp_recovered_side_effects(self) -> None:
        """회복 본격 hp_recovered side_effect."""
        loc = _dungeon_loc()
        bjorn = _bjorn(hp=50)
        hans = _hans(hp=30)
        result = execute_rest_and_night_watch(
            "비요른", "", [bjorn, hans], loc, [], WorldState()
        )
        assert any(
            "hp_recovered=비요른" in eff for eff in result.side_effects
        )
        assert any(
            "hp_recovered=한스" in eff for eff in result.side_effects
        )

    def test_solo_no_hp_recovered_side_effect(self) -> None:
        loc = _dungeon_loc()
        bjorn = _bjorn(hp=50)
        result = execute_rest_and_night_watch(
            "비요른", "", [bjorn], loc, [], WorldState()
        )
        assert not any(
            "hp_recovered" in eff for eff in result.side_effects
        )


# ─── encounter trigger marker ───


class TestEncounterTrigger:
    def test_trigger_marker_probability(self) -> None:
        """20% ± margin 본격 trigger marker 발생."""
        loc = _dungeon_loc()
        triggered = 0
        for seed in range(200):
            bjorn = _bjorn(hp=50)
            rng = random.Random(seed)
            result = execute_rest_and_night_watch(
                "비요른", "", [bjorn], loc, [], WorldState(), rng=rng
            )
            if any(
                "trigger_encounter_after_rest" in eff
                for eff in result.side_effects
            ):
                triggered += 1
        # 20% ± 10% (★ binomial 200 trials σ ≈ 5.6)
        assert 20 <= triggered <= 60

    def test_trigger_seed_deterministic_yes(self) -> None:
        """rng < 0.20 본격 trigger 발생 (★ seed 본격 deterministic)."""
        loc = _dungeon_loc()
        # seed 1 본격 첫 호출 random() ≈ 0.134 → trigger
        bjorn = _bjorn()
        rng = random.Random(1)
        result = execute_rest_and_night_watch(
            "비요른", "", [bjorn], loc, [], WorldState(), rng=rng
        )
        assert any(
            "trigger_encounter_after_rest" in eff
            for eff in result.side_effects
        )

    def test_trigger_seed_deterministic_no(self) -> None:
        """rng >= 0.20 본격 trigger X."""
        loc = _dungeon_loc()
        # seed 0 본격 첫 호출 random() ≈ 0.844 → no trigger
        bjorn = _bjorn()
        rng = random.Random(0)
        result = execute_rest_and_night_watch(
            "비요른", "", [bjorn], loc, [], WorldState(), rng=rng
        )
        assert not any(
            "trigger_encounter_after_rest" in eff
            for eff in result.side_effects
        )


# ─── ENGAGE_BANDIT mutual defense ───


def _hostile_encounter(name: str = "bandit_enc_1") -> Encounter:
    return Encounter(
        type=EncounterType.NPC_HOSTILE,
        name=name,
        location="floor1_corridor",
        description="약탈자 무리의 기척.",
    )


class TestMutualDefenseInBandit:
    def test_two_member_attack_pool_increases_chance(self) -> None:
        """2인 attack pool 본격 단일 attack 본격 본격 ↑ (★ 100 vs 50)."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        # grade 3 본격 attack 50 (★ 단일) / 100 (★ 2인)
        # solo bandit hp 30 본격 50/100 본격 본격 보장 승리
        # 4인조 bandit hp 120 본격 50 본격 패배 / 100 본격 패배
        # 100 vs 120 = -20 → 패배
        # 50 vs 120 = -70 → 더 큰 패배
        # 결과: 2인 본격 단일 본격 본격 본격 승리 횟수 ↑
        c1 = Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=100,
            hp_max=100,
            grade=3,
        )
        c2 = Character(
            name="한스", race=Race.HUMAN, hp=100, hp_max=100, grade=3
        )

        # 다수 seed 본격 비교 — 2인 본격 승률 ↑
        two_wins = 0
        solo_wins = 0
        for seed in range(50):
            c1.hp, c2.hp = 100, 100
            c1.fame, c1.injuries = 0, []
            c2.injuries = []
            rng = random.Random(seed)
            result_two = execute_engage_bandit(
                "비요른",
                enc.name,
                [c1, c2],
                loc,
                [enc],
                WorldState(),
                rng=rng,
            )
            if result_two.success:
                two_wins += 1

            c1.hp = 100
            c1.fame, c1.injuries = 0, []
            rng_solo = random.Random(seed)
            result_solo = execute_engage_bandit(
                "비요른",
                enc.name,
                [c1],
                loc,
                [enc],
                WorldState(),
                rng=rng_solo,
            )
            if result_solo.success:
                solo_wins += 1

        # 2인 본격 단일 본격 본격 승률 ↑ (★ mutual defense 본격 정합)
        assert two_wins >= solo_wins

    def test_mutual_defense_side_effect_2(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        c1 = Character(name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, grade=5)
        c2 = Character(name="한스", race=Race.HUMAN, hp=100, hp_max=100, grade=5)
        rng = random.Random(0)
        result = execute_engage_bandit(
            "비요른", enc.name, [c1, c2], loc, [enc], WorldState(), rng=rng
        )
        assert any("mutual_defense=2" in se for se in result.side_effects)

    def test_mutual_defense_side_effect_1_for_solo(self) -> None:
        """단일 actor 본격 mutual_defense=1 (★ 9.17-d 본격 본격 호환)."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        c1 = Character(name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, grade=5)
        rng = random.Random(0)
        result = execute_engage_bandit(
            "비요른", enc.name, [c1], loc, [enc], WorldState(), rng=rng
        )
        assert any("mutual_defense=1" in se for se in result.side_effects)

    def test_lose_damage_split_per_member(self) -> None:
        """패배 본격 damage 본격 alive_members 본격 분담."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        # grade 1 본격 2인 본격 attack 60 vs 4인조 120 → 패배, damage 60, per_member 30
        c1 = Character(name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, grade=1)
        c2 = Character(name="한스", race=Race.HUMAN, hp=100, hp_max=100, grade=1)
        rng = random.Random(0)  # seed 0 본격 4인조
        result = execute_engage_bandit(
            "비요른", enc.name, [c1, c2], loc, [enc], WorldState(), rng=rng
        )
        assert result.success is False
        # 본격 분담 본격 본격 본격 본격 양쪽 본격 본격 비슷한 hp loss
        loss_1 = 100 - c1.hp
        loss_2 = 100 - c2.hp
        assert loss_1 > 0
        assert loss_2 > 0
        assert loss_1 == loss_2  # ★ 동일 분담

    def test_dead_member_excluded_from_pool(self) -> None:
        """죽은 멤버 본격 attack pool 본격 미포함."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        c1 = Character(name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, grade=5)
        dead = Character(name="한스", race=Race.HUMAN, hp=0, hp_max=100, grade=9)
        rng = random.Random(0)
        result = execute_engage_bandit(
            "비요른", enc.name, [c1, dead], loc, [enc], WorldState(), rng=rng
        )
        # alive_count = 1 본격 mutual_defense=1
        assert any("mutual_defense=1" in se for se in result.side_effects)


# ─── 9.17-d regression — 단일 actor 본격 본격 본격 ───


class TestBanditSingleActorBackwardCompat:
    def test_solo_actor_per_member_marker(self) -> None:
        """단일 actor 본격 bandit_defeat={actor}:... 본격 본격 (★ 9.17-d 호환)."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = Character(name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, grade=1)
        rng = random.Random(0)  # 4인조 seed
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(), rng=rng
        )
        assert result.success is False
        # 9.17-d test_lose_emits_damage_marker 본격 호환
        assert any(
            "bandit_defeat=비요른" in eff for eff in result.side_effects
        )

    def test_solo_actor_hp_loss_marker(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = Character(name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, grade=1)
        rng = random.Random(0)
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(), rng=rng
        )
        # 9.17-d test_lose_emits_hp_loss_marker 본격 호환
        assert any(
            eff.startswith("hp_loss=비요른:")
            for eff in result.side_effects
        )

    def test_solo_win_stone_proportional(self) -> None:
        """단일 actor 승리 본격 stone gain 본격 본격 (★ 9.17-d 호환)."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = Character(name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, grade=9)
        original_stone = bjorn.stone
        rng = random.Random(1)  # solo seed
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(), rng=rng
        )
        assert result.success is True
        # stone gain 본격 5000 (★ solo × 5000)
        assert bjorn.stone - original_stone == 5000
        # fame +5
        assert bjorn.fame == BANDIT_FAME_GAIN_WIN
