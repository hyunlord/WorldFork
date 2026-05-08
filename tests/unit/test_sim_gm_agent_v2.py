"""SimGMAgent v2 본격 보강 검증 (★ A. encounter 빈도/다양/누적).

본 commit:
- last_encounter_types tracking + reset_history
- 직전 type prompt 출력
- TTL 만료 검증
- ENCOUNTER_TTL 본문 본질 정합
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from core.llm.client import LLMResponse
from service.sim.sim_gm_agent import (
    SIM_GM_SYSTEM_PROMPT,
    SimGMAgent,
    _build_gm_prompt,
)
from service.sim.types import (
    ENCOUNTER_TTL,
    Encounter,
    EncounterType,
)


def test_system_prompt_contains_diversity_enforcement() -> None:
    """다양 강제 본격 명시."""
    p = SIM_GM_SYSTEM_PROMPT
    assert "본격 다양 강제" in p
    assert "직전 spawn type" in p
    assert "연속" in p
    assert "type rotation" in p


def test_system_prompt_contains_increased_frequency() -> None:
    """빈도 ↑ 본격 (★ 70/80/85%)."""
    p = SIM_GM_SYSTEM_PROMPT
    assert "70%" in p
    assert "80%" in p
    assert "85%" in p


def test_build_prompt_includes_last_types() -> None:
    """직전 type 본격 출력."""
    ctx: dict[str, Any] = {
        "v2_characters": {},
        "v2_world_state": {"hours_in_dungeon": 5},
        "v2_initial_location": {"sub_area": "수정 동굴"},
    }
    p = _build_gm_prompt(
        turn_number=10,
        ctx=ctx,
        last_encounter_types=["essence", "essence", "monster"],
    )
    assert "직전 spawn types" in p
    assert "essence" in p
    assert "monster" in p
    assert "절대 금지" in p


def test_build_prompt_no_last_types() -> None:
    """직전 X 시 본격 출력 X."""
    ctx: dict[str, Any] = {
        "v2_characters": {},
        "v2_world_state": {"hours_in_dungeon": 0},
        "v2_initial_location": {"sub_area": "진입점"},
    }
    p = _build_gm_prompt(turn_number=1, ctx=ctx, last_encounter_types=None)
    assert "직전 spawn types" not in p


def test_gm_agent_tracks_last_types() -> None:
    """SimGMAgent 직전 type tracking + reset_history 본격."""
    mock_llm = MagicMock()
    mock_llm.model_name = "qwen36_27b_q2"
    mock_llm.generate.return_value = LLMResponse(
        text=(
            '{"encounters": [{"type": "essence", "name": "청록색 정수", '
            '"location": "수정 동굴"}], "narrative": "..."}'
        ),
        model="qwen36_27b_q2",
        cost_usd=0.0,
        latency_ms=200,
        input_tokens=100,
        output_tokens=50,
        raw={},
    )

    agent = SimGMAgent(llm_client=mock_llm)
    agent.generate_encounters(
        1,
        {
            "v2_characters": {},
            "v2_world_state": {"hours_in_dungeon": 1},
            "v2_initial_location": {"sub_area": "수정 동굴"},
        },
    )

    assert "essence" in agent._last_encounter_types

    agent.reset_history()
    assert agent._last_encounter_types == []


def test_encounter_ttl_essence_30() -> None:
    """ESSENCE TTL 30분 (★ 13/14화 본문)."""
    assert ENCOUNTER_TTL[EncounterType.ESSENCE] == 30


def test_encounter_is_expired() -> None:
    """TTL 만료 검증 본격."""
    e = Encounter(
        type=EncounterType.ESSENCE,
        name="청록색 정수",
        location="수정 동굴",
        description="...",
        spawned_at_turn=10,
        ttl_turns=30,
    )

    assert not e.is_expired(15)  # 5턴 후, 미만료
    assert not e.is_expired(39)  # 29턴 후, 미만료
    assert e.is_expired(40)      # 30턴 후, 만료
    assert e.is_expired(100)     # 90턴 후, 만료


def test_encounter_ttl_per_type() -> None:
    """type별 TTL 본격."""
    assert ENCOUNTER_TTL[EncounterType.MONSTER] == 5
    assert ENCOUNTER_TTL[EncounterType.RIFT] == 100
    assert ENCOUNTER_TTL[EncounterType.NARRATIVE] == 1
    assert ENCOUNTER_TTL[EncounterType.ITEM] == 50
    assert ENCOUNTER_TTL[EncounterType.EVENT] == 3
