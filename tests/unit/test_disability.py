"""Phase 9.10 disability — 영구 disability + 회복 mechanism minimal unit.

검증 본질:
- Disability frozen dataclass (body_part / kind / hp_max_penalty)
- Character.disabilities default 빈 list
- Character.effective_hp_max property (★ HP_max - sum penalty, min 1)
- _maybe_create_disability:
  * CRITICAL only → Disability (★ scar = major+, disability = critical만)
  * body_part 본격 penalty mapping (★ head 20 / neck 25 / torso 20 / arm 10 / leg 15)
  * 미지 body_part → default 10
- WAIT_IN_VILLAGE: critical injury 회복 완료 → disability append
- HEAL_AT_TEMPLE:
  * disability 본격 정수 비용 (★ DISABILITY_HEAL_COST = 50000)
  * injury + disability 동시 처리 (★ Option A 본격)
  * atomic — 부족 시 mutation X
  * side_effects: disability_acquired / disability_healed_by_temple
- gm_agent prompt: 영구 손상 line + effective HP_max
- sim_runner _refresh_context: disabilities + effective_hp_max serialize

본문 정합:
- 71/214화: 절단 narrative (★ amputation default)
- 117/268화: 회복 path (★ 신성력 / 재생 스킬)
- 268화: critical heal cost (5000) × 10 → DISABILITY_HEAL_COST
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    Disability,
    Injury,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    DISABILITY_HEAL_COST,
    DISABILITY_HP_MAX_PENALTY_BY_PART,
    HEAL_COST_PER_SEVERITY,
    _maybe_create_disability,
    execute_heal_at_temple,
    execute_wait_in_village,
)
from service.sim.sim_runner import _refresh_context

# ─── 1. Disability dataclass ───


def test_disability_frozen() -> None:
    d = Disability(body_part="leg", kind="amputation", hp_max_penalty=15)
    try:
        d.body_part = "arm"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("Disability 본격 frozen 본격 X")


def test_disability_default_kind_amputation() -> None:
    d = Disability(body_part="arm")
    assert d.kind == "amputation"
    assert d.hp_max_penalty == 0


def test_disability_explicit_fields() -> None:
    d = Disability(body_part="neck", kind="amputation", hp_max_penalty=25)
    assert d.body_part == "neck"
    assert d.hp_max_penalty == 25


# ─── 2. Character.disabilities + effective_hp_max ───


def test_character_default_disabilities_empty() -> None:
    c = Character(name="Test", race=Race.HUMAN)
    assert c.disabilities == []


def test_effective_hp_max_no_disability_equals_hp_max() -> None:
    c = Character(name="Test", race=Race.HUMAN, hp_max=100)
    assert c.effective_hp_max == 100


def test_effective_hp_max_single_disability() -> None:
    c = Character(name="Test", race=Race.HUMAN, hp_max=100)
    c.disabilities.append(Disability(body_part="leg", hp_max_penalty=15))
    assert c.effective_hp_max == 85


def test_effective_hp_max_multiple_disabilities() -> None:
    c = Character(name="Test", race=Race.HUMAN, hp_max=100)
    c.disabilities.append(Disability(body_part="leg", hp_max_penalty=15))
    c.disabilities.append(Disability(body_part="arm", hp_max_penalty=10))
    assert c.effective_hp_max == 75


def test_effective_hp_max_min_1_when_penalty_exceeds() -> None:
    """penalty > hp_max → 1 (★ floor)."""
    c = Character(name="Test", race=Race.HUMAN, hp_max=20)
    c.disabilities.append(Disability(body_part="neck", hp_max_penalty=100))
    assert c.effective_hp_max == 1


# ─── 3. _maybe_create_disability ───


def test_maybe_disability_critical_leg() -> None:
    inj = Injury(severity="critical", body_part="leg", recovery_days=60)
    d = _maybe_create_disability(inj)
    assert d is not None
    assert d.body_part == "leg"
    assert d.kind == "amputation"
    assert d.hp_max_penalty == DISABILITY_HP_MAX_PENALTY_BY_PART["leg"]


def test_maybe_disability_critical_neck_highest_penalty() -> None:
    """neck = 25 (★ 본인 답 — 가장 큰 penalty)."""
    inj = Injury(severity="critical", body_part="neck", recovery_days=60)
    d = _maybe_create_disability(inj)
    assert d is not None
    assert d.hp_max_penalty == 25


def test_maybe_disability_major_returns_none() -> None:
    """major 본격 disability X (★ scar 본격, 9.6 본격)."""
    inj = Injury(severity="major", body_part="leg", recovery_days=21)
    assert _maybe_create_disability(inj) is None


def test_maybe_disability_minor_returns_none() -> None:
    inj = Injury(severity="minor", body_part="arm", recovery_days=7)
    assert _maybe_create_disability(inj) is None


def test_maybe_disability_unknown_body_part_default_10() -> None:
    inj = Injury(severity="critical", body_part="finger", recovery_days=60)
    d = _maybe_create_disability(inj)
    assert d is not None
    assert d.hp_max_penalty == 10


# ─── 4. WAIT_IN_VILLAGE — critical → disability transition ───


def _village_world() -> WorldState:
    w = WorldState()
    w.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    return w


def test_wait_critical_recovery_acquires_disability() -> None:
    world = _village_world()
    actor = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=80,
        hp_max=100,
    )
    actor.injuries.append(
        Injury(severity="critical", body_part="leg", recovery_days=1, scar=True)
    )
    result = execute_wait_in_village("비요른", [actor], world)
    assert result.success is True
    assert len(actor.injuries) == 0
    assert len(actor.disabilities) == 1
    assert actor.disabilities[0].body_part == "leg"
    assert actor.disabilities[0].kind == "amputation"
    # ★ effective HP_max 본격 감소
    assert actor.effective_hp_max == 100 - 15


def test_wait_major_recovery_no_disability_scar_only() -> None:
    """major → scar (9.6) only, disability X."""
    world = _village_world()
    actor = Character(name="비요른", race=Race.BARBARIAN, hp=80, hp_max=100)
    actor.injuries.append(
        Injury(severity="major", body_part="arm", recovery_days=1, scar=True)
    )
    execute_wait_in_village("비요른", [actor], world)
    assert len(actor.disabilities) == 0
    assert len(actor.scars) == 1


def test_wait_disability_side_effect_emitted() -> None:
    world = _village_world()
    actor = Character(name="비요른", race=Race.BARBARIAN, hp=80, hp_max=100)
    actor.injuries.append(
        Injury(severity="critical", body_part="arm", recovery_days=1, scar=True)
    )
    result = execute_wait_in_village("비요른", [actor], world)
    assert any(
        s.startswith("disability_acquired=비요른:arm_amputation")
        for s in result.side_effects
    )


# ─── 5. HEAL_AT_TEMPLE — critical→disability + disability heal ───


def _temple_loc(sub_area: str = "reatlas_temple") -> Location:
    return Location(
        realm=Realm.CITY, floor=0, sub_area=sub_area, city_id="rapdonia"
    )


def test_temple_heal_critical_acquires_disability() -> None:
    """temple heal 본격 critical injury 본격 disability transition."""
    world = WorldState()
    actor = Character(
        name="비요른", race=Race.BARBARIAN, hp=50, hp_max=100, stone=10000
    )
    actor.injuries.append(
        Injury(severity="critical", body_part="leg", recovery_days=60, scar=True)
    )
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("reatlas_temple")
    )
    assert result.success is True
    # critical injury cost 차감 (5000)
    assert actor.stone == 10000 - HEAL_COST_PER_SEVERITY["critical"]
    # injury 사라지고 disability 본격 남음 (★ transition)
    assert len(actor.injuries) == 0
    assert len(actor.disabilities) == 1
    assert actor.disabilities[0].body_part == "leg"
    # message + side_effect 검증
    assert "영구 손상" in result.message
    assert any(
        "disability_acquired=비요른:leg_amputation" == s
        for s in result.side_effects
    )


def test_temple_heal_existing_disability_costs_50000() -> None:
    """기존 disability 본격 temple heal cost = DISABILITY_HEAL_COST."""
    world = WorldState()
    actor = Character(
        name="비요른", race=Race.BARBARIAN, hp=50, hp_max=100, stone=100000
    )
    actor.disabilities.append(
        Disability(body_part="leg", hp_max_penalty=15)
    )
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("reatlas_temple")
    )
    assert result.success is True
    assert actor.stone == 100000 - DISABILITY_HEAL_COST
    assert len(actor.disabilities) == 0
    assert actor.effective_hp_max == 100  # ★ penalty 해제
    assert any(
        "disability_healed_by_temple=비요른:leg_amputation" == s
        for s in result.side_effects
    )


def test_temple_heal_no_injury_no_disability_fails() -> None:
    world = WorldState()
    actor = Character(
        name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, stone=100000
    )
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("reatlas_temple")
    )
    assert result.success is False


def test_temple_heal_insufficient_stone_atomic() -> None:
    """비용 부족 → fail + 본 mutation X (★ atomic)."""
    world = WorldState()
    actor = Character(
        name="비요른", race=Race.BARBARIAN, hp=50, hp_max=100, stone=100
    )
    actor.disabilities.append(
        Disability(body_part="leg", hp_max_penalty=15)
    )
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("reatlas_temple")
    )
    assert result.success is False
    assert actor.stone == 100
    assert len(actor.disabilities) == 1


def test_temple_heal_injury_plus_disability_combined_cost() -> None:
    """injury + disability 동시 → 합산 비용 (★ Option A)."""
    world = WorldState()
    actor = Character(
        name="비요른", race=Race.BARBARIAN, hp=50, hp_max=100, stone=100000
    )
    actor.injuries.append(
        Injury(severity="minor", body_part="arm", recovery_days=7)
    )
    actor.disabilities.append(
        Disability(body_part="leg", hp_max_penalty=15)
    )
    result = execute_heal_at_temple(
        "비요른", [actor], world, _temple_loc("reatlas_temple")
    )
    assert result.success is True
    expected = HEAL_COST_PER_SEVERITY["minor"] + DISABILITY_HEAL_COST
    assert actor.stone == 100000 - expected
    assert len(actor.injuries) == 0
    assert len(actor.disabilities) == 0
    assert "부상" in result.message
    assert "영구 손상" in result.message


# ─── 6. gm_agent prompt 본격 disability render ───


def _base_ctx() -> dict[str, Any]:
    return {
        "work_name": "1층 시뮬",
        "work_genre": "판타지",
        "world_setting": "라스카니아",
        "world_tone": "차분",
        "world_rules": ["1층 어둠"],
        "main_character_name": "비요른",
        "main_character_role": "주인공",
        "supporting_characters": [],
        "current_location": "라프도니아",
        "current_turn": 0,
    }


def _ctx_with_disabilities(
    disabilities: list[dict[str, Any]], effective_hp_max: int = 100
) -> dict[str, Any]:
    ctx = _base_ctx()
    ctx["v2_characters"] = {
        "비요른": {
            "race": "바바리안",
            "hp": 100,
            "hp_max": 100,
            "level": 1,
            "experience": 0,
            "physical": 14,
            "strength": 16,
            "grade": 1,
            "class_type": "warrior",
            "disabilities": disabilities,
            "effective_hp_max": effective_hp_max,
        },
    }
    return ctx


def test_prompt_no_disability_no_render() -> None:
    prompt = _gm_system_prompt(_ctx_with_disabilities([], 100))
    assert "영구 손상" not in prompt
    assert "실효 HP_max" not in prompt


def test_prompt_disability_line_rendered() -> None:
    prompt = _gm_system_prompt(
        _ctx_with_disabilities(
            [
                {
                    "body_part": "leg",
                    "kind": "amputation",
                    "hp_max_penalty": 15,
                }
            ],
            85,
        )
    )
    assert "영구 손상: leg amputation" in prompt
    assert "HP_max -15" in prompt
    assert "실효 HP_max: 85" in prompt


# ─── 7. sim_runner ctx serialize ───


def _make_party_world() -> tuple[dict[str, Character], WorldState, Location]:
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=100,
            hp_max=100,
        ),
    }
    world = WorldState(party_members=["비요른"])
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")
    return party, world, loc


def test_refresh_context_no_disabilities_empty_list() -> None:
    party, world, loc = _make_party_world()
    ctx = _refresh_context(party, world, loc, _base_ctx(), [])
    assert ctx["v2_characters"]["비요른"]["disabilities"] == []
    assert ctx["v2_characters"]["비요른"]["effective_hp_max"] == 100


def test_refresh_context_serializes_disabilities() -> None:
    party, world, loc = _make_party_world()
    party["비요른"].disabilities.append(
        Disability(body_part="leg", kind="amputation", hp_max_penalty=15)
    )
    ctx = _refresh_context(party, world, loc, _base_ctx(), [])
    disabilities = ctx["v2_characters"]["비요른"]["disabilities"]
    assert len(disabilities) == 1
    assert disabilities[0] == {
        "body_part": "leg",
        "kind": "amputation",
        "hp_max_penalty": 15,
    }
    assert ctx["v2_characters"]["비요른"]["effective_hp_max"] == 85
