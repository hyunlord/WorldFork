"""Day 4: LLM Judge 단위 테스트 (Mock 사용)."""

from typing import Any

from core.llm.client import JSONLLMResponse, LLMClient, LLMResponse, Prompt
from core.verify.llm_judge import (
    JUDGE_SCHEMA,
    JudgeCriteria,
    JudgeScore,
    LLMJudge,
    build_judge_prompt,
)

# ─── Mock 클라이언트 ───────────────────────────────────────────


class MockJSONClient(LLMClient):
    """generate_json()만 구현한 mock."""

    def __init__(self, parsed_response: dict[str, Any], model: str = "mock-judge") -> None:
        self._parsed = parsed_response
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:  # type: ignore[override]
        raise NotImplementedError("MockJSONClient does not support generate()")

    def generate_json(
        self,
        prompt: Prompt,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> JSONLLMResponse:
        return JSONLLMResponse(
            parsed=self._parsed,
            text=str(self._parsed),
            model=self._model,
            cost_usd=0.0,
            latency_ms=10,
            input_tokens=100,
            output_tokens=50,
        )


# ─── JudgeCriteria ────────────────────────────────────────────


class TestJudgeCriteria:
    def test_to_prompt_section_includes_description(self) -> None:
        c = JudgeCriteria(
            name="test",
            description="Test description",
            dimensions=["dim1", "dim2"],
        )
        section = c.to_prompt_section()
        assert "Test description" in section

    def test_to_prompt_section_includes_all_dimensions(self) -> None:
        c = JudgeCriteria(
            name="t",
            description="d",
            dimensions=["naturalness", "formality", "consistency"],
        )
        section = c.to_prompt_section()
        assert "naturalness" in section
        assert "formality" in section
        assert "consistency" in section

    def test_to_prompt_section_empty_dimensions(self) -> None:
        c = JudgeCriteria(name="t", description="only description", dimensions=[])
        section = c.to_prompt_section()
        assert "only description" in section


# ─── JudgeScore ───────────────────────────────────────────────


class TestJudgeScore:
    def test_to_dict_contains_all_fields(self) -> None:
        s = JudgeScore(
            score=85.0,
            verdict="pass",
            issues=[],
            suggestions=["be more specific"],
            judge_model="mock",
            cost_usd=0.001,
            latency_ms=100,
        )
        d = s.to_dict()
        assert d["score"] == 85.0
        assert d["verdict"] == "pass"
        assert d["issues"] == []
        assert d["suggestions"] == ["be more specific"]
        assert d["judge_model"] == "mock"
        assert d["cost_usd"] == 0.001
        assert d["latency_ms"] == 100

    def test_summary_line_includes_model_and_score(self) -> None:
        s = JudgeScore(
            score=90.0,
            verdict="pass",
            issues=[],
            suggestions=[],
            judge_model="codex-judge",
            cost_usd=0.0,
            latency_ms=0,
        )
        line = s.summary_line()
        assert "codex-judge" in line
        assert "90" in line

    def test_summary_line_verdict_symbols(self) -> None:
        for verdict, expected in [("pass", "✅"), ("warn", "⚠️"), ("fail", "❌")]:
            s = JudgeScore(
                score=80.0, verdict=verdict,  # type: ignore[arg-type]
                issues=[], suggestions=[],
                judge_model="m", cost_usd=0.0, latency_ms=0,
            )
            assert expected in s.summary_line()


# ─── build_judge_prompt ───────────────────────────────────────


class TestBuildJudgePrompt:
    def test_includes_response_text(self) -> None:
        c = JudgeCriteria(name="x", description="d", dimensions=[])
        prompt = build_judge_prompt("응답 텍스트", c)
        assert "응답 텍스트" in prompt.user

    def test_includes_criteria_description(self) -> None:
        c = JudgeCriteria(
            name="x",
            description="Korean speech naturalness",
            dimensions=["formality"],
        )
        prompt = build_judge_prompt("응답", c)
        assert "Korean speech naturalness" in prompt.user

    def test_includes_dimensions(self) -> None:
        c = JudgeCriteria(
            name="x",
            description="d",
            dimensions=["dim_a", "dim_b"],
        )
        prompt = build_judge_prompt("응답", c)
        assert "dim_a" in prompt.user
        assert "dim_b" in prompt.user

    def test_includes_json_in_output_format(self) -> None:
        c = JudgeCriteria(name="x", description="d", dimensions=[])
        prompt = build_judge_prompt("응답", c)
        assert "JSON" in prompt.user

    def test_context_included_in_prompt(self) -> None:
        c = JudgeCriteria(name="x", description="d", dimensions=[])
        prompt = build_judge_prompt("응답", c, context={"character": "셰인"})
        assert "셰인" in prompt.user

    def test_returns_prompt_with_system_field(self) -> None:
        c = JudgeCriteria(name="x", description="d", dimensions=[])
        prompt = build_judge_prompt("응답", c)
        assert isinstance(prompt, Prompt)
        assert len(prompt.system) > 0


# ─── LLMJudge ─────────────────────────────────────────────────


class TestLLMJudge:
    def test_evaluate_pass_verdict(self) -> None:
        client = MockJSONClient({
            "score": 90,
            "verdict": "pass",
            "issues": [],
            "suggestions": [],
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)

        assert score.score == 90.0
        assert score.verdict == "pass"
        assert score.issues == []

    def test_evaluate_fail_verdict_with_issues(self) -> None:
        client = MockJSONClient({
            "score": 50,
            "verdict": "fail",
            "issues": ["bad korean", "unnatural phrasing"],
            "suggestions": ["use formal speech"],
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)

        assert score.score == 50.0
        assert score.verdict == "fail"
        assert "bad korean" in score.issues
        assert "unnatural phrasing" in score.issues
        assert "use formal speech" in score.suggestions

    def test_evaluate_warn_verdict(self) -> None:
        client = MockJSONClient({
            "score": 75,
            "verdict": "warn",
            "issues": ["minor issue"],
            "suggestions": [],
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)

        assert score.verdict == "warn"
        assert score.score == 75.0

    def test_evaluate_clamps_score_above_100(self) -> None:
        client = MockJSONClient({
            "score": 150,
            "verdict": "pass",
            "issues": [],
            "suggestions": [],
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)
        assert score.score == 100.0

    def test_evaluate_clamps_score_below_0(self) -> None:
        client = MockJSONClient({
            "score": -10,
            "verdict": "fail",
            "issues": [],
            "suggestions": [],
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)
        assert score.score == 0.0

    def test_evaluate_invalid_verdict_recovers_to_pass_for_high_score(self) -> None:
        client = MockJSONClient({
            "score": 90,
            "verdict": "excellent",  # 잘못된 값
            "issues": [],
            "suggestions": [],
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)
        # score >= 85 → pass
        assert score.verdict == "pass"

    def test_evaluate_invalid_verdict_recovers_to_warn_for_mid_score(self) -> None:
        client = MockJSONClient({
            "score": 75,
            "verdict": "okay",  # 잘못된 값
            "issues": [],
            "suggestions": [],
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)
        # 70 <= score < 85 → warn
        assert score.verdict == "warn"

    def test_evaluate_invalid_verdict_recovers_to_fail_for_low_score(self) -> None:
        client = MockJSONClient({
            "score": 40,
            "verdict": "bad",  # 잘못된 값
            "issues": [],
            "suggestions": [],
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)
        # score < 70 → fail
        assert score.verdict == "fail"

    def test_evaluate_uses_judge_model_name(self) -> None:
        client = MockJSONClient(
            {"score": 85, "verdict": "pass", "issues": [], "suggestions": []},
            model="codex-eval",
        )
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)
        assert score.judge_model == "codex-eval"

    def test_evaluate_with_context(self) -> None:
        client = MockJSONClient({
            "score": 88,
            "verdict": "pass",
            "issues": [],
            "suggestions": [],
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria, context={"character": "셰인"})
        assert score.score == 88.0

    def test_evaluate_non_list_issues_falls_back_to_empty(self) -> None:
        client = MockJSONClient({
            "score": 60,
            "verdict": "fail",
            "issues": "not a list",  # 잘못된 타입
            "suggestions": None,  # 잘못된 타입
        })
        judge = LLMJudge(client)
        criteria = JudgeCriteria(name="t", description="d", dimensions=[])

        score = judge.evaluate("응답", criteria)
        assert score.issues == []
        assert score.suggestions == []


# ─── JUDGE_SCHEMA 구조 ────────────────────────────────────────


def test_judge_schema_required_keys() -> None:
    assert "score" in JUDGE_SCHEMA["required"]
    assert "verdict" in JUDGE_SCHEMA["required"]
    assert "issues" in JUDGE_SCHEMA["required"]
    assert "suggestions" in JUDGE_SCHEMA["required"]


def test_judge_schema_properties_types() -> None:
    props = JUDGE_SCHEMA["properties"]
    assert props["score"]["type"] == "number"
    assert props["verdict"]["type"] == "string"
    assert props["issues"]["type"] == "array"
    assert props["suggestions"]["type"] == "array"
