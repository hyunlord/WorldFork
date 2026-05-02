"""W2 D3 작업 4: Planning Agent 테스트."""

from typing import Any
from unittest.mock import MagicMock

from core.llm.client import LLMResponse, Prompt
from service.pipeline.planning import (
    PLAN_REQUIRED_FIELDS,
    MockPlanningAgent,
    PlanningAgent,
)
from service.search.mock_adapter import MockWebSearchAdapter


class _MockLLM:
    """LLMClient Mock."""

    def __init__(self, response_text: str = "") -> None:
        self._text = response_text

    @property
    def model_name(self) -> str:
        return "mock"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text=self._text, model="mock",
            cost_usd=0.05, latency_ms=200,
            input_tokens=100, output_tokens=200,
        )


VALID_PLAN_JSON = """
{
    "work_name": "test_work",
    "work_genre": "판타지",
    "main_character": {
        "name": "투르윈",
        "role": "주인공",
        "description": "신참 모험가"
    },
    "supporting_characters": [
        {"name": "셰인", "role": "조력자", "description": "멘토"}
    ],
    "world": {
        "setting_name": "테스트 세계",
        "genre": "판타지",
        "tone": "진지",
        "rules": ["마법 존재"]
    },
    "opening_scene": "투르윈은 던전 입구에 있다",
    "initial_choices": ["들어가기", "살피기"]
}
"""


class TestMockPlanningAgent:
    def test_known_work_returns_plan(self) -> None:
        agent = MockPlanningAgent()
        result = agent.run(work_name="novice_dungeon_run")
        assert result.error is None
        assert result.plan.work_name == "novice_dungeon_run"
        assert result.plan.ip_masking_applied is True

    def test_unknown_work_returns_error(self) -> None:
        agent = MockPlanningAgent()
        result = agent.run(work_name="not_in_db_xyz")
        assert result.error is not None
        assert "No mock plan" in result.error

    def test_user_preferences_attached(self) -> None:
        agent = MockPlanningAgent()
        prefs = {"entry_point": "주인공", "play_style": "전투"}
        result = agent.run(work_name="novice_dungeon_run", user_preferences=prefs)
        assert result.plan.user_preferences == prefs


class TestPlanningAgentRealLLM:
    def test_full_flow_success(self) -> None:
        llm = _MockLLM(response_text=VALID_PLAN_JSON)
        search = MockWebSearchAdapter()
        agent = PlanningAgent(llm, search)

        result = agent.run(
            work_name="novice_dungeon_run",
            user_preferences={"entry_point": "주인공"},
        )
        assert result.error is None
        assert result.plan.work_name == "test_work"
        assert result.plan.main_character.name == "투르윈"

    def test_no_search_results(self) -> None:
        llm = _MockLLM()
        search = MockWebSearchAdapter()
        agent = PlanningAgent(llm, search)
        result = agent.run(work_name="totally_unknown_xyz")
        assert result.error is not None
        assert "No search results" in result.error

    def test_invalid_json(self) -> None:
        llm = _MockLLM(response_text="이건 JSON이 아닙니다")
        search = MockWebSearchAdapter()
        agent = PlanningAgent(llm, search)
        result = agent.run(work_name="novice_dungeon_run")
        assert result.error is not None

    def test_missing_required_field(self) -> None:
        partial_json = '{"work_name": "test", "work_genre": "판타지"}'
        llm = _MockLLM(response_text=partial_json)
        search = MockWebSearchAdapter()
        agent = PlanningAgent(llm, search)
        result = agent.run(work_name="novice_dungeon_run")
        assert result.error is not None

    def test_search_failure_handled(self) -> None:
        llm = _MockLLM()
        broken_search = MagicMock()
        broken_search.search.side_effect = RuntimeError("search down")
        agent = PlanningAgent(llm, broken_search)
        result = agent.run(work_name="any")
        assert result.error is not None
        assert "Search failed" in result.error

    def test_llm_failure_handled(self) -> None:
        llm = MagicMock()
        llm.generate.side_effect = RuntimeError("LLM down")
        llm.model_name = "broken"
        search = MockWebSearchAdapter()
        agent = PlanningAgent(llm, search)
        result = agent.run(work_name="novice_dungeon_run")
        assert result.error is not None
        assert "LLM call failed" in result.error

    def test_ip_masking_re_applied(self) -> None:
        """LLM이 IP를 누설할 경우 재masking 확인."""
        json_with_leakage = """
{
    "work_name": "novice_dungeon_run",
    "work_genre": "판타지",
    "main_character": {
        "name": "비요른",
        "role": "주인공",
        "description": "바바리안"
    },
    "supporting_characters": [],
    "world": {
        "setting_name": "라프도니아",
        "genre": "판타지",
        "tone": "진지",
        "rules": []
    },
    "opening_scene": "test scene here",
    "initial_choices": ["x"]
}
"""
        llm = _MockLLM(response_text=json_with_leakage)
        search = MockWebSearchAdapter()
        agent = PlanningAgent(llm, search)
        result = agent.run(work_name="novice_dungeon_run")
        assert result.error is None
        assert "비요른" not in result.plan.main_character.name
        assert "라프도니아" not in result.plan.world.setting_name


class TestPlanRequiredFields:
    def test_required_fields_listed(self) -> None:
        assert "work_name" in PLAN_REQUIRED_FIELDS
        assert "main_character" in PLAN_REQUIRED_FIELDS
        assert "world" in PLAN_REQUIRED_FIELDS
