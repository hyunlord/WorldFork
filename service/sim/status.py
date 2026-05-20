"""Phase D step 6b — StatusEffect schema + apply logic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StatusType(StrEnum):
    POISON = "poison"
    PARALYZE = "paralyze"
    BLEED = "bleed"
    BURN = "burn"
    SLOW = "slow"


STATUS_KEYWORD_MAP: dict[str, StatusType] = {
    "독": StatusType.POISON,
    "마비": StatusType.PARALYZE,
    "출혈": StatusType.BLEED,
    "화상": StatusType.BURN,
    "둔화": StatusType.SLOW,
}


@dataclass
class StatusEffect:
    type: StatusType
    duration: int
    intensity: int
    source: str


def extract_status_from_text(text: str) -> list[StatusEffect]:
    """canon skill / ability 텍스트에서 status effect 추출."""
    effects: list[StatusEffect] = []
    for keyword, status_type in STATUS_KEYWORD_MAP.items():
        if keyword in text:
            effects.append(StatusEffect(
                type=status_type,
                duration=3,
                intensity=3,
                source=text[:50],
            ))
    return effects


def apply_status_effects(
    hp: int,
    max_hp: int,
    effects: list[StatusEffect],
) -> tuple[int, list[StatusEffect]]:
    """한 턴 status 적용.

    return: (new_hp, surviving_effects)
    """
    new_hp = hp
    surviving: list[StatusEffect] = []
    for effect in effects:
        if effect.type in (StatusType.POISON, StatusType.BLEED, StatusType.BURN):
            new_hp = max(0, new_hp - effect.intensity)
        if effect.duration > 1:
            surviving.append(StatusEffect(
                type=effect.type,
                duration=effect.duration - 1,
                intensity=effect.intensity,
                source=effect.source,
            ))
    return new_hp, surviving


def serialize_status(s: StatusEffect) -> dict[str, object]:
    return {
        "type": s.type.value,
        "duration": s.duration,
        "intensity": s.intensity,
        "source": s.source,
    }


def deserialize_status(d: dict[str, object]) -> StatusEffect:
    type_val = d.get("type", "")
    duration_val = d.get("duration", 1)
    intensity_val = d.get("intensity", 1)
    source_val = d.get("source", "")
    return StatusEffect(
        type=StatusType(str(type_val)),
        duration=int(duration_val) if isinstance(duration_val, (int, float)) else 1,
        intensity=int(intensity_val) if isinstance(intensity_val, (int, float)) else 1,
        source=str(source_val),
    )
