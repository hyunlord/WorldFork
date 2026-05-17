"""Phase 9.17-d — 약탈자 encounter (★ 24/37/51화 본문 정합) unit tests.

본 commit (B minimal):
- BanditEncounter dataclass (frozen, slots)
- PlayerActionType.ENGAGE_BANDIT (★ 27 → 28)
- _create_bandit_encounter (★ producer, 솔로/4인조 binary)
- execute_engage_bandit (★ HOSTILE consumer, flee/win/lose 분기)
- _generate_injury_from_damage 재사용 (★ 패배 시 부상)
"""

from __future__ import annotations

import dataclasses
import random

import pytest

from service.game.state_v2 import (
    BanditEncounter,
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    BANDIT_FAME_GAIN_WIN,
    BANDIT_HP_PER_MEMBER,
    BANDIT_STONE_PER_MEMBER,
    _create_bandit_encounter,
    execute_engage_bandit,
)
from service.sim.types import Encounter, EncounterType, PlayerActionType

# ─── BanditEncounter dataclass ───


class TestBanditEncounterDataclass:
    def test_create(self) -> None:
        b = BanditEncounter(
            faction_name="수정 연합",
            member_count=1,
            leader_grade=5,
            hp_pool=30,
        )
        assert b.faction_name == "수정 연합"
        assert b.member_count == 1
        assert b.leader_grade == 5
        assert b.hp_pool == 30

    def test_frozen(self) -> None:
        b = BanditEncounter(
            faction_name="수정 연합",
            member_count=1,
            leader_grade=5,
            hp_pool=30,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            b.member_count = 4  # type: ignore[misc]

    def test_4_member_count(self) -> None:
        b = BanditEncounter(
            faction_name="수정 연합",
            member_count=4,
            leader_grade=5,
            hp_pool=120,
        )
        assert b.member_count == 4
        assert b.hp_pool == 120


# ─── PlayerActionType.ENGAGE_BANDIT ───


class TestPlayerActionTypeEngageBandit:
    def test_engage_bandit_value(self) -> None:
        assert PlayerActionType.ENGAGE_BANDIT.value == "engage_bandit"


# ─── _create_bandit_encounter ───


class TestCreateBanditEncounter:
    def test_solo_or_four_only(self) -> None:
        """member_count 본격 1 또는 4 (★ 24화 솔로 / 37화 4인조)."""
        seen_counts: set[int] = set()
        for seed in range(100):
            rng = random.Random(seed)
            b = _create_bandit_encounter(5, "수정 연합", rng)
            seen_counts.add(b.member_count)
        assert seen_counts.issubset({1, 4})

    def test_solo_probability_approximate(self) -> None:
        """솔로 본격 BANDIT_SOLO_PROBABILITY (★ 70% ± margin)."""
        rng = random.Random(42)
        solos = 0
        for _ in range(1000):
            b = _create_bandit_encounter(5, "수정 연합", rng)
            if b.member_count == 1:
                solos += 1
        # 70% ± 5% — 사실상 normal distribution σ ≈ 14
        assert 650 <= solos <= 750

    def test_hp_pool_matches_member_count(self) -> None:
        for seed in range(50):
            rng = random.Random(seed)
            b = _create_bandit_encounter(5, "수정 연합", rng)
            assert b.hp_pool == BANDIT_HP_PER_MEMBER * b.member_count

    def test_leader_grade_within_delta(self) -> None:
        """leader_grade 본격 actor.grade ± 1."""
        for seed in range(100):
            rng = random.Random(seed)
            b = _create_bandit_encounter(5, "수정 연합", rng)
            assert 4 <= b.leader_grade <= 6

    def test_leader_grade_min_1_floor(self) -> None:
        """actor.grade=1 본격 leader_grade ≥ 1 (★ floor)."""
        for seed in range(100):
            rng = random.Random(seed)
            b = _create_bandit_encounter(1, "수정 연합", rng)
            assert b.leader_grade >= 1

    def test_faction_name_preserved(self) -> None:
        rng = random.Random(0)
        b = _create_bandit_encounter(5, "수정 연합", rng)
        assert b.faction_name == "수정 연합"


# ─── execute_engage_bandit ───


def _hostile_encounter(name: str = "bandit_enc_1") -> Encounter:
    return Encounter(
        type=EncounterType.NPC_HOSTILE,
        name=name,
        location="floor1_corridor",
        description="약탈자 무리의 기척이 느껴진다.",
    )


def _dungeon_loc() -> Location:
    return Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="floor1_corridor",
    )


def _bjorn(grade: int = 5) -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=100,
        hp_max=100,
        grade=grade,
    )


class TestExecuteEngageBanditFlee:
    def test_flee_always_succeeds(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        party = [_bjorn(grade=3)]
        result = execute_engage_bandit(
            "비요른", "flee", party, loc, [enc], WorldState()
        )
        assert result.success is True
        assert "도주" in result.message
        assert any(
            eff == f"encounter_consumed={enc.name}"
            for eff in result.side_effects
        )

    def test_flee_emits_fled_marker(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        party = [_bjorn()]
        result = execute_engage_bandit(
            "비요른", "flee", party, loc, [enc], WorldState()
        )
        assert any(
            eff.startswith("fled_from_bandit=")
            for eff in result.side_effects
        )

    def test_flee_no_hp_loss(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn()
        original_hp = bjorn.hp
        execute_engage_bandit(
            "비요른", "flee", [bjorn], loc, [enc], WorldState()
        )
        assert bjorn.hp == original_hp

    def test_flee_no_stone_gain(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn()
        original_stone = bjorn.stone
        execute_engage_bandit(
            "비요른", "flee", [bjorn], loc, [enc], WorldState()
        )
        assert bjorn.stone == original_stone


class TestExecuteEngageBanditFight:
    def test_high_grade_actor_wins_solo(self) -> None:
        """grade 9 actor (★ attack 110) vs solo (★ hp 30) → win 보장."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn(grade=9)
        original_stone = bjorn.stone
        original_fame = bjorn.fame

        # 솔로 seed 강제 (★ rng.random() < 0.7 본격 solo)
        # seed 0 본격 첫 호출 random() ≈ 0.84 → 4인조 (★ test_fight_low...)
        # seed 1 본격 첫 호출 random() ≈ 0.13 → 솔로
        rng = random.Random(1)
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(),
            rng=rng,
        )
        # 9등급 actor (attack=110) 본격 solo (hp 30) 본격 보장 승리
        assert result.success is True
        assert bjorn.stone > original_stone
        assert bjorn.fame == original_fame + BANDIT_FAME_GAIN_WIN

    def test_low_grade_actor_loses_to_four(self) -> None:
        """grade 1 actor (★ attack 30) vs 4인조 (★ hp 120) → 패배."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn(grade=1)
        original_hp = bjorn.hp

        # 4인조 강제 — seed 0 본격 0.84 → 4인조
        rng = random.Random(0)
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(),
            rng=rng,
        )
        # 1등급 actor (attack=30) 본격 4인조 (hp 120) 본격 보장 패배
        assert result.success is False
        assert bjorn.hp < original_hp

    def test_win_grants_fame_gain_marker(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn(grade=9)
        rng = random.Random(1)
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(),
            rng=rng,
        )
        assert result.success is True
        assert any(
            "fame_gain=비요른" in eff and "_bandit" in eff
            for eff in result.side_effects
        )

    def test_win_grants_stone_proportional(self) -> None:
        """승리 stone 본격 member_count × BANDIT_STONE_PER_MEMBER."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn(grade=9)
        original_stone = bjorn.stone
        rng = random.Random(1)  # 솔로 seed
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(),
            rng=rng,
        )
        assert result.success is True
        # 솔로 시 stone gain = 5000
        assert bjorn.stone - original_stone == BANDIT_STONE_PER_MEMBER

    def test_lose_emits_damage_marker(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn(grade=1)
        rng = random.Random(0)  # 4인조 seed
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(),
            rng=rng,
        )
        assert result.success is False
        assert any(
            "bandit_defeat=비요른" in eff for eff in result.side_effects
        )

    def test_lose_generates_injury(self) -> None:
        """패배 본격 _generate_injury_from_damage 본격 부상 generation."""
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn(grade=1)
        assert len(bjorn.injuries) == 0
        rng = random.Random(0)  # 4인조 seed — 큰 damage (90)
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(),
            rng=rng,
        )
        assert result.success is False
        # 큰 hp_loss 본격 injury 생성 (★ severity table 본격)
        assert len(bjorn.injuries) > 0

    def test_lose_emits_hp_loss_marker(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn(grade=1)
        rng = random.Random(0)
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(),
            rng=rng,
        )
        assert result.success is False
        assert any(
            eff.startswith("hp_loss=비요른:")
            for eff in result.side_effects
        )


# ─── encounter consume / 매칭 ───


class TestEncounterMatching:
    def test_no_hostile_fails(self) -> None:
        loc = _dungeon_loc()
        party = [_bjorn()]
        result = execute_engage_bandit(
            "비요른", "any", party, loc, [], WorldState()
        )
        assert result.success is False
        assert "약탈자" in result.message

    def test_only_peaceful_encounter_fails(self) -> None:
        """PEACEFUL encounter 본격 ENGAGE_BANDIT 본격 X."""
        loc = _dungeon_loc()
        peaceful_enc = Encounter(
            type=EncounterType.NPC_PEACEFUL,
            name="enc_peaceful_1",
            location="floor1_corridor",
            description="우호 탐험가.",
        )
        party = [_bjorn()]
        result = execute_engage_bandit(
            "비요른",
            peaceful_enc.name,
            party,
            loc,
            [peaceful_enc],
            WorldState(),
        )
        assert result.success is False

    def test_encounter_consumed_on_win(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn(grade=9)
        rng = random.Random(1)
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(),
            rng=rng,
        )
        assert result.success is True
        assert any(
            eff == f"encounter_consumed={enc.name}"
            for eff in result.side_effects
        )

    def test_encounter_consumed_on_lose(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        bjorn = _bjorn(grade=1)
        rng = random.Random(0)
        result = execute_engage_bandit(
            "비요른", enc.name, [bjorn], loc, [enc], WorldState(),
            rng=rng,
        )
        assert result.success is False
        assert any(
            eff == f"encounter_consumed={enc.name}"
            for eff in result.side_effects
        )

    def test_encounter_consumed_on_flee(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        party = [_bjorn()]
        result = execute_engage_bandit(
            "비요른", "flee", party, loc, [enc], WorldState()
        )
        assert any(
            eff == f"encounter_consumed={enc.name}"
            for eff in result.side_effects
        )

    def test_actor_not_in_party_fails(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        party = [_bjorn()]
        result = execute_engage_bandit(
            "유령", enc.name, party, loc, [enc], WorldState()
        )
        assert result.success is False


# ─── ACTION_HOURS_DELTA 정합 ───


class TestActionHoursDelta:
    def test_engage_bandit_has_delta(self) -> None:
        from service.sim.types import ACTION_HOURS_DELTA

        assert PlayerActionType.ENGAGE_BANDIT in ACTION_HOURS_DELTA


# ─── result.action_type 정합 ───


class TestResultActionType:
    def test_flee_action_type(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        result = execute_engage_bandit(
            "비요른", "flee", [_bjorn()], loc, [enc], WorldState()
        )
        assert result.action_type == "engage_bandit"

    def test_win_action_type(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        rng = random.Random(1)
        result = execute_engage_bandit(
            "비요른",
            enc.name,
            [_bjorn(grade=9)],
            loc,
            [enc],
            WorldState(),
            rng=rng,
        )
        assert result.action_type == "engage_bandit"

    def test_lose_action_type(self) -> None:
        loc = _dungeon_loc()
        enc = _hostile_encounter()
        rng = random.Random(0)
        result = execute_engage_bandit(
            "비요른",
            enc.name,
            [_bjorn(grade=1)],
            loc,
            [enc],
            WorldState(),
            rng=rng,
        )
        assert result.action_type == "engage_bandit"
