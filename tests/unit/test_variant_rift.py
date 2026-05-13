"""Phase 8 A2 — variant rift spawn mechanism 검증.

본질:
- decide_variant: VariantTrigger 본격 reproducible (★ rng seed)
- enter_rift: variant 결정 본격 location.rift_is_variant mutation
- gm_agent: boss chamber 도달 시 변종 시각 표시
"""

from __future__ import annotations

import random
from dataclasses import replace

from service.game.floors.floor1_rifts import (
    FLOOR1_RIFT_DEFS,
    decide_variant,
)
from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    VariantTrigger,
    WorldState,
)
from service.game.turn_handler_v2 import enter_rift

# ─── VariantTrigger schema ───


def test_bloody_castle_has_trigger() -> None:
    """핏빛성채: variant_trigger 본격 (★ 캠보르미어 spawn)."""
    bc = FLOOR1_RIFT_DEFS["bloody_castle"]
    assert bc.variant_trigger is not None
    # ★ namu "매우 드물게" → 매우 낮은 확률
    assert 0 < bc.variant_trigger.base_probability < 0.1


def test_glacier_has_trigger() -> None:
    """빙하굴: variant_trigger 본격 (★ 키르뒤 spawn)."""
    gc = FLOOR1_RIFT_DEFS["glacier_cave"]
    assert gc.variant_trigger is not None


def test_green_mine_no_trigger() -> None:
    """녹색 탄광: namu/본인 변종 X — trigger None."""
    gm = FLOOR1_RIFT_DEFS["green_mine"]
    assert gm.variant_trigger is None


def test_iron_tomb_no_trigger() -> None:
    """강철의 묘: namu/본인 변종 X — trigger None."""
    it = FLOOR1_RIFT_DEFS["iron_tomb"]
    assert it.variant_trigger is None


# ─── decide_variant() ───


def test_no_trigger_always_false() -> None:
    """trigger None 시 — 항상 False."""
    gm = FLOOR1_RIFT_DEFS["green_mine"]
    for seed in range(10):
        rng = random.Random(seed)
        assert decide_variant(gm, rng) is False


def test_trigger_low_probability() -> None:
    """base 2% 본격 — 1000회 시 < 10% 발현 본격."""
    bc = FLOOR1_RIFT_DEFS["bloody_castle"]
    rng = random.Random(42)
    variants = sum(decide_variant(bc, rng) for _ in range(1000))
    assert variants < 100, f"변종 {variants}/1000 > 10% (★ base 2%)"
    assert variants > 0, "변종 0회 — 너무 낮음"


def test_high_prob_forces_variant() -> None:
    """base_probability=1.0 — 항상 변종."""
    bc = FLOOR1_RIFT_DEFS["bloody_castle"]
    forced = replace(bc, variant_trigger=VariantTrigger(base_probability=1.0))
    for seed in range(5):
        rng = random.Random(seed)
        assert decide_variant(forced, rng) is True


def test_variant_boss_name_none_blocks_variant() -> None:
    """variant_boss_name None 시 — trigger 있어도 False (★ green/iron 대비)."""
    bc = FLOOR1_RIFT_DEFS["bloody_castle"]
    no_variant_boss = replace(
        bc,
        variant_boss_name=None,
        variant_trigger=VariantTrigger(base_probability=1.0),
    )
    rng = random.Random(42)
    assert decide_variant(no_variant_boss, rng) is False


def test_reproducible_with_seed() -> None:
    """같은 seed 본격 같은 결과."""
    bc = FLOOR1_RIFT_DEFS["bloody_castle"]
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    results1 = [decide_variant(bc, rng1) for _ in range(100)]
    results2 = [decide_variant(bc, rng2) for _ in range(100)]
    assert results1 == results2


# ─── enter_rift mutation ───


def _make_party_and_world(rift_id: str) -> tuple[list[Character], WorldState]:
    """진입 가능 본격 minimal party + world."""
    party = [
        Character(name="비요른", race=Race.BARBARIAN, is_player=True),
    ]
    world = WorldState(active_rifts=[rift_id])
    return party, world


def test_enter_rift_force_variant_true() -> None:
    """force_variant=True 시 — side_effect 본격 True."""
    party, world = _make_party_and_world("bloody_castle")
    r = enter_rift(party, world, "bloody_castle", force_variant=True)
    assert r.success
    assert any("target_rift_is_variant=True" in eff for eff in r.side_effects)
    assert "공기가 다르다" in r.message


def test_enter_rift_force_variant_false() -> None:
    """force_variant=False 시 — side_effect 본격 False + 변종 msg X."""
    party, world = _make_party_and_world("bloody_castle")
    r = enter_rift(party, world, "bloody_castle", force_variant=False)
    assert r.success
    assert any("target_rift_is_variant=False" in eff for eff in r.side_effects)
    assert "공기가 다르다" not in r.message


def test_enter_rift_force_variant_blocked_by_none_boss() -> None:
    """variant_boss X 균열 (★ 강철의 묘): force_variant=True 본격 False 본격."""
    party, world = _make_party_and_world("iron_tomb")
    r = enter_rift(party, world, "iron_tomb", force_variant=True)
    assert r.success
    # variant_boss_name=None → is_variant 본격 False 본격
    assert any(
        "target_rift_is_variant=False" in eff for eff in r.side_effects
    )


def test_enter_rift_seeded_rng() -> None:
    """rng 본격 reproducibility 본격 — 같은 seed 본격 같은 variant 결과."""
    party, world = _make_party_and_world("bloody_castle")
    # 본격 1 본격: seed=0 본격 variant 본격 본격 본격 본격
    r1 = enter_rift(
        party, world, "bloody_castle", rng=random.Random(0)
    )
    party2, world2 = _make_party_and_world("bloody_castle")
    r2 = enter_rift(
        party2, world2, "bloody_castle", rng=random.Random(0)
    )
    assert r1.success and r2.success
    # 본격 본격 same seed → same is_variant 본격
    eff1 = next(
        e for e in r1.side_effects if e.startswith("target_rift_is_variant=")
    )
    eff2 = next(
        e for e in r2.side_effects if e.startswith("target_rift_is_variant=")
    )
    assert eff1 == eff2


# ─── gm_agent boss chamber message ───


def _ctx_at_boss_chamber(*, is_variant: bool) -> dict[str, object]:
    """rift 내부 + boss chamber 위치 ctx."""
    from tools.measure_gm_prompt import _ctx_inside_rift_boss

    ctx = _ctx_inside_rift_boss()
    loc = dict(ctx["v2_initial_location"])  # type: ignore[arg-type]
    loc["rift_sub_area"] = "bc_ch5"  # ★ 핏빛성채 boss chamber
    loc["rift_is_variant"] = is_variant
    ctx["v2_initial_location"] = loc
    return ctx


def test_boss_chamber_variant_message() -> None:
    """rift_is_variant=True + boss chamber 본격 → 변종 시각 표시."""
    prompt = _gm_system_prompt(_ctx_at_boss_chamber(is_variant=True))
    assert "변종이 깨어났다" in prompt
    assert "캠보르미어" in prompt
    assert "진입 여부는 파티 결정" in prompt


def test_boss_chamber_normal_message() -> None:
    """rift_is_variant=False + boss chamber 본격 → 일반 수호자 표시."""
    prompt = _gm_system_prompt(_ctx_at_boss_chamber(is_variant=False))
    # 변종 본격 X
    assert "변종이 깨어났다" not in prompt
    assert "보스방 앞 — 수호자" in prompt
    assert "저주받은 기사 블라터" in prompt


def test_non_boss_chamber_no_variant_hint() -> None:
    """boss chamber X 본격 — 변종 hint X (★ 진입 시 hint는 enter_rift 메시지만)."""
    from tools.measure_gm_prompt import _ctx_inside_rift_boss

    ctx = _ctx_inside_rift_boss()
    loc = dict(ctx["v2_initial_location"])  # type: ignore[arg-type]
    loc["rift_sub_area"] = "bc_ch1"  # ★ 진입 chamber, boss chamber X
    loc["rift_is_variant"] = True
    ctx["v2_initial_location"] = loc

    prompt = _gm_system_prompt(ctx)
    # boss chamber 도달 본격 X 본격 변종 chamber 메시지 본격 X
    assert "변종이 깨어났다" not in prompt
    assert "보스방 앞" not in prompt


# ─── Location.realm — Realm enum ───


def test_realm_rift_enum_value() -> None:
    """Realm.RIFT 본격 value 본격 (★ ctx 본격 정합)."""
    assert Realm.RIFT.value == "균열"


def test_location_default_rift_is_variant_false() -> None:
    """Location default 본격 rift_is_variant=False."""
    loc = Location(realm=Realm.DUNGEON)
    assert loc.rift_is_variant is False
    assert loc.rift_sub_area is None
