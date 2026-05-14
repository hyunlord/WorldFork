"""Phase 9 gm-injury-prompt — gm_agent prompt 본격 injury summary 본격 unit.

검증 본질:
- v2_characters[name]["injuries"] 본격 prompt 본격 본격
- body_part / severity / recovery_days 표시
- scar=True → '(흉터 예정)' marker
- empty injuries → section 본격 X
- multiple injuries 본격 본격 line
- sim_runner._refresh_context 본격 injuries serialize 본격

본 commit 본격 wire:
- sim_runner.py _refresh_context: chars_ctx[name]["injuries"] = [...]
- gm_agent.py v2_chars loop: injuries 본격 sub-line append
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    Injury,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.sim_runner import _refresh_context


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


def _make_party_world() -> tuple[
    dict[str, Character], WorldState, Location
]:
    party = {
        "비요른": Character(
            name="비요른",
            race=Race.BARBARIAN,
            hp=100,
            hp_max=100,
            is_player=True,
        ),
    }
    world = WorldState(party_members=["비요른"])
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")
    return party, world, loc


# ─── 1. _refresh_context 본격 injuries serialize ───


def test_refresh_context_no_injuries_empty_list() -> None:
    party, world, loc = _make_party_world()
    ctx = _refresh_context(party, world, loc, _base_ctx(), [])
    assert ctx["v2_characters"]["비요른"]["injuries"] == []


def test_refresh_context_serializes_injuries() -> None:
    party, world, loc = _make_party_world()
    party["비요른"].injuries.append(
        Injury(severity="scratch", body_part="arm", recovery_days=2)
    )
    ctx = _refresh_context(party, world, loc, _base_ctx(), [])
    injs = ctx["v2_characters"]["비요른"]["injuries"]
    assert len(injs) == 1
    assert injs[0] == {
        "severity": "scratch",
        "body_part": "arm",
        "recovery_days": 2,
        "scar": False,
    }


def test_refresh_context_serializes_scar() -> None:
    party, world, loc = _make_party_world()
    party["비요른"].injuries.append(
        Injury(
            severity="major",
            body_part="neck",
            recovery_days=20,
            scar=True,
        )
    )
    ctx = _refresh_context(party, world, loc, _base_ctx(), [])
    inj = ctx["v2_characters"]["비요른"]["injuries"][0]
    assert inj["scar"] is True


# ─── 2. gm_agent prompt rendering ───


def _ctx_with_char(injuries: list[dict[str, Any]]) -> dict[str, Any]:
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
            "injuries": injuries,
        },
    }
    return ctx


def test_no_injuries_omits_section() -> None:
    """injuries=[] 본격 prompt 본격 '부상' marker X."""
    prompt = _gm_system_prompt(_ctx_with_char([]))
    assert "└ 부상:" not in prompt


def test_scratch_renders_body_part_severity_days() -> None:
    """scratch 본격 본격 본격 출력."""
    injuries = [
        {
            "severity": "scratch",
            "body_part": "arm",
            "recovery_days": 2,
            "scar": False,
        }
    ]
    prompt = _gm_system_prompt(_ctx_with_char(injuries))
    assert "└ 부상: arm scratch" in prompt
    assert "회복 2일 남음" in prompt


def test_no_scar_no_marker() -> None:
    injuries = [
        {
            "severity": "scratch",
            "body_part": "arm",
            "recovery_days": 2,
            "scar": False,
        }
    ]
    prompt = _gm_system_prompt(_ctx_with_char(injuries))
    assert "흉터 예정" not in prompt


def test_major_with_scar_renders_marker() -> None:
    """25화 본문 정합 (★ scar=True → '흉터 예정' marker)."""
    injuries = [
        {
            "severity": "major",
            "body_part": "neck",
            "recovery_days": 18,
            "scar": True,
        }
    ]
    prompt = _gm_system_prompt(_ctx_with_char(injuries))
    assert "└ 부상: neck major" in prompt
    assert "회복 18일 남음" in prompt
    assert "(흉터 예정)" in prompt


def test_multiple_injuries_each_line() -> None:
    """다수 injury 본격 본격 line."""
    injuries = [
        {
            "severity": "scratch",
            "body_part": "arm",
            "recovery_days": 1,
            "scar": False,
        },
        {
            "severity": "major",
            "body_part": "leg",
            "recovery_days": 15,
            "scar": True,
        },
    ]
    prompt = _gm_system_prompt(_ctx_with_char(injuries))
    assert "arm scratch" in prompt
    assert "leg major" in prompt
    # 2개 모두 sub-line 본격
    injury_lines = [
        ln for ln in prompt.splitlines() if "└ 부상:" in ln
    ]
    assert len(injury_lines) == 2


def test_missing_injuries_key_omits_section() -> None:
    """ctx 본격 injuries key 본격 X 본격 (★ backward compat)."""
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
            # ★ injuries key 본격 X
        },
    }
    prompt = _gm_system_prompt(ctx)
    assert "└ 부상:" not in prompt
