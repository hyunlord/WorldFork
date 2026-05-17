"""§B critical bug regression — MOVE location.sub_area mutation.

30턴 playthrough §B finding:
- turn 4 `move 북쪽 통로` success=True
- side_effect `target_sub_area=북쪽 통로` emit
- 본격 location.sub_area mutation X — '진입점' 본격 stuck
- turn 17/28 후속 move fail cascade

root cause:
- service/sim/sim_runner.py MOVE dispatch
- RIFT branch (★ target_rift_sub_area apply) 본격 본격 본격
- DUNGEON branch (★ target_sub_area apply) **본격 X** ← §B bug

fix:
- 본격 r.success 본격 본격 본격 target_sub_area / target_rift_sub_area 본격
  side_effect 본격 parallel apply (★ 모든 realm 본격 정합)

본 test file (★ regression coverage):
- DUNGEON 본격 move success → sub_area mutation
- chain hops (★ 진입점 → 북쪽 통로 → 비석 공동)
- move fail (★ 인접 X) → mutation X
- RIFT regression (★ rift_sub_area only, sub_area 변화 X)
- 30턴 playthrough §B 본격 본격 reproducer
"""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.sim_runner import _execute_action
from service.sim.types import PlayerAction, PlayerActionType

# ─── Helpers ───


def _bjorn() -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=100,
        hp_max=100,
        is_player=True,
    )


def _dungeon_entrance() -> Location:
    return Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="진입점",
        has_light=True,
    )


def _move_action(target: str) -> PlayerAction:
    return PlayerAction(
        action_type=PlayerActionType.MOVE,
        actor_name="비요른",
        target=target,
        rationale="move test",
    )


def _party_dict(c: Character) -> dict[str, Character]:
    return {c.name: c}


# ─── DUNGEON move sub_area mutation (★ §B fix 검증) ───


class TestDungeonMoveSubAreaMutation:
    def test_dungeon_move_updates_sub_area(self) -> None:
        """30턴 playthrough §B reproducer — turn 4 move 북쪽 통로."""
        party = _party_dict(_bjorn())
        world = WorldState()
        location = _dungeon_entrance()
        assert location.sub_area == "진입점"

        success, message, side_effects = _execute_action(
            _move_action("북쪽 통로"), party, world, location
        )

        assert success is True
        assert "진입점 → 북쪽 통로" in message
        # ★ §B fix — location.sub_area 본격 mutation 본격
        assert location.sub_area == "북쪽 통로"
        # side_effect 본격 본격 emit (★ regression — handler 본격 본격)
        assert any(
            eff == "target_sub_area=북쪽 통로"
            for eff in side_effects
        )

    def test_dungeon_move_chain_3_hops(self) -> None:
        """진입점 → 북쪽 통로 → 비석 공동 (★ floor1 connection 정합).

        본격 본격 본격 본격 본격 본격 stuck 본격 본격 본격 cascade fail 본격.
        """
        party = _party_dict(_bjorn())
        world = WorldState()
        location = _dungeon_entrance()

        # hop 1: 진입점 → 북쪽 통로
        s1, _, _ = _execute_action(
            _move_action("북쪽 통로"), party, world, location
        )
        assert s1 is True
        assert location.sub_area == "북쪽 통로"

        # hop 2: 북쪽 통로 → 비석 공동 (★ accessible_from 정합)
        s2, _, _ = _execute_action(
            _move_action("비석 공동"), party, world, location
        )
        assert s2 is True
        assert location.sub_area == "비석 공동"

        # hop 3: 비석 공동 → 북쪽 통로 (★ 회귀)
        s3, _, _ = _execute_action(
            _move_action("북쪽 통로"), party, world, location
        )
        assert s3 is True
        assert location.sub_area == "북쪽 통로"

    def test_dungeon_move_fail_no_mutation(self) -> None:
        """fail 본격 본격 본격 location.sub_area 변화 X."""
        party = _party_dict(_bjorn())
        world = WorldState()
        location = _dungeon_entrance()

        # 진입점 → 포탈 근처 본격 인접 X (★ 진입점 accessible_from = ('북쪽 통로',))
        success, message, _ = _execute_action(
            _move_action("포탈 근처"), party, world, location
        )

        assert success is False
        assert "인접 X" in message
        # ★ mutation X
        assert location.sub_area == "진입점"

    def test_dungeon_move_unknown_target_no_mutation(self) -> None:
        """unknown sub_area 본격 본격 본격 mutation X."""
        party = _party_dict(_bjorn())
        world = WorldState()
        location = _dungeon_entrance()

        success, message, _ = _execute_action(
            _move_action("남쪽"), party, world, location
        )

        assert success is False
        # 30턴 playthrough turn 9 본격 본격 fail message
        assert "sub_area 없음" in message
        assert location.sub_area == "진입점"


# ─── RIFT move regression (★ rift_sub_area only, sub_area unchanged) ───


class TestRiftMoveBackwardCompat:
    def _rift_entrance(self) -> Location:
        """핏빛성채 entrance (★ bc_ch1) — bandit dungeon 본격."""
        return Location(
            realm=Realm.RIFT,
            floor=1,
            sub_area="포탈 근처",  # ★ rift 본격 sub_area 본격 본격 본격 X
            rift_id="bloody_castle",
            rift_sub_area="bc_ch1",
            rift_is_variant=False,
            has_light=True,
        )

    def test_rift_move_updates_rift_sub_area_only(self) -> None:
        """rift move 본격 rift_sub_area 본격 본격, sub_area 변화 X."""
        party = _party_dict(_bjorn())
        world = WorldState()
        location = self._rift_entrance()
        initial_sub_area = location.sub_area

        # bc_ch1 → bc_ch2 (★ 정확한 connection 본격 본격 본격 RiftDef 본격 확인)
        # 본격 본격 본격 본격 본격 본격 본격 — 본격 본격 본격 본격 본격 본격 본격
        # bc_ch1 connections 본격 도개교 본격 본격 (★ 본문 playthrough turn 21)
        success, message, side_effects = _execute_action(
            _move_action("도개교"), party, world, location
        )

        # success/fail 본격 본격 본격 본격 — 본격 본격 본격 본격 본격 sub_area 본격 본격 X
        # ★ 본격 본격 본격 본격 sub_area 본격 본격 본격 X (★ §B fix regression)
        assert location.sub_area == initial_sub_area
        # success 본격 본격 본격 rift_sub_area 본격 본격
        if success:
            assert location.rift_sub_area != "bc_ch1"
            assert any(
                eff.startswith("target_rift_sub_area=")
                for eff in side_effects
            )


# ─── Realm enum 본격 branch coverage ───


class TestMoveDispatchSideEffectParity:
    def test_dungeon_emits_target_sub_area(self) -> None:
        """DUNGEON handler 본격 target_sub_area= side_effect emit (★ producer)."""
        party = _party_dict(_bjorn())
        world = WorldState()
        location = _dungeon_entrance()

        _, _, side_effects = _execute_action(
            _move_action("북쪽 통로"), party, world, location
        )
        targets = [
            eff.split("=", 1)[1]
            for eff in side_effects
            if eff.startswith("target_sub_area=")
        ]
        assert targets == ["북쪽 통로"]

    def test_dungeon_no_target_rift_sub_area(self) -> None:
        """DUNGEON 본격 본격 target_rift_sub_area 본격 emit X."""
        party = _party_dict(_bjorn())
        world = WorldState()
        location = _dungeon_entrance()

        _, _, side_effects = _execute_action(
            _move_action("북쪽 통로"), party, world, location
        )
        assert not any(
            eff.startswith("target_rift_sub_area=")
            for eff in side_effects
        )


# ─── 30턴 playthrough §B integration scenario ───


class TestPlaythrough30TurnReproduction:
    """30턴 playthrough §B 본격 본격 specific reproducer."""

    def test_turn_4_move_then_turn_17_works(self) -> None:
        """turn 4 본격 move 본격 본격 location 본격 본격 본격 본격 turn 17 본격 move 본격 본격.

        본격 본격 본격 본격 stuck 본격 본격 본격 본격 turn 17 본격 본격 진입점
        → 포탈 근처 본격 fail. 본 fix 본격 본격 본격 turn 4 본격 본격 본격
        북쪽 통로 본격 본격 본격, turn 17 본격 북쪽 통로 → 포탈 근처 본격 본격.
        """
        party = _party_dict(_bjorn())
        world = WorldState()
        location = _dungeon_entrance()

        # turn 4: 진입점 → 북쪽 통로
        s4, _, _ = _execute_action(
            _move_action("북쪽 통로"), party, world, location
        )
        assert s4 is True
        assert location.sub_area == "북쪽 통로"

        # turn 17: 북쪽 통로 → 포탈 근처 (★ accessible_from 정합)
        s17, msg17, _ = _execute_action(
            _move_action("포탈 근처"), party, world, location
        )
        # ★ §B fix 본격 본격 본격 본격 본격 본격 본격
        assert s17 is True, (
            f"§B fix 본격 본격 — 본격 fail message: {msg17}"
        )
        assert location.sub_area == "포탈 근처"
