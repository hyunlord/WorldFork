"""진짜 LLM PlayerAgent 단위 테스트 (★ 2차 commit).

LLM 호출 X — Mock LLMClient로 응답 진짜 검증.
"""

from __future__ import annotations

from typing import Any

from core.llm.client import LLMClient, LLMResponse, Prompt
from service.sim.player_agent import (
    PlayerAgent,
    _build_player_prompt,
    _parse_action_json,
)
from service.sim.types import PlayerActionType


class _MockLLMClient(LLMClient):
    """Mock LLMClient (★ 단위 테스트용)."""

    def __init__(self, response_text: str, model: str = "mock-9b") -> None:
        self._text = response_text
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text=self._text,
            model=self._model,
            cost_usd=0.0,
            latency_ms=100,
            input_tokens=0,
            output_tokens=0,
        )


# ─── _parse_action_json ───


def test_parse_action_json_basic() -> None:
    text = (
        '{"action_type": "activate_light", "target": "횃불", '
        '"rationale": "어둠 본질"}'
    )
    action = _parse_action_json(text, "비요른")

    assert action.action_type == PlayerActionType.ACTIVATE_LIGHT
    assert action.target == "횃불"
    assert action.rationale == "어둠 본질"
    assert action.actor_name == "비요른"


def test_parse_action_json_with_code_block() -> None:
    """LLM 가끔 ```json ...``` 코드블록 출력."""
    text = '```json\n{"action_type": "wait", "target": null}\n```'
    action = _parse_action_json(text, "X")
    assert action.action_type == PlayerActionType.WAIT


def test_parse_action_json_invalid_action_type_falls_back() -> None:
    text = '{"action_type": "invalid_action", "target": null}'
    action = _parse_action_json(text, "X")
    assert action.action_type == PlayerActionType.WAIT


def test_parse_action_json_malformed_falls_back() -> None:
    """JSON parsing 실패 시 WAIT."""
    action = _parse_action_json("이건 JSON이 아님", "비요른")
    assert action.action_type == PlayerActionType.WAIT
    assert "[parse_failed]" in action.rationale


def test_parse_action_json_with_extra_text() -> None:
    """JSON 앞뒤에 텍스트 있어도 추출."""
    text = (
        '응답: {"action_type": "move", "target": "북쪽 통로", '
        '"rationale": ""} 끝.'
    )
    action = _parse_action_json(text, "X")
    assert action.action_type == PlayerActionType.MOVE
    assert action.target == "북쪽 통로"


# ─── _build_player_prompt ───


def test_build_player_prompt_includes_actor() -> None:
    ctx = {
        "v2_characters": {
            "비요른": {
                "race": "바바리안",
                "hp": 150,
                "hp_max": 150,
                "physical": 14,
                "mental": 14,
                "special": 8,
                "strength": 16,
                "agility": 10,
            },
        },
        "v2_initial_location": {
            "realm": "미궁",
            "floor": 1,
            "sub_area": "진입점",
            "visibility_meters": 10,
            "has_light": False,
        },
        "v2_world_state": {
            "hours_in_dungeon": 0,
            "is_dark_zone": True,
        },
    }
    prompt = _build_player_prompt("비요른", ctx)

    assert "비요른" in prompt
    assert "바바리안" in prompt
    assert "150" in prompt
    assert "미궁" in prompt
    assert "어둠" in prompt


# ─── PlayerAgent ───


def test_player_agent_generate_action_basic() -> None:
    """PlayerAgent → JSON 응답 → PlayerAction."""
    mock_client = _MockLLMClient(
        '{"action_type": "activate_light", "target": "횃불", '
        '"rationale": "어둠"}'
    )
    agent = PlayerAgent(mock_client)

    response = agent.generate_action("비요른", {})

    assert response.action.action_type == PlayerActionType.ACTIVATE_LIGHT
    assert response.action.target == "횃불"
    assert response.action.actor_name == "비요른"


def test_player_agent_handles_malformed_response() -> None:
    """LLM 응답 비정상이어도 안전."""
    mock_client = _MockLLMClient("이건 JSON 아님")
    agent = PlayerAgent(mock_client)

    response = agent.generate_action("X", {})
    assert response.action.action_type == PlayerActionType.WAIT


def test_player_agent_model_name() -> None:
    mock_client = _MockLLMClient("{}", model="qwen35-9b-q3-test")
    agent = PlayerAgent(mock_client)
    assert agent.model_name == "qwen35-9b-q3-test"
