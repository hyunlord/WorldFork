"""Phase D step 6b — StatusEffect schema + apply logic tests."""

from __future__ import annotations

from service.sim.status import (
    StatusEffect,
    StatusType,
    apply_status_effects,
    deserialize_status,
    extract_status_from_text,
    serialize_status,
)


def _poison(duration: int = 3, intensity: int = 3) -> StatusEffect:
    return StatusEffect(
        type=StatusType.POISON, duration=duration, intensity=intensity, source="독화살"
    )


def test_apply_poison_reduces_hp() -> None:
    hp, effects = apply_status_effects(50, 100, [_poison()])
    assert hp == 47
    assert len(effects) == 1
    assert effects[0].duration == 2


def test_apply_bleed_reduces_hp() -> None:
    effect = StatusEffect(type=StatusType.BLEED, duration=2, intensity=5, source="출혈")
    hp, effects = apply_status_effects(50, 100, [effect])
    assert hp == 45
    assert effects[0].duration == 1


def test_apply_burn_reduces_hp() -> None:
    effect = StatusEffect(type=StatusType.BURN, duration=1, intensity=4, source="화상")
    hp, effects = apply_status_effects(50, 100, [effect])
    assert hp == 46
    assert effects == []  # duration 1 → expires


def test_apply_paralyze_no_hp_change() -> None:
    effect = StatusEffect(type=StatusType.PARALYZE, duration=2, intensity=0, source="마비")
    hp, effects = apply_status_effects(50, 100, [effect])
    assert hp == 50  # no damage
    assert len(effects) == 1


def test_apply_slow_no_hp_change() -> None:
    effect = StatusEffect(type=StatusType.SLOW, duration=3, intensity=0, source="둔화")
    hp, effects = apply_status_effects(60, 100, [effect])
    assert hp == 60
    assert effects[0].duration == 2


def test_status_duration_decrements() -> None:
    hp, effects = apply_status_effects(100, 100, [_poison(duration=3)])
    assert effects[0].duration == 2
    hp, effects = apply_status_effects(hp, 100, effects)
    assert effects[0].duration == 1
    hp, effects = apply_status_effects(hp, 100, effects)
    assert effects == []  # expired


def test_hp_floor_zero() -> None:
    effect = StatusEffect(type=StatusType.POISON, duration=3, intensity=100, source="독")
    hp, _ = apply_status_effects(5, 100, [effect])
    assert hp == 0


def test_extract_status_poison() -> None:
    effects = extract_status_from_text("독화살 (P)")
    assert any(e.type == StatusType.POISON for e in effects)


def test_extract_status_paralyze() -> None:
    effects = extract_status_from_text("마비독 상시 부여")
    assert any(e.type == StatusType.PARALYZE for e in effects)


def test_extract_status_multiple() -> None:
    effects = extract_status_from_text("독성 + 출혈 공격")
    types = {e.type for e in effects}
    assert StatusType.POISON in types
    assert StatusType.BLEED in types


def test_extract_status_empty() -> None:
    assert extract_status_from_text("기본 공격") == []


def test_serialize_round_trip() -> None:
    s = _poison(duration=2, intensity=5)
    d = serialize_status(s)
    s2 = deserialize_status(d)
    assert s2.type == StatusType.POISON
    assert s2.duration == 2
    assert s2.intensity == 5
