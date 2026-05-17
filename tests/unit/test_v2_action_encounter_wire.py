"""Phase 9.18-a — v2_state_router encounter wire (★ §E fix).

본 commit (★ B.2a):
- _V2StateHolder.active_encounters 필드
- _V2StateHolder._sim_gm_agent lazy init (★ 9B Q3 / 8083)
- _expire_encounters TTL cleanup
- _handle_encounter_side_effects (★ encounter_consumed / trigger / essence_spawn)
- _maybe_spawn_encounters (★ 던전 한정 + silent fallback)
- post_action flow 본격 encounter wire
- ActionResponse.encounters 필드

기대 효과 (★ 30턴 playthrough §E 검증):
- 9.17 시리즈 consumer (밤친구 / 약탈자 / 불침번 trigger) 본격 본격 trigger 가능
- LLM 실패 시 mechanical 본격 계속 진행 (★ silent fallback)
"""

from __future__ import annotations

import random
from typing import Any

from fastapi.testclient import TestClient

from service.api.app import app
from service.api.v2_state_router import (
    _expire_encounters,
    _handle_encounter_side_effects,
    _maybe_spawn_encounters,
    _serialize_encounter,
    _V2StateHolder,
    get_holder,
)
from service.game.state_v2 import Location, Realm
from service.sim.types import Encounter, EncounterType, GMResponse

# ─── _V2StateHolder.active_encounters ───


class TestActiveEncountersField:
    def test_default_empty(self) -> None:
        h = _V2StateHolder()
        assert h.active_encounters == []

    def test_reset_clears(self) -> None:
        h = _V2StateHolder()
        h.active_encounters.append(
            Encounter(
                type=EncounterType.NPC_PEACEFUL,
                name="enc_1",
                location="loc",
                spawned_at_turn=0,
                ttl_turns=5,
            )
        )
        h.reset()
        assert h.active_encounters == []

    def test_reset_preserves_sim_gm_agent(self) -> None:
        """reset 본격 SimGMAgent instance 본격 본격 본격 (★ cost 본격)."""
        h = _V2StateHolder()
        # lazy create
        agent = h.get_sim_gm_agent()
        h.reset()
        # 본격 본격 본격 instance 본격
        assert h._sim_gm_agent is agent


class TestLazyInitSimGMAgent:
    def test_initial_none(self) -> None:
        h = _V2StateHolder()
        assert h._sim_gm_agent is None

    def test_lazy_creation(self) -> None:
        h = _V2StateHolder()
        agent = h.get_sim_gm_agent()
        assert agent is not None

    def test_singleton_per_holder(self) -> None:
        h = _V2StateHolder()
        a1 = h.get_sim_gm_agent()
        a2 = h.get_sim_gm_agent()
        assert a1 is a2


# ─── _expire_encounters ───


class TestExpireEncounters:
    def _enc(
        self,
        name: str,
        spawned: int,
        ttl: int,
        type_: EncounterType = EncounterType.NPC_PEACEFUL,
    ) -> Encounter:
        return Encounter(
            type=type_,
            name=name,
            location="loc",
            spawned_at_turn=spawned,
            ttl_turns=ttl,
        )

    def test_expired_removed(self) -> None:
        """spawned=10, ttl=3, current=14 → expired (14-10=4 >= 3)."""
        encs = [self._enc("expired", spawned=10, ttl=3)]
        removed = _expire_encounters(encs, current_turn=14)
        assert removed == ["expired"]
        assert encs == []

    def test_alive_kept(self) -> None:
        """spawned=10, ttl=5, current=12 → alive (12-10=2 < 5)."""
        encs = [self._enc("alive", spawned=10, ttl=5)]
        removed = _expire_encounters(encs, current_turn=12)
        assert removed == []
        assert len(encs) == 1

    def test_boundary_exactly_at_ttl(self) -> None:
        """spawned=0, ttl=5, current=5 → expired (5-0=5 >= 5, is_expired 본격)."""
        encs = [self._enc("boundary", spawned=0, ttl=5)]
        _expire_encounters(encs, current_turn=5)
        assert encs == []

    def test_mixed_removes_only_expired(self) -> None:
        encs = [
            self._enc("expired1", spawned=0, ttl=3),
            self._enc("alive1", spawned=5, ttl=10),
            self._enc("expired2", spawned=0, ttl=5),
        ]
        removed = _expire_encounters(encs, current_turn=10)
        assert sorted(removed) == ["expired1", "expired2"]
        assert [e.name for e in encs] == ["alive1"]


# ─── _handle_encounter_side_effects ───


def _dungeon_loc() -> Location:
    return Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="floor1_corridor",
    )


def _peaceful_enc(name: str) -> Encounter:
    return Encounter(
        type=EncounterType.NPC_PEACEFUL,
        name=name,
        location="floor1_corridor",
        spawned_at_turn=0,
        ttl_turns=5,
    )


class TestHandleEncounterConsumed:
    def test_single_consumed_removed(self) -> None:
        encs = [_peaceful_enc("e1"), _peaceful_enc("e2")]
        side_effects = ["encounter_consumed=e1"]
        _handle_encounter_side_effects(
            side_effects, encs, _dungeon_loc(), current_turn=3
        )
        assert [e.name for e in encs] == ["e2"]

    def test_multi_consumed_batch_removed(self) -> None:
        encs = [_peaceful_enc("e1"), _peaceful_enc("e2"), _peaceful_enc("e3")]
        side_effects = [
            "encounter_consumed=e1",
            "encounter_consumed=e3",
        ]
        _handle_encounter_side_effects(
            side_effects, encs, _dungeon_loc(), current_turn=3
        )
        assert [e.name for e in encs] == ["e2"]

    def test_unknown_consumed_no_op(self) -> None:
        encs = [_peaceful_enc("e1")]
        side_effects = ["encounter_consumed=nonexistent"]
        _handle_encounter_side_effects(
            side_effects, encs, _dungeon_loc(), current_turn=3
        )
        assert [e.name for e in encs] == ["e1"]


class TestHandleTriggerEncounterAfterRest:
    def test_spawns_new_encounter(self) -> None:
        encs: list[Encounter] = []
        side_effects = ["trigger_encounter_after_rest"]
        rng = random.Random(0)
        _handle_encounter_side_effects(
            side_effects, encs, _dungeon_loc(), current_turn=5, rng=rng
        )
        assert len(encs) == 1
        # location 본격 sub_area 정합
        assert encs[0].location == "floor1_corridor"
        assert encs[0].spawned_at_turn == 5

    def test_appends_spawn_marker(self) -> None:
        encs: list[Encounter] = []
        side_effects = ["trigger_encounter_after_rest"]
        rng = random.Random(0)
        _handle_encounter_side_effects(
            side_effects, encs, _dungeon_loc(), current_turn=5, rng=rng
        )
        assert any(
            eff.startswith("encounter_spawned_after_rest=")
            for eff in side_effects
        )

    def test_uses_rift_id_if_in_rift(self) -> None:
        loc = Location(
            realm=Realm.DUNGEON,
            floor=1,
            sub_area="floor1_corridor",
            rift_id="bloody_castle",
        )
        encs: list[Encounter] = []
        side_effects = ["trigger_encounter_after_rest"]
        rng = random.Random(0)
        _handle_encounter_side_effects(
            side_effects, encs, loc, current_turn=5, rng=rng
        )
        # rift_id 우선
        assert encs[0].location == "bloody_castle"

    def test_no_trigger_no_spawn(self) -> None:
        encs: list[Encounter] = []
        side_effects = ["불침번 — 80% 회복"]
        _handle_encounter_side_effects(
            side_effects, encs, _dungeon_loc(), current_turn=5
        )
        assert encs == []


class TestHandleEssenceSpawn:
    def test_red_essence_spawn(self) -> None:
        encs: list[Encounter] = []
        side_effects = ["essence_spawn=red"]
        _handle_encounter_side_effects(
            side_effects, encs, _dungeon_loc(), current_turn=5
        )
        assert len(encs) == 1
        assert encs[0].type == EncounterType.ESSENCE
        assert "핏빛" in encs[0].name

    def test_unknown_color_fallback(self) -> None:
        encs: list[Encounter] = []
        side_effects = ["essence_spawn=purple"]
        _handle_encounter_side_effects(
            side_effects, encs, _dungeon_loc(), current_turn=5
        )
        assert len(encs) == 1
        assert "purple" in encs[0].name


# ─── _maybe_spawn_encounters (★ 던전 한정) ───


class TestMaybeSpawnEncounters:
    def test_city_skips_generator(self) -> None:
        """CITY 본격 generator 호출 X (★ 본격 mechanical only)."""
        h = _V2StateHolder()
        h.location = Location(realm=Realm.CITY, sub_area="district_7_plaza")
        initial = len(h.active_encounters)
        # _sim_gm_agent 본격 None 본격 본격 (★ lazy init 본격 본격 X)
        _maybe_spawn_encounters(h)
        assert len(h.active_encounters) == initial
        assert h._sim_gm_agent is None  # ★ lazy init 본격 X

    def test_dungeon_calls_generator(self) -> None:
        """DUNGEON 본격 generator 호출 + 신규 encounter spawn."""
        h = _V2StateHolder()
        # mock SimGMAgent — encounter 1개 반환
        mock_enc = Encounter(
            type=EncounterType.NPC_PEACEFUL,
            name="mock_peaceful",
            location="floor1_corridor",
            description="mocked",
        )
        mock_response = GMResponse(encounters=[mock_enc])

        class _MockAgent:
            def generate_encounters(
                self, turn_number: int, game_context: dict[str, Any]
            ) -> GMResponse:
                return mock_response

        h._sim_gm_agent = _MockAgent()  # type: ignore[assignment]
        _maybe_spawn_encounters(h)
        assert len(h.active_encounters) == 1
        assert h.active_encounters[0].name == "mock_peaceful"
        # spawned_at_turn 본격 holder.turn 본격
        assert h.active_encounters[0].spawned_at_turn == h.turn

    def test_silent_fallback_on_llm_error(self) -> None:
        """LLM 호출 실패 시 mechanical 본격 계속 진행 (★ silent fallback)."""
        h = _V2StateHolder()

        class _FailingAgent:
            def generate_encounters(
                self, turn_number: int, game_context: dict[str, Any]
            ) -> GMResponse:
                raise RuntimeError("LLM down")

        h._sim_gm_agent = _FailingAgent()  # type: ignore[assignment]
        # 본격 본격 본격 본격 본격 (★ silent)
        _maybe_spawn_encounters(h)
        assert h.active_encounters == []

    def test_wilderness_skips(self) -> None:
        h = _V2StateHolder()
        h.location = Location(realm=Realm.WILDERNESS)
        _maybe_spawn_encounters(h)
        assert h._sim_gm_agent is None


# ─── _serialize_encounter ───


class TestSerializeEncounter:
    def test_required_fields(self) -> None:
        enc = Encounter(
            type=EncounterType.NPC_HOSTILE,
            name="bandit_1",
            location="corridor",
            description="약탈자",
            spawned_at_turn=3,
            ttl_turns=5,
        )
        d = _serialize_encounter(enc)
        assert d["name"] == "bandit_1"
        assert d["type"] == "npc_hostile"
        assert d["location"] == "corridor"
        assert d["description"] == "약탈자"
        assert d["spawned_at_turn"] == 3
        assert d["ttl_turns"] == 5


# ─── post_action integration (★ frontend path) ───


class TestPostActionIntegration:
    def test_action_response_has_encounters_field(self) -> None:
        """ActionResponse.encounters 필드 본격 본격 (★ frontend schema)."""
        client = TestClient(app)
        # reset 본격 깨끗 state
        client.post("/api/v2/state/reset")
        # LLM 호출 본격 본격 본격 generator 실패 본격 정합 — 본격 silent fallback
        # 본격 encounters 본격 본격 본격 본격 본격 (★ side_effect 본격 본격)
        response = client.post(
            "/api/v2/action",
            json={"action_type": "explore", "actor": "비요른"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "encounters" in data
        assert isinstance(data["encounters"], list)

    def test_unknown_action_400(self) -> None:
        client = TestClient(app)
        client.post("/api/v2/state/reset")
        response = client.post(
            "/api/v2/action",
            json={"action_type": "nonexistent_action"},
        )
        assert response.status_code == 400

    def test_silent_fallback_via_failing_agent(self) -> None:
        """LLM 실패 시 mechanical action 본격 계속 작동.

        본격 _maybe_spawn_encounters 본격 본격 try/except 본격 silent fallback —
        holder 본격 SimGMAgent 본격 본격 fail 본격 본격 action 본격 본격 200 본격.
        """
        client = TestClient(app)
        client.post("/api/v2/state/reset")
        h = get_holder()

        class _FailingAgent:
            def generate_encounters(
                self, turn_number: int, game_context: dict[str, Any]
            ) -> GMResponse:
                raise RuntimeError("LLM down")

        # 본격 SimGMAgent instance 본격 강제 fail 본격 본격 — _maybe_spawn_encounters
        # 본격 except 본격 silent fallback 본격 본격 mechanical 본격 본격
        h._sim_gm_agent = _FailingAgent()  # type: ignore[assignment]
        try:
            response = client.post(
                "/api/v2/action",
                json={"action_type": "explore", "actor": "비요른"},
            )
            assert response.status_code == 200, response.text
            data = response.json()
            # mechanical 본격 본격 본격 (★ explore 본격 본격 본격)
            assert data["success"] is True
            # encounters 본격 빈 list (★ fallback 본격 spawn X)
            assert data["encounters"] == []
        finally:
            h.reset()
            h._sim_gm_agent = None


class TestHolderGlobalSingleton:
    def test_get_holder_returns_singleton(self) -> None:
        h1 = get_holder()
        h2 = get_holder()
        assert h1 is h2

    def test_holder_active_encounters_persist_across_calls(self) -> None:
        """holder.active_encounters 본격 cross-request state 본격."""
        h = get_holder()
        h.reset()
        # 본격 본격 추가 본격
        h.active_encounters.append(
            Encounter(
                type=EncounterType.NPC_NEUTRAL,
                name="persisted_enc",
                location="corridor",
            )
        )
        # 본격 새 reference 본격 본격
        h2 = get_holder()
        assert any(
            e.name == "persisted_enc" for e in h2.active_encounters
        )
        h.reset()  # cleanup
