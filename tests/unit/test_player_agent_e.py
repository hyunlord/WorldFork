"""PlayerAgent v3 본격 enforcement 검증 (★ E, A.6 mirror).

본 commit 본격:
- _detect_dominant_actions (★ Step B)
- _is_consecutive_violation / _is_action_violation (★ Step A)
- _build_forbidden_action_section / _build_required_action_section (★ Step C)
- _make_fallback_action (★ Step D)
- PlayerAgent retry / fallback / enforcement_stats 본격
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from core.llm.client import LLMResponse
from service.sim.player_agent import (
    ACTION_DOMINANCE_THRESHOLD,
    ACTION_DOMINANCE_WINDOW,
    ENCOUNTER_REQUIRED_ACTIONS,
    FALLBACK_ACTIONS_BY_PRIORITY,
    LAST_ACTIONS_WINDOW,
    MAX_PLAYER_RETRY_COUNT,
    PlayerAgent,
    _build_forbidden_action_section,
    _build_required_action_section,
    _detect_dominant_actions,
    _is_action_violation,
    _is_consecutive_violation,
    _make_fallback_action,
)
from service.sim.types import PlayerActionType

# ─── _detect_dominant_actions ───


def test_detect_dominant_actions_threshold() -> None:
    """50%+ dominance."""
    actions = ["absorb_essence"] * 5 + ["activate_light"] * 3
    dom = _detect_dominant_actions(actions, window=8, threshold=0.5)
    assert "absorb_essence" in dom


def test_detect_dominant_actions_count() -> None:
    """5+ 같은 ActionType."""
    actions = ["absorb_essence"] * 5 + ["explore"] * 3
    dom = _detect_dominant_actions(actions)
    assert "absorb_essence" in dom


def test_detect_dominant_actions_balanced() -> None:
    """다양 분포 X dominance."""
    actions = [
        "absorb_essence",
        "attack",
        "move",
        "explore",
        "rest",
        "wait",
        "flee",
        "use_item",
    ]
    dom = _detect_dominant_actions(actions)
    assert dom == []


def test_detect_dominant_actions_empty() -> None:
    assert _detect_dominant_actions([]) == []


def test_detect_dominant_actions_too_short() -> None:
    """history < 3 → dominance X."""
    assert _detect_dominant_actions(["absorb_essence", "absorb_essence"]) == []


def test_detect_dominant_actions_uses_module_constants() -> None:
    assert ACTION_DOMINANCE_WINDOW == 8
    assert ACTION_DOMINANCE_THRESHOLD == 0.5


# ─── _is_consecutive_violation ───


def test_is_consecutive_violation_3_in_a_row() -> None:
    """직전 3 같음 → 4번째 본격 X."""
    actions = ["absorb_essence"] * 3
    assert _is_consecutive_violation(actions, "absorb_essence")


def test_is_consecutive_violation_different() -> None:
    """직전 같음 + new 다름 → OK."""
    actions = ["absorb_essence"] * 3
    assert not _is_consecutive_violation(actions, "attack")


def test_is_consecutive_violation_short_history() -> None:
    """history < max_consecutive → OK."""
    actions = ["absorb_essence"]
    assert not _is_consecutive_violation(actions, "absorb_essence")


def test_is_consecutive_violation_mixed_history() -> None:
    """history 안 다른 ActionType 있음 → OK."""
    actions = ["absorb_essence", "attack", "absorb_essence"]
    assert not _is_consecutive_violation(actions, "absorb_essence")


# ─── _is_action_violation ───


def test_is_action_violation_consecutive() -> None:
    """3+ 연속 위반."""
    actions = ["absorb_essence"] * 3
    v, _ = _is_action_violation("absorb_essence", actions, [])
    assert v


def test_is_action_violation_dominance() -> None:
    v, r = _is_action_violation("absorb_essence", [], ["absorb_essence"])
    assert v
    assert "dominance" in r


def test_is_action_violation_clean() -> None:
    v, _ = _is_action_violation(
        "attack", ["absorb_essence", "absorb_essence"], []
    )
    assert not v


def test_is_action_violation_no_constraints() -> None:
    v, _ = _is_action_violation("attack", [], [])
    assert not v


# ─── _build_forbidden_action_section ───


def test_build_forbidden_with_last_action() -> None:
    s = _build_forbidden_action_section(
        last_action="absorb_essence",
        dominant_actions=[],
    )
    assert "absorb_essence" in s
    assert "연속" in s


def test_build_forbidden_with_dominance() -> None:
    s = _build_forbidden_action_section(
        last_action="explore",
        dominant_actions=["absorb_essence", "explore"],
    )
    assert "absorb_essence" in s
    assert "explore" in s
    # explore는 last_action이라 dominance 줄에 중복 X
    assert s.count("explore") == 1
    assert "dominance" in s


def test_build_forbidden_empty() -> None:
    s = _build_forbidden_action_section(last_action=None, dominant_actions=[])
    assert "자유 결정" in s


# ─── _build_required_action_section ───


def test_build_required_essence() -> None:
    """ESSENCE encounter → ABSORB_ESSENCE."""
    encs = [{"type": "essence", "name": "청록색 정수"}]
    s = _build_required_action_section(encs)
    assert "ABSORB_ESSENCE" in s
    assert "청록색 정수" in s


def test_build_required_monster() -> None:
    """MONSTER → ATTACK / FLEE / USE_ITEM."""
    encs = [{"type": "monster", "name": "고블린"}]
    s = _build_required_action_section(encs)
    assert "ATTACK" in s
    assert "FLEE" in s


def test_build_required_rift() -> None:
    """RIFT → ENTER_RIFT / OFFER_TO_STONE / EXIT_RIFT."""
    encs = [{"type": "rift", "name": "핏빛성채"}]
    s = _build_required_action_section(encs)
    assert "ENTER_RIFT" in s
    assert "OFFER_TO_STONE" in s


def test_build_required_no_encounter() -> None:
    s = _build_required_action_section([])
    assert "encounter X" in s


def test_build_required_narrative_only() -> None:
    """narrative encounter → mapping X."""
    encs = [{"type": "narrative", "name": "고요"}]
    s = _build_required_action_section(encs)
    assert "narrative" in s


# ─── _make_fallback_action ───


def test_make_fallback_with_essence_encounter() -> None:
    """ESSENCE encounter → ABSORB_ESSENCE fallback."""
    encs = [{"type": "essence", "name": "정수"}]
    f = _make_fallback_action(
        actor_name="비요른",
        encounters=encs,
        last_actions=[],
        dominant_actions=[],
    )
    assert f.action_type == PlayerActionType.ABSORB_ESSENCE
    assert f.actor_name == "비요른"
    assert f.target == "정수"


def test_make_fallback_with_monster_encounter() -> None:
    """MONSTER encounter → ATTACK (★ 첫 priority)."""
    encs = [{"type": "monster", "name": "고블린"}]
    f = _make_fallback_action(
        actor_name="비요른",
        encounters=encs,
        last_actions=[],
        dominant_actions=[],
    )
    assert f.action_type == PlayerActionType.ATTACK


def test_make_fallback_with_dominance_skips_required() -> None:
    """ABSORB dominance 시 다른 ActionType."""
    encs = [{"type": "essence", "name": "정수"}]
    f = _make_fallback_action(
        actor_name="비요른",
        encounters=encs,
        last_actions=["absorb_essence"] * 5,
        dominant_actions=["absorb_essence"],
    )
    assert f.action_type != PlayerActionType.ABSORB_ESSENCE


def test_make_fallback_priority_list_when_no_encounter() -> None:
    """encounter X → priority list 본격."""
    f = _make_fallback_action(
        actor_name="비요른",
        encounters=[],
        last_actions=["absorb_essence"] * 5,
        dominant_actions=["absorb_essence"],
    )
    # absorb_essence dominance → priority next = attack
    assert f.action_type == PlayerActionType.ATTACK


def test_make_fallback_default_explore() -> None:
    """모든 priority dominance → 최후 EXPLORE."""
    all_priority = list(FALLBACK_ACTIONS_BY_PRIORITY)
    f = _make_fallback_action(
        actor_name="비요른",
        encounters=[],
        last_actions=[],
        dominant_actions=all_priority,
    )
    assert f.action_type == PlayerActionType.EXPLORE


def test_encounter_required_mapping_complete() -> None:
    """ENCOUNTER_REQUIRED_ACTIONS 본격 매핑."""
    assert "absorb_essence" in ENCOUNTER_REQUIRED_ACTIONS["essence"]
    assert "attack" in ENCOUNTER_REQUIRED_ACTIONS["monster"]
    assert "flee" in ENCOUNTER_REQUIRED_ACTIONS["monster"]
    assert "enter_rift" in ENCOUNTER_REQUIRED_ACTIONS["rift"]
    assert "use_item" in ENCOUNTER_REQUIRED_ACTIONS["item"]


# ─── PlayerAgent ───


def _llm_resp(text: str) -> LLMResponse:
    return LLMResponse(
        text=text,
        model="qwen35_9b_q3",
        cost_usd=0.0,
        latency_ms=200,
        input_tokens=100,
        output_tokens=50,
        raw={},
    )


def _mock_llm() -> MagicMock:
    mock = MagicMock()
    mock.model_name = "qwen35_9b_q3"
    return mock


def _ctx(
    has_light: bool = True,
    encounters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "race": "BARBARIAN",
                "has_active_light": has_light,
                "essence_slots_used": 0,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 5,
            "party_members": ["비요른"],
        },
        "v2_initial_location": {"sub_area": "수정 동굴"},
        "active_encounters": encounters or [],
    }


def test_player_agent_passes_when_no_violation() -> None:
    """rule 통과 시 LLM 응답 그대로."""
    mock_llm = _mock_llm()
    mock_llm.generate.return_value = _llm_resp(
        '{"action_type": "absorb_essence", "target": "정수", '
        '"rationale": "정수 흡수"}'
    )

    agent = PlayerAgent(llm_client=mock_llm)
    response = agent.generate_action(
        "비요른",
        _ctx(encounters=[{"type": "essence", "name": "정수"}]),
    )

    assert response.action.action_type == PlayerActionType.ABSORB_ESSENCE
    assert response.action.actor_name == "비요른"
    assert mock_llm.generate.call_count == 1
    assert agent.enforcement_stats == {"retry_count": 0, "fallback_count": 0}


def test_player_agent_retries_on_consecutive() -> None:
    """3+ 연속 위반 시 retry → 통과."""
    mock_llm = _mock_llm()
    mock_llm.generate.side_effect = [
        _llm_resp(
            '{"action_type": "absorb_essence", "rationale": "..."}'
        ),
        _llm_resp('{"action_type": "attack", "rationale": "..."}'),
    ]

    agent = PlayerAgent(llm_client=mock_llm)
    agent._last_actions = ["absorb_essence"] * 3  # 직전 3 연속

    response = agent.generate_action("비요른", _ctx())

    assert response.action.action_type == PlayerActionType.ATTACK
    assert mock_llm.generate.call_count == 2
    assert agent.enforcement_stats == {"retry_count": 1, "fallback_count": 0}


def test_player_agent_fallback_after_max_retry() -> None:
    """retry 모두 실패 시 fallback rule-based."""
    mock_llm = _mock_llm()
    mock_llm.generate.return_value = _llm_resp(
        '{"action_type": "absorb_essence", "rationale": "..."}'
    )

    agent = PlayerAgent(llm_client=mock_llm, max_retry=2)
    agent._last_actions = ["absorb_essence"] * 5  # dominance

    response = agent.generate_action(
        "비요른",
        _ctx(encounters=[{"type": "essence", "name": "정수"}]),
    )

    # absorb_essence dominance → fallback rule-based 다른 action
    assert response.action.action_type != PlayerActionType.ABSORB_ESSENCE
    assert mock_llm.generate.call_count == 3  # 1 + 2 retry
    assert agent.enforcement_stats == {"retry_count": 2, "fallback_count": 1}


def test_player_agent_fallback_accumulates_cost_and_latency() -> None:
    """fallback 시 비용/지연 retry 횟수만큼 누적."""
    mock_llm = _mock_llm()
    mock_llm.generate.return_value = LLMResponse(
        text='{"action_type": "absorb_essence", "rationale": "..."}',
        model="x",
        cost_usd=0.5,
        latency_ms=100,
        input_tokens=10,
        output_tokens=10,
        raw={},
    )

    agent = PlayerAgent(llm_client=mock_llm, max_retry=2)
    agent._last_actions = ["absorb_essence"] * 5

    response = agent.generate_action("비요른", _ctx())

    # 3 attempts × 0.5 = 1.5, × 100 = 300
    assert response.cost_usd == 1.5
    assert response.latency_ms == 300


def test_player_agent_enforcement_stats_initial() -> None:
    agent = PlayerAgent(llm_client=_mock_llm())
    assert agent.enforcement_stats == {"retry_count": 0, "fallback_count": 0}


def test_player_agent_reset_history_clears_metrics() -> None:
    agent = PlayerAgent(llm_client=_mock_llm())
    agent._retry_count_total = 5
    agent._fallback_count = 2
    agent._last_actions = ["explore"]

    agent.reset_history()

    assert agent._last_actions == []
    assert agent.enforcement_stats == {"retry_count": 0, "fallback_count": 0}


def test_player_agent_default_max_retry_matches_constant() -> None:
    agent = PlayerAgent(llm_client=_mock_llm())
    assert agent.max_retry == MAX_PLAYER_RETRY_COUNT


def test_player_agent_tracks_recent_actions_window() -> None:
    """_last_actions 본격 LAST_ACTIONS_WINDOW 유지."""
    mock_llm = _mock_llm()
    types_cycle = ["attack", "explore", "move", "wait"] * 8
    mock_llm.generate.side_effect = [
        _llm_resp(f'{{"action_type": "{t}", "rationale": "?"}}')
        for t in types_cycle
    ]

    agent = PlayerAgent(llm_client=mock_llm)
    for _ in range(20):
        agent.generate_action("비요른", _ctx())

    assert len(agent._last_actions) == LAST_ACTIONS_WINDOW
