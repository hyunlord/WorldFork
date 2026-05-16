"""Phase 9.17-c2 — 밤친구 (★ 6/88/111화 본문 정합) unit tests.

본 commit (B minimal):
- Character.is_temporary field
- PlayerActionType FORM_NIGHT_COMPANION / DISBAND_NIGHT_COMPANION
- execute_form_night_companion (★ Realm + floor 검증 + Encounter 매칭)
- execute_disband_night_companion (★ individual / 'all', 영구 멤버 보호)
- _auto_disband_on_exit (★ 던전 출구 자동 해산)
- _auto_disband_on_death (★ 사망 자동 해산)
- gm_agent _format_party_status (★ 밤친구 section 표시)
"""

from __future__ import annotations

import random

from service.game.gm_agent import _format_party_status
from service.game.state_v2 import (
    Character,
    ClassType,
    Location,
    Race,
    Realm,
)
from service.game.turn_handler_v2 import (
    NIGHT_COMPANION_RECOMMENDED_TOTAL,
    _auto_disband_on_death,
    _auto_disband_on_exit,
    execute_disband_night_companion,
    execute_form_night_companion,
)
from service.sim.types import Encounter, EncounterType, PlayerActionType

# ─── Character.is_temporary ───


class TestCharacterIsTemporary:
    def test_default_false(self) -> None:
        c = Character(name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100)
        assert c.is_temporary is False

    def test_explicit_true(self) -> None:
        c = Character(
            name="한스",
            race=Race.HUMAN,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        assert c.is_temporary is True


# ─── PlayerActionType 본격 ───


class TestPlayerActionTypeFormDisband:
    def test_form_value(self) -> None:
        assert (
            PlayerActionType.FORM_NIGHT_COMPANION.value
            == "form_night_companion"
        )

    def test_disband_value(self) -> None:
        assert (
            PlayerActionType.DISBAND_NIGHT_COMPANION.value
            == "disband_night_companion"
        )

    def test_total_count_27(self) -> None:
        assert len(list(PlayerActionType)) == 27


# ─── execute_form_night_companion ───


def _dungeon_floor1() -> Location:
    return Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="floor1_corridor",
    )


def _peaceful_encounter(name: str = "enc_peaceful_1") -> Encounter:
    return Encounter(
        type=EncounterType.NPC_PEACEFUL,
        name=name,
        location="floor1_corridor",
        description="어둠 속에서 다른 탐험가의 인기척이 느껴진다.",
    )


def _bjorn() -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=100,
        hp_max=100,
    )


class TestFormNightCompanion:
    def test_form_success(self) -> None:
        loc = _dungeon_floor1()
        enc = _peaceful_encounter()
        party = [_bjorn()]
        rng = random.Random(42)
        result = execute_form_night_companion(
            "비요른", enc.name, party, loc, [enc], rng=rng
        )
        assert result.success is True
        assert len(party) == 2
        assert party[1].is_temporary is True
        assert party[1].hp == 80

    def test_form_outside_dungeon_fails(self) -> None:
        loc = Location(realm=Realm.CITY, sub_area="district_7_plaza")
        party = [_bjorn()]
        result = execute_form_night_companion(
            "비요른", "any", party, loc, []
        )
        assert result.success is False
        assert "던전" in result.message
        assert len(party) == 1

    def test_form_floor_2_fails(self) -> None:
        loc = Location(
            realm=Realm.DUNGEON, floor=2, sub_area="floor2_corridor"
        )
        party = [_bjorn()]
        result = execute_form_night_companion(
            "비요른", "any", party, loc, []
        )
        assert result.success is False
        assert "1층" in result.message or "111화" in result.message
        assert len(party) == 1

    def test_form_no_floor_fails(self) -> None:
        loc = Location(realm=Realm.DUNGEON, sub_area="unknown")
        party = [_bjorn()]
        result = execute_form_night_companion(
            "비요른", "any", party, loc, []
        )
        assert result.success is False
        assert len(party) == 1

    def test_form_no_peaceful_fails(self) -> None:
        loc = _dungeon_floor1()
        party = [_bjorn()]
        result = execute_form_night_companion(
            "비요른", "any", party, loc, []
        )
        assert result.success is False
        assert "우호" in result.message
        assert len(party) == 1

    def test_form_wrong_encounter_type_fails(self) -> None:
        loc = _dungeon_floor1()
        wrong_enc = Encounter(
            type=EncounterType.NPC_NEUTRAL,
            name="enc_neutral_1",
            location="floor1_corridor",
            description="통과하는 탐험가.",
        )
        party = [_bjorn()]
        result = execute_form_night_companion(
            "비요른", wrong_enc.name, party, loc, [wrong_enc]
        )
        assert result.success is False
        assert len(party) == 1

    def test_form_emits_encounter_consumed(self) -> None:
        loc = _dungeon_floor1()
        enc = _peaceful_encounter()
        party = [_bjorn()]
        result = execute_form_night_companion(
            "비요른", enc.name, party, loc, [enc]
        )
        assert result.success is True
        assert any(
            eff == f"encounter_consumed={enc.name}"
            for eff in result.side_effects
        )

    def test_form_emits_companion_formed(self) -> None:
        loc = _dungeon_floor1()
        enc = _peaceful_encounter()
        party = [_bjorn()]
        result = execute_form_night_companion(
            "비요른", enc.name, party, loc, [enc]
        )
        assert any(
            eff.startswith("night_companion_formed=")
            for eff in result.side_effects
        )

    def test_recommended_total_warning(self) -> None:
        loc = _dungeon_floor1()
        enc = _peaceful_encounter()
        members = [
            Character(
                name=f"M{i}", race=Race.HUMAN, hp=100, hp_max=100
            )
            for i in range(NIGHT_COMPANION_RECOMMENDED_TOTAL)
        ]
        result = execute_form_night_companion(
            "M0", enc.name, members, loc, [enc]
        )
        assert result.success is True
        assert "권장" in result.message

    def test_recommended_total_no_warning_at_limit(self) -> None:
        """권장 인원 본격 — 권장 정확히 도달 본격 본격 경고 X."""
        loc = _dungeon_floor1()
        enc = _peaceful_encounter()
        members = [
            Character(
                name=f"M{i}", race=Race.HUMAN, hp=100, hp_max=100
            )
            for i in range(NIGHT_COMPANION_RECOMMENDED_TOTAL - 1)
        ]
        result = execute_form_night_companion(
            "M0", enc.name, members, loc, [enc]
        )
        assert result.success is True
        # 권장 도달 본격 본격 경고 X (★ 본격 초과 본격 본격).
        assert "권장" not in result.message

    def test_form_action_type_is_form_night_companion(self) -> None:
        loc = _dungeon_floor1()
        enc = _peaceful_encounter()
        party = [_bjorn()]
        result = execute_form_night_companion(
            "비요른", enc.name, party, loc, [enc]
        )
        assert result.action_type == "form_night_companion"


# ─── execute_disband_night_companion ───


class TestDisbandNightCompanion:
    def test_disband_specific(self) -> None:
        bjorn = _bjorn()
        hans = Character(
            name="한스",
            race=Race.HUMAN,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        party = [bjorn, hans]
        result = execute_disband_night_companion("비요른", "한스", party)
        assert result.success is True
        assert len(party) == 1
        assert party[0].name == "비요른"

    def test_disband_all(self) -> None:
        bjorn = _bjorn()
        hans = Character(
            name="한스",
            race=Race.HUMAN,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        karl = Character(
            name="칼",
            race=Race.DWARF,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        party = [bjorn, hans, karl]
        result = execute_disband_night_companion("비요른", "all", party)
        assert result.success is True
        assert len(party) == 1
        assert party[0].name == "비요른"

    def test_disband_no_temp_fails(self) -> None:
        party = [_bjorn()]
        result = execute_disband_night_companion("비요른", "all", party)
        assert result.success is False
        assert len(party) == 1

    def test_disband_permanent_fails(self) -> None:
        bjorn = _bjorn()
        permanent = Character(
            name="에르웬",
            race=Race.FAERIE,
            hp=100,
            hp_max=100,
            is_temporary=False,
        )
        party = [bjorn, permanent]
        result = execute_disband_night_companion(
            "비요른", "에르웬", party
        )
        assert result.success is False
        assert len(party) == 2

    def test_disband_unknown_target_fails(self) -> None:
        party = [_bjorn()]
        result = execute_disband_night_companion(
            "비요른", "유령", party
        )
        assert result.success is False
        assert len(party) == 1

    def test_disband_emits_side_effects(self) -> None:
        bjorn = _bjorn()
        hans = Character(
            name="한스",
            race=Race.HUMAN,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        party = [bjorn, hans]
        result = execute_disband_night_companion("비요른", "한스", party)
        assert any(
            eff == "night_companion_disbanded=한스"
            for eff in result.side_effects
        )


# ─── _auto_disband_on_exit ───


class TestAutoDisbandOnExit:
    def test_disbands_temps(self) -> None:
        bjorn = _bjorn()
        hans = Character(
            name="한스",
            race=Race.HUMAN,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        party = [bjorn, hans]
        side_effects: list[str] = []
        _auto_disband_on_exit(party, side_effects)
        assert len(party) == 1
        assert party[0].name == "비요른"
        assert any(
            "auto_disbanded_on_exit=한스" in eff
            for eff in side_effects
        )

    def test_keeps_permanent(self) -> None:
        bjorn = _bjorn()
        erwen = Character(
            name="에르웬",
            race=Race.FAERIE,
            hp=100,
            hp_max=100,
            is_temporary=False,
        )
        party = [bjorn, erwen]
        side_effects: list[str] = []
        _auto_disband_on_exit(party, side_effects)
        assert len(party) == 2
        assert side_effects == []

    def test_disbands_alive_temp(self) -> None:
        """alive 본격 temp 본격 본격 출구 시 자동 해산."""
        bjorn = _bjorn()
        alive_temp = Character(
            name="한스",
            race=Race.HUMAN,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        party = [bjorn, alive_temp]
        side_effects: list[str] = []
        _auto_disband_on_exit(party, side_effects)
        assert len(party) == 1
        assert party[0].name == "비요른"


# ─── _auto_disband_on_death ───


class TestAutoDisbandOnDeath:
    def test_dead_temp_removed(self) -> None:
        bjorn = _bjorn()
        dead_temp = Character(
            name="한스",
            race=Race.HUMAN,
            hp=0,
            hp_max=80,
            is_temporary=True,
        )
        party = [bjorn, dead_temp]
        side_effects: list[str] = []
        _auto_disband_on_death(party, side_effects)
        assert len(party) == 1
        assert party[0].name == "비요른"
        assert any(
            "auto_disbanded_on_death=한스" in eff
            for eff in side_effects
        )

    def test_dead_permanent_kept(self) -> None:
        """영구 멤버 사망 본격 본격 X (★ defeated 검증 별도)."""
        bjorn = _bjorn()
        dead_perm = Character(
            name="에르웬",
            race=Race.FAERIE,
            hp=0,
            hp_max=100,
            is_temporary=False,
        )
        party = [bjorn, dead_perm]
        side_effects: list[str] = []
        _auto_disband_on_death(party, side_effects)
        assert len(party) == 2
        assert side_effects == []

    def test_alive_temp_kept(self) -> None:
        """alive temp 본격 본격 X (★ 사망 본격 본격 본격 hp<=0)."""
        bjorn = _bjorn()
        alive_temp = Character(
            name="한스",
            race=Race.HUMAN,
            hp=50,
            hp_max=80,
            is_temporary=True,
        )
        party = [bjorn, alive_temp]
        side_effects: list[str] = []
        _auto_disband_on_death(party, side_effects)
        assert len(party) == 2
        assert side_effects == []

    def test_mixed_alive_dead_temps(self) -> None:
        """alive temp 본격 유지 / dead temp 본격 본격 제거."""
        bjorn = _bjorn()
        dead_temp = Character(
            name="한스",
            race=Race.HUMAN,
            hp=0,
            hp_max=80,
            is_temporary=True,
        )
        alive_temp = Character(
            name="칼",
            race=Race.DWARF,
            hp=60,
            hp_max=80,
            is_temporary=True,
        )
        party = [bjorn, dead_temp, alive_temp]
        side_effects: list[str] = []
        _auto_disband_on_death(party, side_effects)
        assert len(party) == 2
        assert {m.name for m in party} == {"비요른", "칼"}


# ─── gm_agent _format_party_status ───


class TestFormatPartyStatus:
    def test_companion_section_shown(self) -> None:
        bjorn = _bjorn()
        hans = Character(
            name="한스",
            race=Race.HUMAN,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        result = _format_party_status([bjorn, hans])
        assert "밤친구" in result
        assert "한스" in result
        assert "임시 협력" in result

    def test_no_companion_no_section(self) -> None:
        bjorn = _bjorn()
        result = _format_party_status([bjorn])
        assert "밤친구" not in result
        assert result == ""

    def test_multiple_companions_count(self) -> None:
        bjorn = _bjorn()
        hans = Character(
            name="한스",
            race=Race.HUMAN,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        karl = Character(
            name="칼",
            race=Race.DWARF,
            hp=80,
            hp_max=80,
            is_temporary=True,
        )
        result = _format_party_status([bjorn, hans, karl])
        assert "2명" in result
        assert "한스" in result
        assert "칼" in result


# ─── PlayerActionType ACTION_HOURS_DELTA 정합 ───


class TestActionHoursDelta:
    def test_form_has_delta(self) -> None:
        from service.sim.types import ACTION_HOURS_DELTA

        assert PlayerActionType.FORM_NIGHT_COMPANION in ACTION_HOURS_DELTA

    def test_disband_has_delta(self) -> None:
        from service.sim.types import ACTION_HOURS_DELTA

        assert (
            PlayerActionType.DISBAND_NIGHT_COMPANION in ACTION_HOURS_DELTA
        )


# ─── ClassType import 확인 (★ Character.class_type 본격 본격) ───


class TestNightCompanionClassType:
    def test_warrior_default(self) -> None:
        """밤친구 본격 본격 신참 WARRIOR (★ 9.9-a 정합)."""
        loc = _dungeon_floor1()
        enc = _peaceful_encounter()
        party = [_bjorn()]
        result = execute_form_night_companion(
            "비요른", enc.name, party, loc, [enc]
        )
        assert result.success is True
        assert party[1].class_type == ClassType.WARRIOR.value
