"""Phase 9.3 injury-schema — Injury dataclass + WAIT 자연 회복 wire 본격.

검증 본질:
- Injury frozen dataclass (★ recovery_days mutation X)
- Character.injuries default empty
- WAIT_IN_VILLAGE 자연 회복:
  * 살아남은 멤버 recovery_days--
  * 새 Injury instance 생성 (★ frozen)
  * recovery_days<=0 본격 → injury 제거 + injury_healed marker
  * 죽은 멤버 회복 X
  * 다수 injury 본격 독립

본문 정합:
- 23화: '팔뚝에 스크래치' (★ body_part="arm", severity="scratch")
- 25화: '목의 상처' + '흉터가 남겠군' (★ body_part="neck", severity="major", scar=True)

★ producer (ATTACK generation) 본격 별도 test 본격 (test_injury_generation.py).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from service.game.state_v2 import (
    SEVERITY_LEAVES_SCAR,
    SEVERITY_RECOVERY_DEFAULT,
    Character,
    Injury,
    InjuryBodyPart,
    InjurySeverity,
    Race,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import execute_wait_in_village

# ─── 0. enum + SEVERITY table ───


def test_severity_values() -> None:
    assert InjurySeverity.SCRATCH.value == "scratch"
    assert InjurySeverity.MINOR.value == "minor"
    assert InjurySeverity.MAJOR.value == "major"
    assert InjurySeverity.CRITICAL.value == "critical"


def test_body_part_values_23_25hwa() -> None:
    """23화 팔뚝 / 25화 목 본문 정합."""
    assert InjuryBodyPart.ARM.value == "arm"
    assert InjuryBodyPart.NECK.value == "neck"
    assert InjuryBodyPart.HEAD.value == "head"
    assert InjuryBodyPart.TORSO.value == "torso"
    assert InjuryBodyPart.LEG.value == "leg"


def test_severity_recovery_defaults() -> None:
    assert SEVERITY_RECOVERY_DEFAULT["scratch"] == 2
    assert SEVERITY_RECOVERY_DEFAULT["minor"] == 7
    assert SEVERITY_RECOVERY_DEFAULT["major"] == 21
    assert SEVERITY_RECOVERY_DEFAULT["critical"] == 60


def test_severity_scar_defaults_25hwa() -> None:
    """25화 본문: major 본격 흉터."""
    assert SEVERITY_LEAVES_SCAR["major"] is True
    assert SEVERITY_LEAVES_SCAR["critical"] is True
    assert SEVERITY_LEAVES_SCAR["scratch"] is False
    assert SEVERITY_LEAVES_SCAR["minor"] is False


# ─── 1. Injury dataclass ───


def test_injury_create() -> None:
    inj = Injury(severity="scratch", body_part="arm", recovery_days=2)
    assert inj.severity == "scratch"
    assert inj.body_part == "arm"
    assert inj.recovery_days == 2
    assert inj.scar is False  # ★ default


def test_injury_explicit_scar() -> None:
    inj = Injury(
        severity="major",
        body_part="neck",
        recovery_days=21,
        scar=True,
    )
    assert inj.scar is True


def test_injury_frozen() -> None:
    """recovery_days mutation X (★ frozen dataclass)."""
    inj = Injury(severity="minor", body_part="leg", recovery_days=7)
    with pytest.raises(FrozenInstanceError):
        inj.recovery_days = 0  # type: ignore[misc]


# ─── 2. Character.injuries ───


def test_character_injuries_default_empty() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    assert c.injuries == []


def test_character_injuries_append() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    c.injuries.append(
        Injury(severity="scratch", body_part="arm", recovery_days=2)
    )
    assert len(c.injuries) == 1


# ─── 3. WAIT_IN_VILLAGE 자연 회복 wire ───


def _village_world() -> WorldState:
    w = WorldState()
    w.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    return w


def _actor(hp: int = 100, hp_max: int = 100) -> Character:
    return Character(
        name="비요른", race=Race.BARBARIAN, hp=hp, hp_max=hp_max
    )


def test_wait_decrements_recovery_days() -> None:
    world = _village_world()
    actor = _actor()
    actor.injuries.append(
        Injury(severity="minor", body_part="leg", recovery_days=7)
    )
    result = execute_wait_in_village("비요른", [actor], world)
    assert result.success is True
    assert len(actor.injuries) == 1
    assert actor.injuries[0].recovery_days == 6  # ★ 7-1=6


def test_wait_removes_when_recovery_zero() -> None:
    world = _village_world()
    actor = _actor()
    actor.injuries.append(
        Injury(severity="scratch", body_part="arm", recovery_days=1)
    )
    result = execute_wait_in_village("비요른", [actor], world)
    assert len(actor.injuries) == 0
    # side_effect marker
    assert any(
        "injury_healed=비요른:arm_scratch" == s
        for s in result.side_effects
    )


def test_wait_dead_member_no_recovery() -> None:
    """본인 답: 죽은 멤버 영구 (★ 회복 X)."""
    world = _village_world()
    dead = _actor(hp=0)
    dead.injuries.append(
        Injury(severity="minor", body_part="arm", recovery_days=5)
    )
    execute_wait_in_village("비요른", [dead], world)
    assert dead.injuries[0].recovery_days == 5  # 변화 X


def test_wait_multiple_injuries_independent() -> None:
    """scratch 본격 healed, major 본격 진행 (★ 본격 독립)."""
    world = _village_world()
    actor = _actor()
    actor.injuries.append(
        Injury(severity="scratch", body_part="arm", recovery_days=1)
    )
    actor.injuries.append(
        Injury(
            severity="major",
            body_part="neck",
            recovery_days=20,
            scar=True,
        )
    )
    result = execute_wait_in_village("비요른", [actor], world)
    # scratch healed, major still recovering
    assert len(actor.injuries) == 1
    assert actor.injuries[0].severity == "major"
    assert actor.injuries[0].recovery_days == 19
    assert actor.injuries[0].scar is True  # ★ 보존
    # marker 1개만 (★ scratch 본격)
    healed_markers = [
        s for s in result.side_effects if s.startswith("injury_healed=")
    ]
    assert len(healed_markers) == 1
    assert "injury_healed=비요른:arm_scratch" in healed_markers


def test_wait_no_injuries_no_marker() -> None:
    """injuries 0 본격 marker 본격 X."""
    world = _village_world()
    actor = _actor()
    result = execute_wait_in_village("비요른", [actor], world)
    assert not any(
        "injury_healed=" in s for s in result.side_effects
    )


def test_wait_new_injury_instance_frozen_consistency() -> None:
    """recovery_days-- mutation 본격 새 Injury instance (★ frozen)."""
    world = _village_world()
    actor = _actor()
    original = Injury(
        severity="major",
        body_part="neck",
        recovery_days=10,
        scar=True,
    )
    actor.injuries.append(original)
    execute_wait_in_village("비요른", [actor], world)
    # 새 instance — original 본격 frozen 본격 본격
    assert actor.injuries[0] is not original
    assert original.recovery_days == 10  # 본격 변화 X
    assert actor.injuries[0].recovery_days == 9
    # scar 본격 보존
    assert actor.injuries[0].scar is True


def test_wait_outside_village_no_recovery() -> None:
    """ACTIVE status 본격 recovery X (★ 본격 본격 X)."""
    world = WorldState()  # ACTIVE
    actor = _actor()
    actor.injuries.append(
        Injury(severity="minor", body_part="leg", recovery_days=7)
    )
    result = execute_wait_in_village("비요른", [actor], world)
    assert result.success is False
    # injury 본격 변화 X
    assert actor.injuries[0].recovery_days == 7
