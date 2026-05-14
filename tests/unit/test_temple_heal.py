"""Phase 9.5 temple-heal — 삼신교 + HEAL_AT_TEMPLE 본격 unit.

검증 본질:
- TempleDeity 3 instance (★ 토베라/레아틀라스/카루이)
- 268화 본문 정합: 토베라 바바리안 거절 ⭐
- 55화: 레아틀라스 선 성향
- 72화: 카루이 사제 엘리사
- get_deity_by_sub_area lookup
- RAPDONIA 12 sub_areas + 12 NPCs
- execute_heal_at_temple:
  * 위치 검증 (★ realm=CITY + sub_area=temple)
  * race 거절 (★ 268화 바바리안-토베라)
  * 부상 X / 비용 부족 fail
  * batch 치료 + stone 차감
  * atomic mutation (★ fail 시 변경 X)
- gm_agent _format_city_context temple hint
"""

from __future__ import annotations

from typing import Any

from service.game.cities.rapdonia import RAPDONIA_SUB_AREAS
from service.game.cities.temples import (
    KARUYI,
    REATLAS,
    TOBERAH,
    get_deity_by_sub_area,
)
from service.game.gm_agent import _format_city_context
from service.game.state_v2 import (
    Character,
    Injury,
    Location,
    Race,
    Realm,
    SimulationStatus,
    WorldState,
)
from service.game.turn_handler_v2 import (
    HEAL_COST_PER_SEVERITY,
    execute_heal_at_temple,
)

# ─── 1. TempleDeity instances ───


def test_toberah_refuses_barbarian_268hwa() -> None:
    """268화 본문 정합 — 토베라 바바리안 거절 규율 ⭐."""
    assert "바바리안" in TOBERAH.refuses_races
    assert TOBERAH.canonical_priest_name == "라이린 에르시나"
    assert TOBERAH.priest_rank == "정사제"


def test_reatlas_nature_good_55hwa() -> None:
    """55화: 레아틀라스 — 선 성향, 탐험의 신."""
    assert REATLAS.nature == "선"
    assert REATLAS.refuses_races == ()
    # 본문 X — placeholder
    assert REATLAS.canonical_priest_name == ""


def test_karuyi_priest_elisa_72hwa() -> None:
    """72화 본문 정합 — 카루이 사제 엘리사."""
    assert KARUYI.canonical_priest_name == "엘리사"
    assert KARUYI.refuses_races == ()


def test_deity_ids_unique() -> None:
    ids = [TOBERAH.deity_id, REATLAS.deity_id, KARUYI.deity_id]
    assert len(set(ids)) == len(ids)


# ─── 2. get_deity_by_sub_area ───


def test_lookup_toberah() -> None:
    assert get_deity_by_sub_area("toberah_temple") is TOBERAH


def test_lookup_reatlas() -> None:
    assert get_deity_by_sub_area("reatlas_temple") is REATLAS


def test_lookup_karuyi() -> None:
    assert get_deity_by_sub_area("karuyi_temple") is KARUYI


def test_lookup_unknown_none() -> None:
    assert get_deity_by_sub_area("nonexistent") is None


def test_lookup_non_temple_none() -> None:
    assert get_deity_by_sub_area("district_7_plaza") is None


# ─── 3. RAPDONIA structure (★ cascade regression) ───


def test_rapdonia_12_sub_areas() -> None:
    """9 본격 + 3 temple (★ Phase 9.5)."""
    assert len(RAPDONIA_SUB_AREAS) == 12


def test_temple_sub_areas_registered() -> None:
    ids = {s.id for s in RAPDONIA_SUB_AREAS}
    assert "toberah_temple" in ids
    assert "reatlas_temple" in ids
    assert "karuyi_temple" in ids


def test_plaza_connects_to_three_temples() -> None:
    plaza = next(
        s for s in RAPDONIA_SUB_AREAS if s.id == "district_7_plaza"
    )
    assert "toberah_temple" in plaza.connections
    assert "reatlas_temple" in plaza.connections
    assert "karuyi_temple" in plaza.connections


def test_temples_connect_back_to_plaza() -> None:
    """bidirectional 일관성."""
    for tid in ("toberah_temple", "reatlas_temple", "karuyi_temple"):
        sub = next(s for s in RAPDONIA_SUB_AREAS if s.id == tid)
        assert "district_7_plaza" in sub.connections


# ─── 4. execute_heal_at_temple ───


def _temple_loc(sub_area: str = "reatlas_temple") -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area=sub_area,
        city_id="rapdonia",
    )


def _floor1_loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


def _bjorn_with_injury(stone: int = 10000) -> Character:
    c = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=80,
        hp_max=100,
        stone=stone,
    )
    c.injuries.append(
        Injury(severity="minor", body_part="arm", recovery_days=5)
    )
    return c


def _village_world() -> WorldState:
    w = WorldState()
    w.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
    return w


def test_outside_city_fails() -> None:
    world = _village_world()
    actor = _bjorn_with_injury()
    result = execute_heal_at_temple(
        "비요른", [actor], world, _floor1_loc()
    )
    assert result.success is False


def test_non_temple_sub_area_fails() -> None:
    world = _village_world()
    actor = _bjorn_with_injury()
    loc = _temple_loc("district_7_plaza")
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is False


def test_barbarian_refused_at_toberah_268hwa() -> None:
    """268화 본문 정합 — 토베라 바바리안 거절 + 정사제 라이린 본격 message ⭐."""
    world = _village_world()
    actor = _bjorn_with_injury()
    pre_stone = actor.stone
    loc = _temple_loc("toberah_temple")
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is False
    assert "토베라" in result.message
    assert "바바리안" in result.message
    # ★ canonical_priest_name + priest_rank + temple_name wire 검증
    assert "라이린 에르시나" in result.message
    assert "정사제" in result.message
    assert "토베라 신전" in result.message
    # mutation X
    assert actor.stone == pre_stone
    assert len(actor.injuries) == 1


def test_barbarian_accepted_at_reatlas() -> None:
    """레아틀라스 본격 거절 X — 바바리안 본격 본격."""
    world = _village_world()
    actor = _bjorn_with_injury()
    loc = _temple_loc("reatlas_temple")
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is True
    assert len(actor.injuries) == 0
    assert actor.stone == 10000 - HEAL_COST_PER_SEVERITY["minor"]


def test_barbarian_accepted_at_karuyi() -> None:
    """카루이 본격 거절 X — 바바리안 본격 본격."""
    world = _village_world()
    actor = _bjorn_with_injury()
    loc = _temple_loc("karuyi_temple")
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is True
    assert len(actor.injuries) == 0


def test_no_injuries_fails() -> None:
    world = _village_world()
    actor = Character(
        name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, stone=10000
    )
    loc = _temple_loc("reatlas_temple")
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is False


def test_insufficient_stone_fails_atomic() -> None:
    """비용 부족 → fail + mutation X (★ atomic)."""
    world = _village_world()
    actor = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=80,
        hp_max=100,
        stone=10,
    )
    actor.injuries.append(
        Injury(severity="major", body_part="neck", recovery_days=20)
    )
    loc = _temple_loc("reatlas_temple")
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is False
    assert "비용" in result.message
    # atomic — mutation X
    assert len(actor.injuries) == 1
    assert actor.stone == 10


def test_batch_multiple_injuries_total_cost() -> None:
    """다수 injury → batch 치료 + 총 비용 차감."""
    world = _village_world()
    actor = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=70,
        hp_max=100,
        stone=10000,
    )
    actor.injuries.append(
        Injury(severity="scratch", body_part="arm", recovery_days=1)
    )
    actor.injuries.append(
        Injury(severity="major", body_part="leg", recovery_days=15)
    )
    loc = _temple_loc("karuyi_temple")
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is True
    expected = (
        HEAL_COST_PER_SEVERITY["scratch"]
        + HEAL_COST_PER_SEVERITY["major"]
    )
    assert actor.stone == 10000 - expected
    assert len(actor.injuries) == 0


def test_side_effects_emitted() -> None:
    world = _village_world()
    actor = _bjorn_with_injury()
    loc = _temple_loc("reatlas_temple")
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    # ★ deity_id wire 검증 (★ reatlas)
    assert any(
        s == "temple_healed=비요른:reatlas:1" for s in result.side_effects
    )
    assert any(
        s.startswith("stone_paid=비요른:") for s in result.side_effects
    )
    assert any(
        "injury_healed_by_temple=비요른:arm_minor" == s
        for s in result.side_effects
    )


def test_success_message_includes_temple_name_and_rank() -> None:
    """temple_name + priest_rank wire 검증 (★ 성공 message)."""
    world = _village_world()
    actor = _bjorn_with_injury()
    loc = _temple_loc("karuyi_temple")
    result = execute_heal_at_temple("비요른", [actor], world, loc)
    assert result.success is True
    assert "카루이 신전" in result.message
    assert "사제" in result.message


def test_actor_not_in_party_fails() -> None:
    world = _village_world()
    actor = _bjorn_with_injury()
    loc = _temple_loc("reatlas_temple")
    result = execute_heal_at_temple("투르윈", [actor], world, loc)
    assert result.success is False


# ─── 5. gm_agent _format_city_context temple hint ───


def _base_ctx(sub_area: str) -> dict[str, Any]:
    return {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": sub_area,
            "city_id": "rapdonia",
        }
    }


def test_prompt_reatlas_shows_heal_hint() -> None:
    out = _format_city_context(_base_ctx("reatlas_temple"))
    assert "HEAL_AT_TEMPLE" in out


def test_prompt_toberah_shows_barbarian_refused() -> None:
    """268화 정합 — toberah_temple prompt 본격 바바리안 거절 명시."""
    out = _format_city_context(_base_ctx("toberah_temple"))
    assert "HEAL_AT_TEMPLE" in out
    assert "바바리안" in out
    assert "거절" in out


def test_prompt_non_temple_no_heal_hint() -> None:
    out = _format_city_context(_base_ctx("district_7_plaza"))
    assert "HEAL_AT_TEMPLE" not in out


def test_prompt_reatlas_shows_nature_good_55hwa() -> None:
    """55화 정합 — 레아틀라스 prompt 본격 '선' 성향 표시."""
    out = _format_city_context(_base_ctx("reatlas_temple"))
    assert "레아틀라스 신전" in out
    assert "성향: 선" in out


def test_prompt_toberah_shows_priest_rairin_268hwa() -> None:
    """268화 정합 — 토베라 prompt 본격 정사제 라이린 표시."""
    out = _format_city_context(_base_ctx("toberah_temple"))
    assert "정사제 라이린 에르시나" in out


def test_prompt_karuyi_shows_priest_elisa_72hwa() -> None:
    """72화 정합 — 카루이 prompt 본격 사제 엘리사 표시."""
    out = _format_city_context(_base_ctx("karuyi_temple"))
    assert "사제 엘리사" in out


def test_prompt_reatlas_priest_placeholder_omitted() -> None:
    """레아틀라스 사제 본문 X (★ placeholder) → 사제 line 본격 X."""
    out = _format_city_context(_base_ctx("reatlas_temple"))
    # canonical_priest_name="" 본격 본격 line append X
    assert "사제: " not in out
