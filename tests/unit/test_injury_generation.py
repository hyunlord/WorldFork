"""Phase 9.3 — Injury ATTACK generation producer 본격 unit.

검증 본질:
- _severity_for_damage hp_loss boundary mapping (★ 0/10/30/60+)
- _generate_injury_from_damage:
  * hp_loss=0 본격 None
  * recovery_days = SEVERITY_RECOVERY_DEFAULT
  * scar = SEVERITY_LEAVES_SCAR
  * body_part random (★ rng inject seed reproducibility)
- execute_attack 본격 wire:
  * 실패 본격 (★ damage < 30) hp_loss 본격 injury append
  * injury_inflicted side_effect marker
  * 성공 본격 (★ damage >= 30) injury 본격 X
"""

from __future__ import annotations

import random

from service.game.state_v2 import (
    SEVERITY_LEAVES_SCAR,
    SEVERITY_RECOVERY_DEFAULT,
    Character,
    InjuryBodyPart,
    InjurySeverity,
    Race,
    WorldState,
)
from service.game.turn_handler_v2 import (
    _generate_injury_from_damage,
    _severity_for_damage,
    execute_attack,
)

# ─── 1. _severity_for_damage boundary ───


def test_severity_zero_damage_none() -> None:
    assert _severity_for_damage(0) is None


def test_severity_negative_damage_none() -> None:
    assert _severity_for_damage(-5) is None


def test_severity_scratch_1_to_10() -> None:
    assert _severity_for_damage(1) == "scratch"
    assert _severity_for_damage(10) == "scratch"


def test_severity_minor_11_to_30() -> None:
    assert _severity_for_damage(11) == "minor"
    assert _severity_for_damage(30) == "minor"


def test_severity_major_31_to_60() -> None:
    assert _severity_for_damage(31) == "major"
    assert _severity_for_damage(60) == "major"


def test_severity_critical_61_plus() -> None:
    assert _severity_for_damage(61) == "critical"
    assert _severity_for_damage(200) == "critical"


# ─── 2. _generate_injury_from_damage ───


def test_generate_zero_damage_none() -> None:
    assert _generate_injury_from_damage(0) is None


def test_generate_scratch_recovery_2_no_scar() -> None:
    rng = random.Random(42)
    inj = _generate_injury_from_damage(5, rng)
    assert inj is not None
    assert inj.severity == "scratch"
    assert inj.recovery_days == SEVERITY_RECOVERY_DEFAULT["scratch"]
    assert inj.scar is False
    # body_part 본격 enum value 본격 본격
    assert inj.body_part in {bp.value for bp in InjuryBodyPart}


def test_generate_major_scar_true() -> None:
    rng = random.Random(0)
    inj = _generate_injury_from_damage(50, rng)
    assert inj is not None
    assert inj.severity == "major"
    assert inj.recovery_days == SEVERITY_RECOVERY_DEFAULT["major"]
    assert inj.scar is True  # ★ 25화 본문 정합
    assert SEVERITY_LEAVES_SCAR[inj.severity] is True


def test_generate_critical_scar_true_recovery_60() -> None:
    rng = random.Random(0)
    inj = _generate_injury_from_damage(100, rng)
    assert inj is not None
    assert inj.severity == "critical"
    assert inj.recovery_days == 60
    assert inj.scar is True


def test_generate_body_part_rng_reproducible() -> None:
    """fixed seed 본격 body_part 본격 결정."""
    inj_a = _generate_injury_from_damage(5, random.Random(42))
    inj_b = _generate_injury_from_damage(5, random.Random(42))
    assert inj_a is not None and inj_b is not None
    assert inj_a.body_part == inj_b.body_part


def test_generate_default_rng_no_crash() -> None:
    """rng=None default 본격 (★ production caller 본격 본격 본격)."""
    inj = _generate_injury_from_damage(5)
    assert inj is not None
    assert inj.severity == InjurySeverity.SCRATCH.value


# ─── 3. execute_attack 본격 wire (★ producer) ───


def _weak_attacker() -> Character:
    """damage < 30 본격 본격 X 본격 본격."""
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=100,
        hp_max=100,
        physical=5,
        strength=5,
        bone_strength=10,  # ★ received = max(0, 10-5) = 5 → SCRATCH
        is_player=True,
    )


def _strong_attacker() -> Character:
    return Character(
        name="투르윈",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        physical=15,
        strength=20,
        bone_strength=10,
        is_player=True,
    )


def test_failed_attack_inflicts_injury() -> None:
    """damage < 30 본격 hp_loss 본격 injury append (★ producer wire)."""
    attacker = _weak_attacker()
    world = WorldState()
    result = execute_attack(attacker, "고블린", [attacker], world)
    assert result.success is False
    # hp_loss = max(0, 10 - 10//2) = 5 → SCRATCH
    assert len(attacker.injuries) == 1
    inj = attacker.injuries[0]
    assert inj.severity == "scratch"
    assert inj.recovery_days == SEVERITY_RECOVERY_DEFAULT["scratch"]


def test_failed_attack_side_effect_injury_inflicted() -> None:
    """side_effect marker 본격."""
    attacker = _weak_attacker()
    world = WorldState()
    result = execute_attack(attacker, "고블린", [attacker], world)
    assert any(
        s.startswith(f"injury_inflicted={attacker.name}:")
        for s in result.side_effects
    )


def test_successful_attack_no_injury() -> None:
    """damage >= 30 → 처치 → 본격 X (★ attacker hp_loss X)."""
    attacker = _strong_attacker()
    world = WorldState()
    result = execute_attack(attacker, "고블린", [attacker], world)
    assert result.success is True
    assert len(attacker.injuries) == 0
    # 본격 본격 marker 본격 X
    assert not any(
        s.startswith(f"injury_inflicted={attacker.name}:")
        for s in result.side_effects
    )


def test_failed_attack_no_damage_no_injury() -> None:
    """bone_strength 본격 본격 received=0 본격 본격 본격 X 본격 부상 X."""
    attacker = Character(
        name="강골",
        race=Race.BARBARIAN,
        hp=100,
        hp_max=100,
        physical=5,
        strength=5,
        bone_strength=100,  # ★ received = max(0, 10-50) = 0
        is_player=True,
    )
    world = WorldState()
    result = execute_attack(attacker, "고블린", [attacker], world)
    assert result.success is False
    assert len(attacker.injuries) == 0


def test_failed_attack_accumulates_injuries() -> None:
    """반복 본격 본격 본격 누적."""
    attacker = _weak_attacker()
    world = WorldState()
    execute_attack(attacker, "고블린", [attacker], world)
    execute_attack(attacker, "고블린", [attacker], world)
    execute_attack(attacker, "고블린", [attacker], world)
    assert len(attacker.injuries) == 3
