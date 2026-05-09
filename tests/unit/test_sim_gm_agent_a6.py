"""SimGMAgent v3 본격 enforcement 검증 (★ A.6 server-side).

본 commit 본격 (★ A.6):
- _detect_dominant_types (★ Step B 본격)
- _is_violation (★ Step A 본격)
- _build_forbidden_section (★ 동적 prompt 본격)
- _make_fallback_response (★ Step C 본격)
- SimGMAgent retry / fallback / enforcement_stats 본격
"""

from __future__ import annotations

from unittest.mock import MagicMock

from core.llm.client import LLMResponse
from service.sim.sim_gm_agent import (
    DOMINANCE_THRESHOLD,
    DOMINANCE_TYPES_TO_REJECT,
    DOMINANCE_WINDOW,
    FALLBACK_NARRATIVE,
    MAX_RETRY_COUNT,
    SimGMAgent,
    _build_forbidden_section,
    _detect_dominant_types,
    _is_violation,
    _make_fallback_response,
)
from service.sim.types import Encounter, EncounterType

# ─── _detect_dominant_types ───


def test_detect_dominant_types_threshold() -> None:
    """60%+ 시 dominance."""
    types = ["essence", "essence", "essence", "monster", "rift"]
    dom = _detect_dominant_types(types, window=5, threshold=0.6)
    assert "essence" in dom


def test_detect_dominant_types_consecutive() -> None:
    """3+ 같은 type 시 dominance."""
    types = ["essence", "essence", "essence", "monster"]
    dom = _detect_dominant_types(types, window=4, threshold=0.99)
    assert "essence" in dom


def test_detect_dominant_types_no_dominance() -> None:
    """다양 분포 시 dominance X."""
    types = ["essence", "monster", "rift", "item", "event"]
    dom = _detect_dominant_types(types)
    assert dom == []


def test_detect_dominant_types_empty() -> None:
    assert _detect_dominant_types([]) == []


def test_detect_dominant_types_single() -> None:
    """단 1개일 땐 dominance X (★ window < 2)."""
    assert _detect_dominant_types(["essence"]) == []


def test_detect_dominant_types_uses_module_constants() -> None:
    """default window/threshold가 모듈 상수와 일치."""
    assert DOMINANCE_WINDOW == 5
    assert DOMINANCE_THRESHOLD == 0.6
    assert DOMINANCE_TYPES_TO_REJECT == 3


# ─── _build_forbidden_section ───


def test_build_forbidden_section_with_last_type() -> None:
    s = _build_forbidden_section(last_type="essence", dominant_types=[])
    assert "essence" in s
    assert "직전 turn과 같음" in s


def test_build_forbidden_section_with_dominance() -> None:
    s = _build_forbidden_section(
        last_type="monster",
        dominant_types=["essence", "monster"],
    )
    assert "essence" in s
    assert "monster" in s
    # monster가 last_type이라 dominance 줄에 중복 X
    assert s.count("monster") == 1
    assert "dominance" in s


def test_build_forbidden_section_empty() -> None:
    s = _build_forbidden_section(last_type=None, dominant_types=[])
    assert "자유 spawn" in s


# ─── _is_violation ───


def _enc(t: EncounterType) -> Encounter:
    return Encounter(type=t, name="?", location="?", description="")


def test_is_violation_same_as_last() -> None:
    """직전 type과 같으면 위반."""
    encs = [_enc(EncounterType.ESSENCE)]
    violation, reason = _is_violation(
        encs, last_type="essence", dominant_types=[]
    )
    assert violation
    assert "essence" in reason


def test_is_violation_dominance() -> None:
    """dominance type 본격 위반."""
    encs = [_enc(EncounterType.ESSENCE)]
    violation, _ = _is_violation(
        encs, last_type="monster", dominant_types=["essence"]
    )
    assert violation


def test_is_violation_narrative_always_ok() -> None:
    """narrative-only는 항상 OK."""
    encs = [_enc(EncounterType.NARRATIVE)]
    violation, _ = _is_violation(
        encs, last_type="essence", dominant_types=["essence"]
    )
    assert not violation


def test_is_violation_no_constraints() -> None:
    """직전 X / dominance X면 통과."""
    encs = [_enc(EncounterType.ESSENCE)]
    violation, _ = _is_violation(encs, last_type=None, dominant_types=[])
    assert not violation


def test_is_violation_empty_encounters() -> None:
    """빈 encounters는 위반 X."""
    violation, _ = _is_violation([], last_type="essence", dominant_types=[])
    assert not violation


def test_is_violation_mixed_some_forbidden() -> None:
    """forbidden type 본격 1개라도 있으면 위반."""
    encs = [
        _enc(EncounterType.MONSTER),
        _enc(EncounterType.ESSENCE),
    ]
    violation, _ = _is_violation(
        encs, last_type="essence", dominant_types=[]
    )
    assert violation


# ─── _make_fallback_response ───


def test_make_fallback_response() -> None:
    """fallback narrative 본격."""
    r = _make_fallback_response()
    assert len(r.encounters) == 1
    assert r.encounters[0].type == EncounterType.NARRATIVE
    assert r.cost_usd == 0.0
    assert r.latency_ms == 0
    assert FALLBACK_NARRATIVE == r.narrative


# ─── SimGMAgent ───


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


def _empty_ctx() -> dict[str, object]:
    """EXPLORE phase ctx (★ ESSENCE / MONSTER / ITEM 본격 OK).

    F commit 본격: phase mismatch 본격 차단 위해 EXPLORE (h=10) 사용.
    """
    return {
        "v2_characters": {},
        "v2_world_state": {"hours_in_dungeon": 10},
        "v2_initial_location": {"sub_area": "?"},
    }


def test_gm_agent_passes_when_no_violation() -> None:
    """rule 통과 시 LLM 응답 그대로."""
    mock_llm = _mock_llm()
    mock_llm.generate.return_value = _llm_resp(
        '{"encounters": [{"type": "monster", "name": "고블린", '
        '"location": "북쪽"}], "narrative": ""}'
    )

    agent = SimGMAgent(llm_client=mock_llm)
    response = agent.generate_encounters(1, _empty_ctx())

    assert len(response.encounters) == 1
    assert response.encounters[0].type == EncounterType.MONSTER
    assert mock_llm.generate.call_count == 1
    assert agent.enforcement_stats == {
        "retry_count": 0,
        "fallback_count": 0,
        "phase_mismatch_count": 0,
    }


def test_gm_agent_retries_on_violation() -> None:
    """위반 시 retry → 통과."""
    mock_llm = _mock_llm()
    # 첫 호출 = essence (위반), 둘째 = monster (OK)
    mock_llm.generate.side_effect = [
        _llm_resp(
            '{"encounters": [{"type": "essence", "name": "정수", '
            '"location": "?"}], "narrative": ""}'
        ),
        _llm_resp(
            '{"encounters": [{"type": "monster", "name": "고블린", '
            '"location": "?"}], "narrative": ""}'
        ),
    ]

    agent = SimGMAgent(llm_client=mock_llm)
    agent._last_encounter_types = ["essence"]  # 직전 essence

    response = agent.generate_encounters(2, _empty_ctx())

    assert response.encounters[0].type == EncounterType.MONSTER
    assert mock_llm.generate.call_count == 2
    assert agent.enforcement_stats == {
        "retry_count": 1,
        "fallback_count": 0,
        "phase_mismatch_count": 0,
    }


def test_gm_agent_fallback_after_max_retry() -> None:
    """retry 모두 실패 시 fallback narrative 본격."""
    mock_llm = _mock_llm()
    # 모든 호출 = essence (위반)
    mock_llm.generate.return_value = _llm_resp(
        '{"encounters": [{"type": "essence", "name": "정수", '
        '"location": "?"}], "narrative": ""}'
    )

    agent = SimGMAgent(llm_client=mock_llm, max_retry=2)
    agent._last_encounter_types = ["essence"]

    response = agent.generate_encounters(3, _empty_ctx())

    # fallback narrative 본격
    assert len(response.encounters) == 1
    assert response.encounters[0].type == EncounterType.NARRATIVE
    # 1 + 2 retry = 3 호출
    assert mock_llm.generate.call_count == 3
    assert agent.enforcement_stats == {
        "retry_count": 2,
        "fallback_count": 1,
        "phase_mismatch_count": 0,
    }

    # 직전 type tracking에 narrative 본격 추가
    assert agent._last_encounter_types[-1] == "narrative"


def test_gm_agent_fallback_accumulates_cost_and_latency() -> None:
    """fallback 시 비용/지연 retry 횟수만큼 누적 측정."""
    mock_llm = _mock_llm()
    mock_llm.generate.return_value = LLMResponse(
        text='{"encounters": [{"type": "essence", "name": "?", '
        '"location": "?"}], "narrative": ""}',
        model="x",
        cost_usd=0.5,
        latency_ms=100,
        input_tokens=10,
        output_tokens=10,
        raw={},
    )

    agent = SimGMAgent(llm_client=mock_llm, max_retry=2)
    agent._last_encounter_types = ["essence"]

    response = agent.generate_encounters(1, _empty_ctx())

    # 3 attempts × 0.5 = 1.5, × 100 = 300
    assert response.cost_usd == 1.5
    assert response.latency_ms == 300


def test_gm_agent_enforcement_stats_initial() -> None:
    """초기 metrics 본격 0."""
    agent = SimGMAgent(llm_client=_mock_llm())
    assert agent.enforcement_stats == {
        "retry_count": 0,
        "fallback_count": 0,
        "phase_mismatch_count": 0,
    }


def test_gm_agent_reset_history_clears_metrics() -> None:
    """reset_history 시 metrics 본격 reset."""
    agent = SimGMAgent(llm_client=_mock_llm())
    agent._retry_count_total = 5
    agent._fallback_count = 2
    agent._last_encounter_types = ["essence", "monster"]

    agent.reset_history()

    assert agent._last_encounter_types == []
    assert agent.enforcement_stats == {
        "retry_count": 0,
        "fallback_count": 0,
        "phase_mismatch_count": 0,
    }


def test_gm_agent_default_max_retry_matches_constant() -> None:
    """default max_retry가 모듈 상수와 일치."""
    agent = SimGMAgent(llm_client=_mock_llm())
    assert agent.max_retry == MAX_RETRY_COUNT


def test_gm_agent_tracks_recent_types_window() -> None:
    """_last_encounter_types 본격 10개 유지."""
    mock_llm = _mock_llm()
    # 매번 OK인 type을 번갈아 — 직전 type 회피
    types_cycle = ["monster", "essence"] * 8
    mock_llm.generate.side_effect = [
        _llm_resp(
            f'{{"encounters": [{{"type": "{t}", "name": "?", '
            f'"location": "?"}}], "narrative": ""}}'
        )
        for t in types_cycle
    ]

    agent = SimGMAgent(llm_client=mock_llm)
    for i in range(16):
        agent.generate_encounters(i + 1, _empty_ctx())

    # window 10 본격 유지
    assert len(agent._last_encounter_types) == 10
