"""SimGMAgent v4 본격 phase enforcement 검증 (★ F commit).

본 commit 본격:
- DungeonPhase enum + determine_phase (★ Step A)
- PHASE_TYPE_WEIGHTS / PHASE_PRIORITY_TYPES / PHASE_SPAWN_FREQUENCY (★ Step B)
- _build_phase_section (★ 동적 prompt)
- _is_phase_mismatch (★ Step C 검증)
- SimGMAgent v4 phase + A.6 통합 enforcement
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from core.llm.client import LLMResponse
from service.sim.sim_gm_agent import (
    PHASE_MISMATCH_WEIGHT_THRESHOLD,
    SimGMAgent,
    _build_phase_section,
    _is_phase_mismatch,
)
from service.sim.types import (
    PHASE_PRIORITY_TYPES,
    PHASE_SPAWN_FREQUENCY,
    PHASE_TYPE_WEIGHTS,
    DungeonPhase,
    Encounter,
    EncounterType,
    determine_phase,
)

# ─── determine_phase ───


def test_determine_phase_entry() -> None:
    """G commit (★ 본 commit base): h<2 ENTRY (★ F의 h<5 완화)."""
    assert determine_phase(0) == DungeonPhase.ENTRY
    assert determine_phase(1) == DungeonPhase.ENTRY


def test_determine_phase_explore() -> None:
    """G commit: 2≤h<24 EXPLORE."""
    assert determine_phase(2) == DungeonPhase.EXPLORE
    assert determine_phase(23) == DungeonPhase.EXPLORE


def test_determine_phase_combat() -> None:
    assert determine_phase(24) == DungeonPhase.COMBAT
    assert determine_phase(71) == DungeonPhase.COMBAT


def test_determine_phase_rift() -> None:
    assert determine_phase(72) == DungeonPhase.RIFT
    assert determine_phase(167) == DungeonPhase.RIFT


# ─── PHASE_TYPE_WEIGHTS / PRIORITY / FREQUENCY ───


def test_phase_type_weights_sum_close_to_1() -> None:
    """각 phase의 weights 합 ~1.0 (★ 본격 본질)."""
    for phase, weights in PHASE_TYPE_WEIGHTS.items():
        total = sum(weights.values())
        assert 0.95 <= total <= 1.05, f"{phase}: sum={total}"


def test_phase_priority_types_complete() -> None:
    """모든 phase에 priority types 본격."""
    for phase in DungeonPhase:
        assert phase in PHASE_PRIORITY_TYPES
        assert len(PHASE_PRIORITY_TYPES[phase]) >= 3


def test_phase_spawn_frequency_increases() -> None:
    """phase 진행 시 spawn 빈도 본격 증가."""
    assert (
        PHASE_SPAWN_FREQUENCY[DungeonPhase.ENTRY]
        < PHASE_SPAWN_FREQUENCY[DungeonPhase.EXPLORE]
        < PHASE_SPAWN_FREQUENCY[DungeonPhase.COMBAT]
        < PHASE_SPAWN_FREQUENCY[DungeonPhase.RIFT]
    )


def test_phase_priority_first_matches_top_weight() -> None:
    """각 phase priority[0]는 top-weight type."""
    for phase, weights in PHASE_TYPE_WEIGHTS.items():
        top_type = max(weights, key=lambda t: weights[t])
        assert PHASE_PRIORITY_TYPES[phase][0] == top_type


# ─── _build_phase_section ───


def test_build_phase_section_entry() -> None:
    s = _build_phase_section(hours_in_dungeon=0)
    assert "ENTRY" in s
    assert "narrative" in s.lower()
    assert "0h" in s


def test_build_phase_section_rift() -> None:
    s = _build_phase_section(hours_in_dungeon=100)
    assert "RIFT" in s
    assert "rift" in s.lower()
    assert "100h" in s


def test_build_phase_section_includes_weights() -> None:
    """phase section에 weight % 본격 명시."""
    s = _build_phase_section(hours_in_dungeon=10)  # EXPLORE
    # EXPLORE에서 essence 35%
    assert "35%" in s


# ─── _is_phase_mismatch ───


def _enc(t: EncounterType) -> Encounter:
    return Encounter(type=t, name="?", location="?", description="")


def test_is_phase_mismatch_rift_in_entry() -> None:
    """ENTRY phase에 RIFT spawn = mismatch (★ weight 0)."""
    encs = [_enc(EncounterType.RIFT)]
    v, r = _is_phase_mismatch(encs, DungeonPhase.ENTRY)
    assert v
    assert "rift" in r.lower()


def test_is_phase_mismatch_monster_in_entry() -> None:
    """ENTRY phase에 MONSTER spawn = mismatch (★ weight 0)."""
    encs = [_enc(EncounterType.MONSTER)]
    v, _ = _is_phase_mismatch(encs, DungeonPhase.ENTRY)
    assert v


def test_is_phase_mismatch_essence_in_explore_ok() -> None:
    """EXPLORE phase에 ESSENCE spawn = OK."""
    encs = [_enc(EncounterType.ESSENCE)]
    v, _ = _is_phase_mismatch(encs, DungeonPhase.EXPLORE)
    assert not v


def test_is_phase_mismatch_rift_in_rift_ok() -> None:
    """RIFT phase에 RIFT spawn = OK."""
    encs = [_enc(EncounterType.RIFT)]
    v, _ = _is_phase_mismatch(encs, DungeonPhase.RIFT)
    assert not v


def test_is_phase_mismatch_narrative_always_ok() -> None:
    """NARRATIVE은 phase 무관 OK (★ A.6 mirror 안전)."""
    encs = [_enc(EncounterType.NARRATIVE)]
    for phase in DungeonPhase:
        v, _ = _is_phase_mismatch(encs, phase)
        assert not v, f"{phase} narrative should be OK"


def test_is_phase_mismatch_empty_ok() -> None:
    v, _ = _is_phase_mismatch([], DungeonPhase.ENTRY)
    assert not v


def test_is_phase_mismatch_threshold_constant() -> None:
    """모듈 상수 본격 노출 (★ tunable)."""
    assert PHASE_MISMATCH_WEIGHT_THRESHOLD > 0
    assert PHASE_MISMATCH_WEIGHT_THRESHOLD < 0.1


# ─── SimGMAgent v4 ───


def _llm_resp(text: str) -> LLMResponse:
    return LLMResponse(
        text=text,
        model="qwen36_27b_q2",
        cost_usd=0.0,
        latency_ms=200,
        input_tokens=100,
        output_tokens=50,
        raw={},
    )


def _mock_llm() -> MagicMock:
    mock = MagicMock()
    mock.model_name = "qwen36_27b_q2"
    return mock


def _ctx(hours: int) -> dict[str, Any]:
    return {
        "v2_characters": {},
        "v2_world_state": {"hours_in_dungeon": hours},
        "v2_initial_location": {"sub_area": "?"},
    }


def test_gm_agent_passes_phase_aware() -> None:
    """phase 정합 응답 통과 (★ RIFT phase + RIFT spawn)."""
    mock_llm = _mock_llm()
    mock_llm.generate.return_value = _llm_resp(
        '{"encounters": [{"type": "rift", "name": "핏빛성채", '
        '"location": "포탈"}], "narrative": ""}'
    )

    agent = SimGMAgent(llm_client=mock_llm)
    response = agent.generate_encounters(50, _ctx(hours=100))

    assert response.encounters[0].type == EncounterType.RIFT
    assert mock_llm.generate.call_count == 1
    assert agent.enforcement_stats["phase_mismatch_count"] == 0


def test_gm_agent_retries_on_phase_mismatch() -> None:
    """phase mismatch (ENTRY+RIFT) 시 retry → narrative 본격 통과."""
    mock_llm = _mock_llm()
    mock_llm.generate.side_effect = [
        _llm_resp(
            '{"encounters": [{"type": "rift", "name": "?", '
            '"location": "?"}], "narrative": ""}'
        ),
        _llm_resp(
            '{"encounters": [{"type": "narrative", "name": "고요", '
            '"location": "?"}], "narrative": ""}'
        ),
    ]

    agent = SimGMAgent(llm_client=mock_llm)
    response = agent.generate_encounters(1, _ctx(hours=0))

    assert response.encounters[0].type == EncounterType.NARRATIVE
    assert mock_llm.generate.call_count == 2
    assert agent.enforcement_stats["phase_mismatch_count"] == 1
    assert agent.enforcement_stats["retry_count"] == 1


def test_gm_agent_enforcement_stats_includes_phase() -> None:
    """enforcement_stats에 phase_mismatch_count 본격."""
    agent = SimGMAgent(llm_client=_mock_llm())
    stats = agent.enforcement_stats

    assert "phase_mismatch_count" in stats
    assert stats["phase_mismatch_count"] == 0
    # A.6 metrics 본격 보존
    assert "retry_count" in stats
    assert "fallback_count" in stats


def test_gm_agent_reset_clears_phase_metric() -> None:
    """reset 시 phase metric 본격 reset (★ A.6 backward compat)."""
    agent = SimGMAgent(llm_client=_mock_llm())
    agent._phase_mismatch_count = 5
    agent._retry_count_total = 3
    agent._fallback_count = 1
    agent._last_encounter_types = ["essence"]

    agent.reset_history()

    assert agent.enforcement_stats == {
        "retry_count": 0,
        "fallback_count": 0,
        "phase_mismatch_count": 0,
    }
    assert agent._last_encounter_types == []


def test_gm_agent_phase_fallback_after_max_retry() -> None:
    """phase mismatch 모두 retry 실패 → fallback narrative."""
    mock_llm = _mock_llm()
    # ENTRY phase에 항상 RIFT (mismatch)
    mock_llm.generate.return_value = _llm_resp(
        '{"encounters": [{"type": "rift", "name": "?", '
        '"location": "?"}], "narrative": ""}'
    )

    agent = SimGMAgent(llm_client=mock_llm, max_retry=2)
    response = agent.generate_encounters(1, _ctx(hours=0))

    # fallback narrative
    assert response.encounters[0].type == EncounterType.NARRATIVE
    # phase mismatch 3회 (★ 모든 attempt)
    assert agent.enforcement_stats["phase_mismatch_count"] == 3
    assert agent.enforcement_stats["fallback_count"] == 1
