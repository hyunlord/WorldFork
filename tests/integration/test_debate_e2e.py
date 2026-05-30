"""Layer1ReviewAgent debate 통합 테스트 (mock LLM)."""

from __future__ import annotations

from core.llm.client import LLMResponse, Prompt
from core.verify.debate import ChallengerReview, DebateJudge, DebateVerdict
from core.verify.layer1_review import Layer1ReviewAgent


class _FakeCodex:
    """Drafter(codex) mock — model_name + generate."""

    model_name = "gpt-5.5"

    def generate(self, prompt: Prompt, **kwargs: object) -> LLMResponse:
        return LLMResponse(
            text='{"score": 23, "verdict": "pass", "issues": [], "summary": "양호"}',
            model="codex",
            cost_usd=0.0,
        )


class _FakeJSON:
    def __init__(self, parsed: dict) -> None:
        self.parsed = parsed
        self.text = ""


class _FakeLocal:
    def __init__(self, parsed: dict) -> None:
        self._parsed = parsed

    def generate_json(self, prompt, schema=None, **kwargs):  # noqa: ANN001
        return _FakeJSON(self._parsed)


def test_layer1_agent_use_debate_flag() -> None:
    """use_debate=True 시 DebateJudge 생성."""
    agent = Layer1ReviewAgent(reviewer=_FakeCodex(), use_debate=True)
    assert agent._debate is not None
    agent_no = Layer1ReviewAgent(reviewer=_FakeCodex(), use_debate=False)
    assert agent_no._debate is None


def test_layer1_agent_forbidden_reviewer_still_enforced() -> None:
    """debate여도 claude reviewer는 Cross-Model 위반."""
    import pytest

    class _Claude:
        model_name = "claude"

        def generate(self, prompt, **kwargs):  # noqa: ANN001, ANN003
            return LLMResponse(text="{}", model="claude", cost_usd=0.0)

    with pytest.raises(ValueError, match="forbidden"):
        Layer1ReviewAgent(reviewer=_Claude(), use_debate=True)


def test_debate_judge_full_flow_pass() -> None:
    """3-stage full — drafter 23 + challenger 우려없음 + quality pass → 23 pass."""
    judge = DebateJudge(
        challenger_client=_FakeLocal(
            {"concerns": [], "missing_checks": [], "summary": "없음"}
        ),
        quality_client=_FakeLocal({"verdict": "pass", "score": 23, "summary": "ok"}),
    )
    result = judge.judge(
        drafter_score=23,
        drafter_summary="양호",
        commit_intent="feat: debate 구현",
    )
    assert result.verdict == DebateVerdict.PASS
    assert result.score == 23
    assert result.models_used["challenger"] == "qwen-27b"
    assert isinstance(result.challenger, ChallengerReview)
