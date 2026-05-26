"""Phase 8 exchange E2E — SimRunner 본격 EXCHANGE_MAGE_STONES dispatch.

검증 본질 (★ LLM 무관 결정적):
- SimRunner 본격 EXCHANGE_MAGE_STONES action 본격 dispatch
- 마을 (★ realm=CITY + sub_area=exchange_office) 본격 본격
- inventory 본격 마석 → stone +N
- trace snapshot 본격 actor.stone 본격 본격

본 commit 본격 본격 (★ docs/village_spec.md §3-3 정합):
1. 마을 도착 (★ 본격 직접 location 본격 본격 — A4 168h 본격 본격 본격 X)
2. exchange_office sub_area 위치
3. ATTACK 처치 + mage stone (★ skip — 본격 직접 inventory 주입)
4. EXCHANGE_MAGE_STONES → stone +rate
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Item,
    ItemCategory,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import SimRunner
from service.sim.types import PlayerAction, PlayerActionType, SimConfig


def _party() -> dict[str, Character]:
    actor = Character(
        name="투르윈",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        is_player=True,
    )
    # 본격 직접 마석 주입 (★ ATTACK + 보스 처치 본격 본격 본격 본격 다른 e2e 본격)
    actor.inventory.items.append(
        Item(
            name="블라터의 마석",
            category=ItemCategory.MATERIAL,
            weight=1,
            grade=6,
        )
    )
    actor.inventory.items.append(
        Item(
            name="고블린 마석",
            category=ItemCategory.MATERIAL,
            weight=1,
            grade=9,
        )
    )
    return {"투르윈": actor}


def _exchange_office_loc() -> Location:
    """직접 마을 환전소 위치 (★ A4 마을 귀환 본격 본격 본격 본격)."""
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="exchange_office",
        city_id="rascania",
    )


# ─── 1. SimRunner dispatch ───


def test_scripted_exchange_increments_stone() -> None:
    """EXCHANGE_MAGE_STONES action → actor.stone += 2520 (★ 6등급 2500 + 9등급 20)."""
    party = _party()
    world = WorldState(party_members=list(party.keys()))
    loc = _exchange_office_loc()

    actions = [
        PlayerAction(
            action_type=PlayerActionType.EXCHANGE_MAGE_STONES,
            actor_name="투르윈",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=1,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=loc)

    assert result.end_reason == "max_turns"
    actor = party["투르윈"]
    # 6등급 마석 = 2500, 9등급 마석 = 20 → 총 2520
    assert actor.stone == 2520
    assert len(actor.inventory.items) == 0  # ★ 환전된 마석 본격 제거

    # turn log side_effects 본격
    log = result.turn_logs[0]
    assert any(
        "exchanged_stones=투르윈:2" in s for s in log.side_effects
    )
    assert any(
        "stone_gained=투르윈:+2520" in s for s in log.side_effects
    )


def test_scripted_exchange_outside_office_fails() -> None:
    """district_7_plaza 본격 EXCHANGE → fail (★ sub_area 검증)."""
    party = _party()
    world = WorldState(party_members=list(party.keys()))
    # 마을 본격, 본격 광장 (★ exchange_office 본격 본격 X)
    loc = Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="district_7_plaza",
        city_id="rascania",
    )

    actions = [
        PlayerAction(
            action_type=PlayerActionType.EXCHANGE_MAGE_STONES,
            actor_name="투르윈",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=1,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=loc)

    actor = party["투르윈"]
    # mutation X — 마석 본격 보존, stone 본격 0
    assert actor.stone == 0
    assert len(actor.inventory.items) == 2
    log = result.turn_logs[0]
    assert log.success is False


def test_scripted_exchange_outside_city_fails() -> None:
    """미궁 본격 EXCHANGE → fail (★ realm 검증)."""
    party = _party()
    world = WorldState(party_members=list(party.keys()))
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")

    actions = [
        PlayerAction(
            action_type=PlayerActionType.EXCHANGE_MAGE_STONES,
            actor_name="투르윈",
        ),
    ]
    runner = SimRunner(
        config=SimConfig(
            max_turns=1,
            initial_hours_in_dungeon=0.0,
            time_scale=1.0,
            stop_on_permadeath=False,
        ),
        player_agent=MockPlayerAgent(mock_actions=actions),
    )
    result = runner.run(party=party, world=world, location=loc)

    actor = party["투르윈"]
    assert actor.stone == 0
    log = result.turn_logs[0]
    assert log.success is False
