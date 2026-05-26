"""Phase 9.6 scar-permanent — 영구 흉터 schema + transition wire 본격 unit.

검증 본질:
- Scar frozen dataclass (★ body_part / origin_severity)
- Character.scars default empty
- execute_wait_in_village:
  * scar=True injury 회복 → Scar 누적 + side_effect
  * scar=False injury → 흉터 X
  * 다수 injury 본격 본격 본격
- execute_heal_at_temple:
  * scar=True injury → Scar 누적
  * message 본격 흉터 표시
  * scar=False → 흉터 X
- _refresh_context: chars_ctx[name]['scars'] serialize
- gm_agent prompt: '영구 흉터' sub-line render

본문 정합:
- 25화: '흉터가 남겠군' (★ major+ 영구 흉터)
- 본 commit: cosmetic only (★ HP_max 영향 X)
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    Injury,
    Location,
    Race,
    Realm,
    Scar,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    execute_heal_at_temple,
    execute_wait_in_village,
)
from service.sim.sim_runner import _refresh_context

# ─── 1. Scar dataclass ───


def test_scar_create() -> None:
    s = Scar(body_part="neck", origin_severity="major")
    assert s.body_part == "neck"
    assert s.origin_severity == "major"


def test_scar_frozen() -> None:
    s = Scar(body_part="arm", origin_severity="critical")
    with pytest.raises(FrozenInstanceError):
        s.body_part = "leg"  # type: ignore[misc]


# ─── 2. Character.scars ───


def test_character_scars_default_empty() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    assert c.scars == []


def test_character_scars_append() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    c.scars.append(Scar(body_part="neck", origin_severity="major"))
    assert len(c.scars) == 1


# ─── 3. WAIT scar transition ───


def _village_world() -> WorldState:
    w = WorldState()
    w.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    return w


def _actor() -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=80,
        hp_max=100,
    )


def test_wait_major_scar_transition_25hwa() -> None:
    """25화 본문 정합 — major + scar=True 회복 시 영구 흉터 ⭐."""
    world = _village_world()
    actor = _actor()
    actor.injuries.append(
        Injury(
            severity="major",
            body_part="neck",
            recovery_days=1,
            scar=True,
        )
    )
    result = execute_wait_in_village("비요른", [actor], world)
    assert len(actor.injuries) == 0
    assert len(actor.scars) == 1
    assert actor.scars[0].body_part == "neck"
    assert actor.scars[0].origin_severity == "major"
    assert any(
        "scar_acquired=비요른:neck_major" == s
        for s in result.side_effects
    )


def test_wait_scratch_no_scar() -> None:
    """scratch + scar=False 회복 → 흉터 X."""
    world = _village_world()
    actor = _actor()
    actor.injuries.append(
        Injury(
            severity="scratch",
            body_part="arm",
            recovery_days=1,
            scar=False,
        )
    )
    execute_wait_in_village("비요른", [actor], world)
    assert len(actor.injuries) == 0
    assert len(actor.scars) == 0


def test_wait_partial_recovery_no_scar_yet() -> None:
    """recovery_days>0 → 흉터 transition X (★ 회복 미완)."""
    world = _village_world()
    actor = _actor()
    actor.injuries.append(
        Injury(
            severity="major",
            body_part="neck",
            recovery_days=5,
            scar=True,
        )
    )
    execute_wait_in_village("비요른", [actor], world)
    # 4일 남음 + 흉터 X (★ 회복 본격 본격)
    assert len(actor.injuries) == 1
    assert actor.injuries[0].recovery_days == 4
    assert len(actor.scars) == 0


def test_wait_mixed_injuries_partial_scars() -> None:
    """scratch healed (no scar) + major healed (scar) 동시."""
    world = _village_world()
    actor = _actor()
    actor.injuries.append(
        Injury(
            severity="scratch", body_part="arm", recovery_days=1, scar=False
        )
    )
    actor.injuries.append(
        Injury(
            severity="major", body_part="neck", recovery_days=1, scar=True
        )
    )
    execute_wait_in_village("비요른", [actor], world)
    assert len(actor.injuries) == 0
    assert len(actor.scars) == 1  # ★ scratch X, major O
    assert actor.scars[0].body_part == "neck"


def test_wait_scar_accumulates() -> None:
    """기존 scars + 신규 scar 누적."""
    world = _village_world()
    actor = _actor()
    actor.scars.append(
        Scar(body_part="arm", origin_severity="critical")
    )
    actor.injuries.append(
        Injury(
            severity="major", body_part="neck", recovery_days=1, scar=True
        )
    )
    execute_wait_in_village("비요른", [actor], world)
    assert len(actor.scars) == 2  # ★ 기존 1 + 신규 1


# ─── 4. temple heal scar transition ───


def _temple_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="reatlas_temple",
        city_id="rascania",
    )


def test_temple_heal_major_scar_transition() -> None:
    """temple heal 본격 scar=True → 영구 흉터."""
    world = _village_world()
    actor = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=80,
        hp_max=100,
        stone=10000,
    )
    actor.injuries.append(
        Injury(
            severity="major",
            body_part="neck",
            recovery_days=20,
            scar=True,
        )
    )
    loc = _temple_loc()
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is True
    assert len(actor.injuries) == 0
    assert len(actor.scars) == 1
    assert actor.scars[0].body_part == "neck"
    assert actor.scars[0].origin_severity == "major"
    assert "흉터" in result.message
    assert any(
        "scar_acquired=비요른:neck_major" == s
        for s in result.side_effects
    )


def test_temple_heal_scratch_no_scar() -> None:
    """temple heal scratch (★ scar=False) → 흉터 X."""
    world = _village_world()
    actor = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=90,
        hp_max=100,
        stone=10000,
    )
    actor.injuries.append(
        Injury(
            severity="scratch",
            body_part="arm",
            recovery_days=2,
            scar=False,
        )
    )
    loc = _temple_loc()
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is True
    assert len(actor.scars) == 0
    assert "흉터" not in result.message


def test_temple_heal_message_no_scar_marker_when_none() -> None:
    """흉터 X 시 message 본격 흉터 marker 본격 X."""
    world = _village_world()
    actor = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=90,
        hp_max=100,
        stone=10000,
    )
    actor.injuries.append(
        Injury(
            severity="minor",
            body_part="leg",
            recovery_days=5,
            scar=False,
        )
    )
    loc = _temple_loc()
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is True
    assert "흉터" not in result.message


# ─── 5. sim_runner ctx serialize ───


def _make_party_world() -> tuple[
    dict[str, Character], WorldState, Location
]:
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


def _base_ctx() -> dict[str, Any]:
    return {
        "work_name": "1층 시뮬",
        "work_genre": "판타지",
        "world_setting": "라스카니아 라프도니아",
        "world_tone": "차분/생존",
        "world_rules": ["1층 어둠 본격"],
        "main_character_name": "비요른",
        "main_character_role": "주인공",
        "supporting_characters": [],
        "current_location": "1층 진입점",
        "current_turn": 0,
    }


def test_refresh_context_no_scars_empty_list() -> None:
    party, world, loc = _make_party_world()
    ctx = _refresh_context(party, world, loc, _base_ctx(), [])
    assert ctx["v2_characters"]["비요른"]["scars"] == []


def test_refresh_context_serializes_scars() -> None:
    party, world, loc = _make_party_world()
    party["비요른"].scars.append(
        Scar(body_part="neck", origin_severity="major")
    )
    ctx = _refresh_context(party, world, loc, _base_ctx(), [])
    scars = ctx["v2_characters"]["비요른"]["scars"]
    assert len(scars) == 1
    assert scars[0] == {
        "body_part": "neck",
        "origin_severity": "major",
    }


# ─── 6. gm_agent prompt 본격 흉터 render ───


def _ctx_with_char(scars: list[dict[str, Any]]) -> dict[str, Any]:
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
            "injuries": [],
            "scars": scars,
        },
    }
    return ctx


def test_prompt_no_scars_omits_section() -> None:
    prompt = _gm_system_prompt(_ctx_with_char([]))
    assert "└ 영구 흉터:" not in prompt


def test_prompt_scar_renders() -> None:
    scars = [{"body_part": "neck", "origin_severity": "major"}]
    prompt = _gm_system_prompt(_ctx_with_char(scars))
    assert "└ 영구 흉터: neck" in prompt
    assert "major 흔적" in prompt


def test_prompt_multiple_scars() -> None:
    scars = [
        {"body_part": "neck", "origin_severity": "major"},
        {"body_part": "arm", "origin_severity": "critical"},
    ]
    prompt = _gm_system_prompt(_ctx_with_char(scars))
    assert "neck" in prompt
    assert "arm" in prompt
    assert "major 흔적" in prompt
    assert "critical 흔적" in prompt
    scar_lines = [
        ln for ln in prompt.splitlines() if "└ 영구 흉터:" in ln
    ]
    assert len(scar_lines) == 2
