"""EntityIndex race ability_tiers lookup 단위 테스트 (★ I-G1 runtime)."""

from __future__ import annotations

from service.canon.entity_index import EntityIndex
from service.canon.schema import (
    AbilityEntry,
    AbilityTier,
    CanonFacts,
    EssenceAbilities,
    Race,
)


def _make_facts() -> CanonFacts:
    return CanonFacts(
        essences=[],
        characters=[],
        locations=[],
        races=[
            Race(
                name="드워프",
                description="산악 거주 종족",
                ability_tiers=EssenceAbilities(
                    text="건축 조예(상), 야금술(중), 노화 저항(하)",
                    parsed=[
                        AbilityEntry(name="건축 조예", tier=AbilityTier.HIGH),
                        AbilityEntry(name="야금술", tier=AbilityTier.MID),
                        AbilityEntry(name="노화 저항", tier=AbilityTier.LOW),
                    ],
                ),
            ),
            Race(
                name="수인",
                ability_tiers=EssenceAbilities(
                    text="민첩(상), 후각(상)",
                    parsed=[
                        AbilityEntry(name="민첩", tier=AbilityTier.HIGH),
                        AbilityEntry(name="후각", tier=AbilityTier.HIGH),
                    ],
                ),
            ),
            Race(name="무특성종족", description="ability_tiers 없음"),
        ],
        mechanisms=[],
    )


def test_get_race_ability_tiers_exact() -> None:
    idx = EntityIndex(_make_facts())
    at = idx.get_race_ability_tiers("드워프")
    assert at is not None
    assert "건축 조예(상)" in str(at["text"])
    assert len(at["parsed"]) == 3


def test_get_race_ability_tiers_parsed_tier_valid() -> None:
    idx = EntityIndex(_make_facts())
    at = idx.get_race_ability_tiers("드워프")
    assert at is not None
    for p in at["parsed"]:
        assert p["tier"] in ("상", "중", "하")


def test_get_race_ability_tiers_no_tiers() -> None:
    """ability_tiers 빈 race → None (map 미등록)."""
    idx = EntityIndex(_make_facts())
    assert idx.get_race_ability_tiers("무특성종족") is None


def test_get_race_ability_tiers_unknown() -> None:
    idx = EntityIndex(_make_facts())
    assert idx.get_race_ability_tiers("존재하지않는종족XYZ") is None
    assert idx.get_race_ability_tiers("") is None


def test_get_race_ability_tiers_fuzzy() -> None:
    """공백/조사 fuzzy fallback."""
    idx = EntityIndex(_make_facts())
    at = idx.get_race_ability_tiers("수인의")
    assert at is not None
    assert "민첩(상)" in str(at["text"])
