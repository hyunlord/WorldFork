"""W2 D4 작업 3: Agent Selection 테스트."""

import pytest

from service.pipeline.agent_selection import (
    TIER_CANDIDATES,
    AgentSelection,
    select_agents,
    select_game_llm,
    select_verify_llm,
)


class TestSelectGameLLM:
    def test_tier_1_cheap(self) -> None:
        result = select_game_llm("tier_1", "cheap")
        assert result == "qwen35-9b-q3"

    def test_tier_1_premium(self) -> None:
        result = select_game_llm("tier_1", "premium")
        assert result == "qwen36-27b-q2"

    def test_tier_1_balanced(self) -> None:
        result = select_game_llm("tier_1", "balanced")
        assert result in TIER_CANDIDATES["tier_1"]

    def test_unknown_tier_falls_back(self) -> None:
        result = select_game_llm("unknown_tier_xyz", "cheap")
        assert result == "qwen35-9b-q3"


class TestSelectVerifyLLM:
    def test_cross_model_enforced(self) -> None:
        """★ verify는 game과 다른 모델."""
        result = select_verify_llm("qwen35-9b-q3", "tier_1")
        assert result != "qwen35-9b-q3"

    def test_no_verify_when_only_one(self) -> None:
        with pytest.raises(ValueError, match="No verify"):
            select_verify_llm("qwen35-9b-q3", "tier_with_only_one")


class TestSelectAgents:
    def test_full_selection(self) -> None:
        result = select_agents("tier_1", "cheap")
        assert isinstance(result, AgentSelection)
        assert result.game_llm_key == "qwen35-9b-q3"
        assert result.verify_llm_key != result.game_llm_key
        assert "Cross-Model" in result.reasoning


class TestTierCandidates:
    def test_tier_1_has_candidates(self) -> None:
        assert len(TIER_CANDIDATES["tier_1"]) >= 2
