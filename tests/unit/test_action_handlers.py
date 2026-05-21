"""Phase D step 3 — deterministic action handler unit tests.

pytest-asyncio 미설치 (외부 패키지 0건 streak) → asyncio.run() 사용.
LLM 호출 없음 — handlers는 template narrative + state mutate.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from service.sim.action_context import ActionContext, ActionResult
from service.sim.action_handlers import (
    ACTION_HANDLERS,
    dispatch_action,
    handle_absorb_essence,
    handle_activate_light,
    handle_attack,
    handle_communicate,
    handle_dialogue,
    handle_disband_night_companion,
    handle_engage_bandit,
    handle_enter_dungeon,
    handle_enter_next_floor,
    handle_enter_rift,
    handle_exchange_mage_stones,
    handle_exit_rift,
    handle_exit_to_prev_floor,
    handle_explore,
    handle_flee,
    handle_form_night_companion,
    handle_heal_at_temple,
    handle_library_search,
    handle_move,
    handle_offer_to_stone,
    handle_recruit_from_guild,
    handle_reject_dialogue,
    handle_rest,
    handle_rest_and_night_watch,
    handle_shop_buy,
    handle_shop_sell,
    handle_use_item,
    handle_wait,
    handle_wait_in_village,
)
from service.sim.types import PlayerActionType


def _ctx(**kwargs: object) -> ActionContext:
    defaults: dict[str, object] = {
        "current_hp": 80,
        "max_hp": 100,
        "inventory": [],
        "location": "1층 A구역",
        "encounters": [],
        "user_input": "",
    }
    defaults.update(kwargs)
    return ActionContext(**defaults)  # type: ignore[arg-type]


def run(coro: Coroutine[Any, Any, ActionResult]) -> ActionResult:
    return asyncio.run(coro)


# ─── 핸들러 수 검증 ───


def test_handler_count() -> None:
    assert len(ACTION_HANDLERS) == 33


def test_all_player_action_types_covered() -> None:
    missing = [t for t in PlayerActionType if t not in ACTION_HANDLERS]
    assert missing == [], f"핸들러 미등록: {missing}"


# ─── ACTIVATE_LIGHT ───


def test_activate_light_success() -> None:
    ctx = _ctx(inventory=["횃불"])
    result = run(handle_activate_light(ctx))
    assert result.success
    assert result.time_advance == 0
    assert "횃불" in result.narrative or "불" in result.narrative


def test_activate_light_no_torch() -> None:
    ctx = _ctx(inventory=[])
    result = run(handle_activate_light(ctx))
    assert not result.success
    assert result.fail_reason == "no_torch"
    assert result.time_advance == 0


# ─── MOVE ───


def test_move_north() -> None:
    ctx = _ctx(user_input="북쪽으로 이동한다", location="1층 중심부", floor_number=1)
    result = run(handle_move(ctx))
    assert result.success
    assert result.location is not None
    assert "북쪽" in result.location
    assert result.time_advance == 1


def test_move_no_direction() -> None:
    ctx = _ctx(user_input="이동한다")
    result = run(handle_move(ctx))
    assert not result.success
    assert result.fail_reason == "no_direction"
    assert result.time_advance == 0


# ─── EXPLORE ───


def test_explore() -> None:
    result = run(handle_explore(_ctx()))
    assert result.success
    assert result.time_advance == 2
    assert len(result.narrative) >= 10


# ─── ATTACK ───


def test_attack_with_enemy() -> None:
    ctx = _ctx(encounters=[{"name": "고블린", "hostile": True}])
    result = run(handle_attack(ctx))
    assert result.success
    assert "고블린" in result.narrative
    assert result.time_advance == 1


def test_attack_no_target() -> None:
    result = run(handle_attack(_ctx()))
    assert not result.success
    assert result.fail_reason == "no_target"
    assert result.time_advance == 0


# ─── ABSORB_ESSENCE ───


def test_absorb_essence_success() -> None:
    ctx = _ctx(inventory=["9등급 정수"])
    result = run(handle_absorb_essence(ctx))
    assert result.success
    assert "9등급 정수" in result.inventory_remove
    assert result.time_advance == 1


def test_absorb_essence_no_essence() -> None:
    result = run(handle_absorb_essence(_ctx(inventory=["물약"])))
    assert not result.success
    assert result.fail_reason == "no_essence"


# ─── USE_ITEM ───


def test_use_item_potion() -> None:
    ctx = _ctx(inventory=["HP 물약"], user_input="물약을 사용한다")
    result = run(handle_use_item(ctx))
    assert result.success
    assert result.hp_change == 30
    assert "HP 물약" in result.inventory_remove


def test_use_item_not_in_inventory() -> None:
    ctx = _ctx(inventory=[], user_input="물약을 사용한다")
    result = run(handle_use_item(ctx))
    assert not result.success


# ─── OFFER_TO_STONE ───


def test_offer_to_stone_success() -> None:
    ctx = _ctx(inventory=["마석 3개"])
    result = run(handle_offer_to_stone(ctx))
    assert result.success
    assert "마석 3개" in result.inventory_remove


def test_offer_to_stone_no_mage_stone() -> None:
    result = run(handle_offer_to_stone(_ctx()))
    assert not result.success
    assert result.fail_reason == "no_mage_stone"


# ─── ENTER / EXIT RIFT ───


def test_enter_rift() -> None:
    result = run(handle_enter_rift(_ctx()))
    assert result.success
    assert result.location is not None
    assert "균열" in result.location


def test_exit_rift() -> None:
    ctx = _ctx(location="1층 A구역 (균열 내부)")
    result = run(handle_exit_rift(ctx))
    assert result.success
    assert result.location is not None
    assert "균열 내부" not in result.location


# ─── REST ───


def test_rest_hp_recovery() -> None:
    ctx = _ctx(current_hp=70, max_hp=100)
    result = run(handle_rest(ctx))
    assert result.success
    assert result.hp_change == 20
    assert result.time_advance == 4


def test_rest_already_full_hp() -> None:
    ctx = _ctx(current_hp=100, max_hp=100)
    result = run(handle_rest(ctx))
    assert result.hp_change == 0


# ─── WAIT ───


def test_wait() -> None:
    result = run(handle_wait(_ctx()))
    assert result.success
    assert result.time_advance == 1


# ─── COMMUNICATE ───


def test_communicate() -> None:
    result = run(handle_communicate(_ctx()))
    assert result.success
    assert result.time_advance == 0


# ─── FLEE ───


def test_flee_with_encounter() -> None:
    # handle_flee is now random-based — assert valid outcome, not always-success
    ctx = _ctx(encounters=[{"name": "오크", "hostile": True}])
    result = run(handle_flee(ctx))
    assert result.time_advance > 0  # always advances time
    assert result.fail_reason in (None, "flee_failed")  # valid outcomes


def test_flee_no_combat() -> None:
    result = run(handle_flee(_ctx()))
    assert not result.success
    assert result.fail_reason == "no_combat"


# ─── FLOOR TRANSITIONS ───


def test_enter_next_floor() -> None:
    result = run(handle_enter_next_floor(_ctx(floor_number=1, location="1층 입구")))
    assert result.success
    assert result.location == "2층 입구"
    assert result.floor_change == 1


def test_exit_to_prev_floor() -> None:
    result = run(handle_exit_to_prev_floor(_ctx(floor_number=1, location="1층 입구")))
    assert result.success
    assert result.location == "마을"
    assert result.floor_change == -1


def test_enter_dungeon() -> None:
    result = run(handle_enter_dungeon(_ctx()))
    assert result.success
    assert result.location == "던전 1층"


# ─── EXCHANGE_MAGE_STONES ───


def test_exchange_mage_stones() -> None:
    result = run(handle_exchange_mage_stones(_ctx()))
    assert result.success
    assert result.time_advance == 1


# ─── WAIT_IN_VILLAGE ───


def test_wait_in_village() -> None:
    ctx = _ctx(current_hp=50, max_hp=100)
    result = run(handle_wait_in_village(ctx))
    assert result.success
    assert result.hp_change == 50
    assert result.time_advance == 24


# ─── HEAL_AT_TEMPLE ───


def test_heal_at_temple() -> None:
    ctx = _ctx(current_hp=30, max_hp=100)
    result = run(handle_heal_at_temple(ctx))
    assert result.success
    assert result.hp_change == 70
    assert result.time_advance == 2


# ─── DIALOGUE / REJECT ───


def test_dialogue_with_npc() -> None:
    ctx = _ctx(encounters=[{"name": "한스", "hostile": False}])
    result = run(handle_dialogue(ctx))
    assert result.success
    assert result.affinity_changes.get("한스") == 1
    assert result.time_advance == 1


def test_dialogue_no_npc() -> None:
    result = run(handle_dialogue(_ctx()))
    assert not result.success
    assert result.fail_reason == "no_npc"


def test_reject_dialogue_affinity_down() -> None:
    ctx = _ctx(encounters=[{"name": "상인", "hostile": False}])
    result = run(handle_reject_dialogue(ctx))
    assert result.success
    assert result.affinity_changes.get("상인") == -1
    assert result.time_advance == 0


# ─── LIBRARY_SEARCH ───


def test_library_search() -> None:
    result = run(handle_library_search(_ctx()))
    assert result.success
    assert result.time_advance == 2


# ─── RECRUIT_FROM_GUILD ───


def test_recruit_from_guild() -> None:
    result = run(handle_recruit_from_guild(_ctx()))
    assert result.success
    assert result.time_advance == 2


# ─── SHOP ───


def test_shop_sell_success() -> None:
    ctx = _ctx(inventory=["마석 5개"], user_input="마석을 판다")
    result = run(handle_shop_sell(ctx))
    assert result.success
    assert "마석 5개" in result.inventory_remove


def test_shop_sell_no_item() -> None:
    ctx = _ctx(inventory=[], user_input="마석을 판다")
    result = run(handle_shop_sell(ctx))
    assert not result.success


def test_shop_buy_success() -> None:
    ctx = _ctx(user_input="물약을 산다")
    result = run(handle_shop_buy(ctx))
    assert result.success
    assert result.inventory_add


def test_shop_buy_no_item() -> None:
    ctx = _ctx(user_input="아무것도 산다")
    result = run(handle_shop_buy(ctx))
    assert not result.success


# ─── NIGHT COMPANION ───


def test_form_night_companion() -> None:
    ctx = _ctx(encounters=[{"name": "엘프 전사", "hostile": False}])
    result = run(handle_form_night_companion(ctx))
    assert result.success
    assert result.time_advance == 0


def test_disband_night_companion() -> None:
    result = run(handle_disband_night_companion(_ctx()))
    assert result.success
    assert result.time_advance == 0


# ─── ENGAGE_BANDIT ───


def test_engage_bandit_with_enemy() -> None:
    ctx = _ctx(encounters=[{"name": "약탈자 수장", "hostile": True}])
    result = run(handle_engage_bandit(ctx))
    assert result.success
    assert "약탈자 수장" in result.narrative


def test_engage_bandit_no_encounter() -> None:
    result = run(handle_engage_bandit(_ctx()))
    assert result.success  # 약탈자 조우는 항상 성공 (기본값 사용)
    assert "약탈자" in result.narrative


# ─── REST_AND_NIGHT_WATCH ───


def test_rest_and_night_watch_success() -> None:
    ctx = _ctx(current_hp=60, max_hp=100)
    result = run(handle_rest_and_night_watch(ctx))
    assert result.success
    assert result.hp_change == 40
    assert result.time_advance == 8


def test_rest_and_night_watch_hostile_nearby() -> None:
    ctx = _ctx(encounters=[{"name": "오크", "hostile": True}])
    result = run(handle_rest_and_night_watch(ctx))
    assert not result.success
    assert result.fail_reason == "hostile_nearby"


# ─── dispatch_action ───


def test_dispatch_known_action() -> None:
    ctx = _ctx(current_hp=50, max_hp=100)
    result = run(dispatch_action(PlayerActionType.REST, ctx))
    assert result.success
    assert result.hp_change > 0


def test_dispatch_all_actions_no_crash() -> None:
    """모든 29 액션 기본 context로 호출 시 crash 없음."""
    base_ctx = _ctx(
        inventory=["9등급 정수", "마석 1개", "HP 물약", "횃불", "마석 5개"],
        encounters=[
            {"name": "오크", "hostile": True},
            {"name": "상인", "hostile": False},
        ],
        user_input="북쪽으로 이동",
        location="1층 A구역",
        current_hp=70,
        max_hp=100,
    )
    for action_type in PlayerActionType:
        result = run(dispatch_action(action_type, base_ctx))
        assert isinstance(result, ActionResult), f"{action_type} returned non-ActionResult"
        assert isinstance(result.narrative, str)
        assert len(result.narrative) > 0
