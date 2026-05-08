"""SimGMAgent 단위 테스트.

본 commit (★ C — GM + Player 통합):
- _parse_gm_json 안전 검증
- _build_gm_prompt 컨텍스트 검증
- MockSimGMAgent / SimGMAgent 본격
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from core.llm.client import LLMResponse
from service.sim.sim_gm_agent import (
    SIM_GM_SYSTEM_PROMPT,
    MockSimGMAgent,
    SimGMAgent,
    _build_gm_prompt,
    _parse_gm_json,
)
from service.sim.types import EncounterType, GMResponse


def test_parse_gm_json_basic() -> None:
    text = (
        '{"encounters": [{"type": "essence", "name": "청록색 정수", '
        '"location": "수정 동굴", "description": "..."}],'
        '"narrative": "수정이 반짝인다."}'
    )
    encs, narr = _parse_gm_json(text)
    assert len(encs) == 1
    assert encs[0].type == EncounterType.ESSENCE
    assert encs[0].name == "청록색 정수"
    assert "수정" in narr


def test_parse_gm_json_codeblock() -> None:
    text = '```json\n{"encounters": [], "narrative": "어둠."}\n```'
    encs, narr = _parse_gm_json(text)
    assert encs == []
    assert narr == "어둠."


def test_parse_gm_json_empty_on_invalid() -> None:
    encs, narr = _parse_gm_json("잘못된 응답 X JSON")
    assert encs == []
    assert narr == ""


def test_parse_gm_json_unknown_type_to_narrative() -> None:
    text = (
        '{"encounters": [{"type": "unknown_type", "name": "?", '
        '"location": "?"}], "narrative": ""}'
    )
    encs, _ = _parse_gm_json(text)
    assert len(encs) == 1
    assert encs[0].type == EncounterType.NARRATIVE


def test_build_gm_prompt_includes_party_state() -> None:
    ctx: dict[str, Any] = {
        "v2_characters": {
            "비요른": {
                "hp": 150,
                "hp_max": 150,
                "has_active_light": True,
                "essence_slots_used": 2,
            }
        },
        "v2_world_state": {
            "hours_in_dungeon": 5,
            "party_members": ["비요른"],
        },
        "v2_initial_location": {
            "realm": "DUNGEON",
            "floor": 1,
            "sub_area": "수정 동굴",
        },
    }
    p = _build_gm_prompt(turn_number=10, ctx=ctx)
    assert "턴 10" in p
    assert "비요른" in p
    assert "수정 동굴" in p
    assert "5h" in p


def test_system_prompt_contains_floor1_essentials() -> None:
    p = SIM_GM_SYSTEM_PROMPT
    # 1층 본문 본질
    assert "노움" in p and "남쪽" in p  # 22화
    assert "수정 동굴" in p  # 109/151/478화
    assert "30분 자연 소멸" in p  # 13/14화
    assert "핏빛성채" in p  # 균열
    assert "9등급" in p
    # spawn 가이드 (★ A. encounter 보강 본격)
    assert "encounter spawn 빈도" in p
    assert "다양 강제" in p


def test_mock_gm_returns_predefined() -> None:
    mock = MockSimGMAgent(
        mock_responses=[
            GMResponse(encounters=[], narrative="첫 응답"),
            GMResponse(encounters=[], narrative="둘째 응답"),
        ]
    )
    r1 = mock.generate_encounters(1, {})
    r2 = mock.generate_encounters(2, {})
    assert r1.narrative == "첫 응답"
    assert r2.narrative == "둘째 응답"


def test_real_gm_with_mock_llm() -> None:
    mock_llm = MagicMock()
    mock_llm.model_name = "qwen36_27b_q2"
    mock_llm.generate.return_value = LLMResponse(
        text=(
            '{"encounters": [{"type": "monster", "name": "고블린", '
            '"location": "북쪽 통로", "description": "..."}], '
            '"narrative": "..."}'
        ),
        model="qwen36_27b_q2",
        cost_usd=0.0,
        latency_ms=200,
        input_tokens=100,
        output_tokens=50,
        raw={},
    )

    agent = SimGMAgent(llm_client=mock_llm)
    response = agent.generate_encounters(1, {})

    assert len(response.encounters) == 1
    assert response.encounters[0].type == EncounterType.MONSTER
    assert response.cost_usd == 0.0
    assert response.latency_ms == 200
    mock_llm.generate.assert_called_once()
