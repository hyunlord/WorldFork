"""Phase 9.18-c — v2_state_router narrative wire (★ §A 해소).

본 commit (★ B.2b):
- GMAgent.narrate_action_v2 신규 method
- _V2StateHolder._gm_narrator lazy init (★ 27B Q3 / 8081, verify_llm=None)
- _build_v2_ctx helper
- _maybe_narrate (★ silent fallback)
- post_action narrative call wire
- ActionResponse.narrative: str | None

기대 효과 (★ 30턴 playthrough):
- mechanical message → 한국어 narrative (★ frontend 본격 본격 풍부화)
- LLM 실패 시 mechanical 본격 계속 작동
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from service.api.v2_state_router import (
    _build_v2_ctx,
    _maybe_narrate,
    _serialize_char_min,
    _serialize_location_min,
    _serialize_world_min,
    _V2StateHolder,
)
from service.game.gm_agent import GMAgent
from service.sim.types import Encounter, EncounterType, PlayerAction, PlayerActionType

# ─── _V2StateHolder._gm_narrator lazy init ───


class TestLazyNarrator:
    def test_initial_none(self) -> None:
        h = _V2StateHolder()
        assert h._gm_narrator is None

    def test_lazy_creation_returns_gm_agent(self) -> None:
        h = _V2StateHolder()
        agent = h.get_gm_narrator()
        assert isinstance(agent, GMAgent)

    def test_verify_llm_none(self) -> None:
        """B.2b — V2 본격 verify mechanism 미정의 (★ verify_llm=None)."""
        h = _V2StateHolder()
        agent = h.get_gm_narrator()
        assert agent._verify_llm is None

    def test_singleton_per_holder(self) -> None:
        h = _V2StateHolder()
        a1 = h.get_gm_narrator()
        a2 = h.get_gm_narrator()
        assert a1 is a2

    def test_reset_preserves_narrator(self) -> None:
        """reset 본격 narrator 본격 본격 보존 (★ cost)."""
        h = _V2StateHolder()
        agent = h.get_gm_narrator()
        h.reset()
        assert h._gm_narrator is agent


# ─── _serialize_char_min / world_min / location_min ───


def _bjorn_default() -> Any:
    h = _V2StateHolder()
    return h.party["투르윈"]


class TestSerializeCharMin:
    def test_includes_basic_fields(self) -> None:
        c = _bjorn_default()
        d = _serialize_char_min(c)
        assert d["name"] == "투르윈"
        assert "race" in d
        assert d["hp"] == c.hp
        assert d["hp_max"] == c.hp_max
        assert "is_temporary" in d
        assert "level" in d
        assert "class_type" in d


class TestSerializeWorldMin:
    def test_includes_world_fields(self) -> None:
        h = _V2StateHolder()
        d = _serialize_world_min(h.world)
        assert "hours_in_dungeon" in d
        assert "month_number" in d
        assert "day_in_month" in d
        assert "active_rifts" in d


class TestSerializeLocationMin:
    def test_includes_location_fields(self) -> None:
        h = _V2StateHolder()
        d = _serialize_location_min(h.location)
        assert d["realm"] == "미궁"
        assert d["floor"] == 1
        assert d["sub_area"] == "진입점"


# ─── _build_v2_ctx ───


class TestBuildV2Ctx:
    def test_required_v1_fields(self) -> None:
        h = _V2StateHolder()
        ctx = _build_v2_ctx(h)
        # _gm_system_prompt 본격 본격 본격 본격 field 본격
        for key in (
            "work_name",
            "work_genre",
            "world_setting",
            "world_tone",
            "world_rules",
            "main_character_name",
            "main_character_role",
            "supporting_characters",
            "current_location",
            "current_turn",
        ):
            assert key in ctx, f"missing: {key}"

    def test_v2_fields_present(self) -> None:
        h = _V2StateHolder()
        ctx = _build_v2_ctx(h)
        assert "v2_characters" in ctx
        assert "v2_world_state" in ctx
        assert "v2_initial_location" in ctx
        assert "active_encounters" in ctx

    def test_main_char_excluded_from_supporting(self) -> None:
        h = _V2StateHolder()
        ctx = _build_v2_ctx(h)
        names = [s["name"] for s in ctx["supporting_characters"]]
        assert "투르윈" not in names
        # 에르웬 본격 supporting 본격 포함
        assert "실렌" in names

    def test_includes_active_encounters(self) -> None:
        h = _V2StateHolder()
        h.active_encounters.append(
            Encounter(
                type=EncounterType.NPC_PEACEFUL,
                name="test_enc",
                location="loc",
                spawned_at_turn=0,
                ttl_turns=5,
            )
        )
        ctx = _build_v2_ctx(h)
        assert len(ctx["active_encounters"]) == 1
        assert ctx["active_encounters"][0]["name"] == "test_enc"

    def test_current_location_uses_sub_area(self) -> None:
        h = _V2StateHolder()
        ctx = _build_v2_ctx(h)
        assert ctx["current_location"] == "진입점"

    def test_current_turn_reflects_holder(self) -> None:
        h = _V2StateHolder()
        h.turn = 7
        ctx = _build_v2_ctx(h)
        assert ctx["current_turn"] == 7


# ─── _maybe_narrate ───


def _make_action() -> PlayerAction:
    return PlayerAction(
        action_type=PlayerActionType.EXPLORE,
        actor_name="비요른",
        target=None,
        rationale="test",
    )


class TestMaybeNarrate:
    def test_fail_returns_none(self) -> None:
        """success=False 본격 None (★ fail 본격 mechanical 본격 본격)."""
        h = _V2StateHolder()
        result = _maybe_narrate(
            h, _make_action(), "mech msg", [], success=False
        )
        assert result is None

    def test_success_calls_narrator(self) -> None:
        """success=True 본격 narrate_action_v2 호출 + 결과 반환."""
        h = _V2StateHolder()
        mock_narrator = MagicMock(spec=GMAgent)
        mock_narrator.narrate_action_v2.return_value = "한국어 narrative 본격"
        h._gm_narrator = mock_narrator  # bypass lazy init
        result = _maybe_narrate(
            h, _make_action(), "mech msg", [], success=True
        )
        assert result == "한국어 narrative 본격"
        mock_narrator.narrate_action_v2.assert_called_once()

    def test_llm_exception_silent_fallback(self) -> None:
        """LLM 본격 본격 본격 본격 본격 None 본격 fallback."""
        h = _V2StateHolder()
        mock_narrator = MagicMock(spec=GMAgent)
        mock_narrator.narrate_action_v2.side_effect = RuntimeError("LLM down")
        h._gm_narrator = mock_narrator
        result = _maybe_narrate(
            h, _make_action(), "mech msg", [], success=True
        )
        assert result is None

    def test_narrator_returns_fallback_message_returns_none(self) -> None:
        """narrator 본격 본격 본격 mechanical message 본격 본격 본격 None 본격 본격.

        (★ narrate_action_v2 본격 fallback 본격 result_message 본격 본격
        — caller 본격 본격 None 본격 본격 본격 ActionResponse.narrative 본격 None).
        """
        h = _V2StateHolder()
        mock_narrator = MagicMock(spec=GMAgent)
        mock_narrator.narrate_action_v2.return_value = "mech msg"
        h._gm_narrator = mock_narrator
        result = _maybe_narrate(
            h, _make_action(), "mech msg", [], success=True
        )
        assert result is None


# ─── GMAgent.narrate_action_v2 unit ───


class TestNarrateActionV2:
    def _make_agent_with_mock_llm(self, response_text: str) -> GMAgent:
        mock_llm = MagicMock()
        mock_llm.model_name = "mock-llm"
        mock_response = MagicMock()
        mock_response.text = response_text
        mock_llm.generate.return_value = mock_response
        return GMAgent(game_llm=mock_llm, verify_llm=None)

    def _ctx(self) -> dict[str, Any]:
        h = _V2StateHolder()
        return _build_v2_ctx(h)

    def test_returns_llm_text(self) -> None:
        agent = self._make_agent_with_mock_llm("새로운 한국어 narrative")
        result = agent.narrate_action_v2(
            _make_action(), "mech msg", [], self._ctx()
        )
        assert result == "새로운 한국어 narrative"

    def test_empty_llm_returns_fallback_message(self) -> None:
        agent = self._make_agent_with_mock_llm("")
        result = agent.narrate_action_v2(
            _make_action(), "mech msg", [], self._ctx()
        )
        assert result == "mech msg"

    def test_whitespace_only_returns_fallback(self) -> None:
        agent = self._make_agent_with_mock_llm("   \n\n  ")
        result = agent.narrate_action_v2(
            _make_action(), "mech msg", [], self._ctx()
        )
        assert result == "mech msg"

    def test_llm_exception_returns_fallback(self) -> None:
        mock_llm = MagicMock()
        mock_llm.model_name = "mock-llm"
        mock_llm.generate.side_effect = RuntimeError("LLM down")
        agent = GMAgent(game_llm=mock_llm, verify_llm=None)
        result = agent.narrate_action_v2(
            _make_action(), "fallback msg", [], self._ctx()
        )
        assert result == "fallback msg"

    def test_strips_response(self) -> None:
        agent = self._make_agent_with_mock_llm("\n\n  narrative text  \n")
        result = agent.narrate_action_v2(
            _make_action(), "mech", [], self._ctx()
        )
        assert result == "narrative text"


class TestBuildUserPromptV2:
    def _ctx(self) -> dict[str, Any]:
        h = _V2StateHolder()
        return _build_v2_ctx(h)

    def test_includes_action_metadata(self) -> None:
        prompt = GMAgent._build_user_prompt_v2(
            _make_action(), "mech msg", [], self._ctx()
        )
        assert "비요른" in prompt
        assert "explore" in prompt
        assert "mech msg" in prompt

    def test_includes_target_when_present(self) -> None:
        action = PlayerAction(
            action_type=PlayerActionType.ATTACK,
            actor_name="비요른",
            target="고블린",
        )
        prompt = GMAgent._build_user_prompt_v2(
            action, "처치 완료.", [], self._ctx()
        )
        assert "고블린" in prompt

    def test_significant_side_effects_included(self) -> None:
        prompt = GMAgent._build_user_prompt_v2(
            _make_action(),
            "mech",
            [
                "encounter_consumed=enc_1",
                "hp_recovered=비요른:+30",
                "stone_paid=비요른:-100",
            ],
            self._ctx(),
        )
        assert "encounter_consumed=enc_1" in prompt
        assert "hp_recovered=비요른:+30" in prompt
        assert "stone_paid=비요른:-100" in prompt

    def test_noise_side_effects_filtered(self) -> None:
        """significant 본격 prefix 본격 본격 side_effect 본격 본격 X (★ noise 제거)."""
        prompt = GMAgent._build_user_prompt_v2(
            _make_action(),
            "mech",
            [
                "시간 0.5h 경과",
                "가시거리 10.0m",
                "지속 72.0h",
            ],
            self._ctx(),
        )
        # significant section 본격 본격 본격 — noise 본격 본격 본격 본격 X
        assert "시간 0.5h" not in prompt
        assert "가시거리" not in prompt

    def test_active_encounters_in_prompt(self) -> None:
        h = _V2StateHolder()
        h.active_encounters.append(
            Encounter(
                type=EncounterType.NPC_PEACEFUL,
                name="우호 탐험가",
                location="loc",
                spawned_at_turn=0,
                ttl_turns=5,
            )
        )
        ctx = _build_v2_ctx(h)
        prompt = GMAgent._build_user_prompt_v2(
            _make_action(), "mech", [], ctx
        )
        assert "우호 탐험가" in prompt

    def test_narrative_instruction_present(self) -> None:
        prompt = GMAgent._build_user_prompt_v2(
            _make_action(), "mech", [], self._ctx()
        )
        # 작성 지시 본격 본격 본격 본격
        assert "narrative" in prompt or "본문" in prompt


# ─── ActionResponse.narrative integration ───


class TestActionResponseNarrative:
    def test_default_none(self) -> None:
        from service.api.v2_state_router import ActionResponse

        r = ActionResponse(
            success=True,
            message="m",
            side_effects=[],
            state={},
            turn=1,
        )
        assert r.narrative is None
        assert r.encounters == []

    def test_with_narrative(self) -> None:
        from service.api.v2_state_router import ActionResponse

        r = ActionResponse(
            success=True,
            message="m",
            side_effects=[],
            state={},
            turn=1,
            narrative="한국어 narrative",
        )
        assert r.narrative == "한국어 narrative"


# ─── post_action integration (★ TestClient) ───


class TestPostActionWithNarrate:
    def test_fail_action_no_narrative(self) -> None:
        """unknown_action 본격 본격 본격 narrative 본격 본격 X (★ 400)."""
        from fastapi.testclient import TestClient

        from service.api.app import app

        client = TestClient(app)
        client.post("/api/v2/state/reset")
        response = client.post(
            "/api/v2/action",
            json={"action_type": "nonexistent"},
        )
        assert response.status_code == 400

    def test_success_silent_fallback_no_narrative(self) -> None:
        """LLM 실패 본격 narrative=None / mechanical 본격 본격."""
        from fastapi.testclient import TestClient

        from service.api.app import app
        from service.api.v2_state_router import get_holder

        client = TestClient(app)
        client.post("/api/v2/state/reset")
        h = get_holder()

        # narrator 본격 fail 본격 본격
        class _FailingNarrator:
            def narrate_action_v2(
                self, action: Any, msg: str, se: list[str], ctx: dict[str, Any]
            ) -> str:
                raise RuntimeError("LLM down")

        h._gm_narrator = _FailingNarrator()  # type: ignore[assignment]
        try:
            with patch(
                "service.api.v2_state_router._maybe_spawn_encounters"
            ):  # encounter LLM 본격 본격 본격
                response = client.post(
                    "/api/v2/action",
                    json={"action_type": "explore", "actor": "비요른"},
                )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["narrative"] is None  # ★ silent fallback
            assert data["message"]  # mechanical 본격 본격 본격
        finally:
            h.reset()
            h._gm_narrator = None
