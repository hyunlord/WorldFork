"""Phase 9.12 reject-dialogue — 호감도 하락 본문 정합.

검증 본질:
- AFFINITY_DELTA_REJECTION = -10
- AFFINITY_MIN = 0 (★ floor — negative X)
- execute_reject_dialogue:
  * realm=CITY + sub_area NPC 본격 검증 (★ DIALOGUE 정합 구조)
  * target = NPC id 또는 한국어 name
  * 호감도 -10, floor 0
- PlayerActionType.REJECT_DIALOGUE enum
- gm_agent NPC hint: DIALOGUE +5 / REJECT_DIALOGUE -10 양방향 표시
- DIALOGUE + REJECT 대칭 net 검증

본문 정합:
- 303화: 답변 거절 → 호감도 하락 요인
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _format_city_context
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    AFFINITY_DELTA_DIALOGUE,
    AFFINITY_DELTA_REJECTION,
    AFFINITY_MIN,
    execute_dialogue,
    execute_reject_dialogue,
)
from service.sim.types import PlayerActionType

# ─── 1. constants ───


def test_rejection_delta_minus_10() -> None:
    assert AFFINITY_DELTA_REJECTION == -10


def test_affinity_min_is_zero() -> None:
    """floor 0 — negative 본격 X (★ 본인 답)."""
    assert AFFINITY_MIN == 0


# ─── 2. PlayerActionType ───


def test_reject_dialogue_enum_value() -> None:
    assert PlayerActionType.REJECT_DIALOGUE.value == "reject_dialogue"


def test_reject_dialogue_enum_present() -> None:
    """9.12 본격 enum 정합 (★ 전역 count는 test_state_v2_serialize 본격)."""
    assert PlayerActionType.REJECT_DIALOGUE in set(PlayerActionType)


# ─── 3. execute_reject_dialogue ───


def _plaza_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="district_7_plaza",
        city_id="rascania",
    )


def _dungeon_loc() -> Location:
    return Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")


def _actor() -> Character:
    return Character(
        name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100
    )


def test_reject_decreases_affinity_by_10() -> None:
    world = WorldState()
    world.npc_affinities["aenar"] = 50
    actor = _actor()
    result = execute_reject_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert result.success is True
    assert world.npc_affinities["aenar"] == 40


def test_reject_floor_at_zero() -> None:
    """current=5, delta=-10 → floor 0."""
    world = WorldState()
    world.npc_affinities["aenar"] = 5
    actor = _actor()
    execute_reject_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert world.npc_affinities["aenar"] == 0


def test_reject_no_negative_from_zero() -> None:
    world = WorldState()
    world.npc_affinities["aenar"] = 0
    actor = _actor()
    execute_reject_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert world.npc_affinities["aenar"] == 0


def test_reject_initial_default_zero() -> None:
    """호감도 dict X — default 0 → reject → 0 (★ floor)."""
    world = WorldState()
    actor = _actor()
    execute_reject_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert world.npc_affinities["aenar"] == 0


def test_reject_outside_city_fails() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_reject_dialogue(
        "비요른", "카이라", [actor], world, _dungeon_loc()
    )
    assert result.success is False


def test_reject_unknown_npc_fails() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_reject_dialogue(
        "비요른", "Nonexistent", [actor], world, _plaza_loc()
    )
    assert result.success is False


def test_reject_empty_target_fails() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_reject_dialogue(
        "비요른", "", [actor], world, _plaza_loc()
    )
    assert result.success is False


def test_reject_by_npc_id_works() -> None:
    """target = npc.id 본격 정합 (★ DIALOGUE 정합)."""
    world = WorldState()
    world.npc_affinities["aenar"] = 30
    actor = _actor()
    result = execute_reject_dialogue(
        "비요른", "aenar", [actor], world, _plaza_loc()
    )
    assert result.success is True
    assert world.npc_affinities["aenar"] == 20


def test_reject_actor_not_in_party_fails() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_reject_dialogue(
        "투르윈", "카이라", [actor], world, _plaza_loc()
    )
    assert result.success is False


def test_reject_side_effect_emitted() -> None:
    world = WorldState()
    world.npc_affinities["aenar"] = 50
    actor = _actor()
    result = execute_reject_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert any(
        s == "affinity_changed=aenar:50->40"
        for s in result.side_effects
    )


def test_reject_message_includes_npc_name() -> None:
    world = WorldState()
    actor = _actor()
    result = execute_reject_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert "카이라" in result.message
    assert "거절" in result.message


# ─── 4. DIALOGUE + REJECT 대칭 net ───


def test_dialogue_then_reject_net_minus_5() -> None:
    """DIALOGUE +5 → REJECT -10 = net -5 → floor 0."""
    world = WorldState()
    actor = _actor()
    execute_dialogue("비요른", "카이라", [actor], world, _plaza_loc())
    assert world.npc_affinities["aenar"] == AFFINITY_DELTA_DIALOGUE  # 5
    execute_reject_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    # 5 + (-10) = -5 → floor 0
    assert world.npc_affinities["aenar"] == 0


def test_dialogue_3x_then_reject_no_floor() -> None:
    """+5×3=15 → -10 → 5 (★ 본격 floor 본격 X)."""
    world = WorldState()
    actor = _actor()
    for _ in range(3):
        execute_dialogue(
            "비요른", "카이라", [actor], world, _plaza_loc()
        )
    assert world.npc_affinities["aenar"] == 15
    execute_reject_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert world.npc_affinities["aenar"] == 5


# ─── 5. gm_agent prompt hint ───


def _plaza_ctx() -> dict[str, Any]:
    return {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "district_7_plaza",
            "city_id": "rascania",
        }
    }


def test_prompt_shows_both_dialogue_and_reject_hint() -> None:
    out = _format_city_context(_plaza_ctx())
    assert "DIALOGUE 호감도 +5" in out
    assert "REJECT_DIALOGUE 호감도 -10" in out
