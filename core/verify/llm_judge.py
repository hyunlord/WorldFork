"""LLM-as-Judge (HARNESS_CORE 3장).

다른 모델로 LLM 응답 품질 평가.
Day 4: criteria 기반 score / verdict / issues / suggestions.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from core.llm.client import LLMClient, Prompt

JUDGE_SCHEMA: dict[str, Any] = {
    "required": ["score", "verdict", "issues", "suggestions"],
    "properties": {
        "score": {"type": "number", "minimum": 0, "maximum": 100},
        "verdict": {"type": "string", "enum": ["pass", "warn", "fail"]},
        "issues": {"type": "array", "items": {"type": "string"}},
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
}


@dataclass
class JudgeCriteria:
    """Judge가 평가할 기준."""

    name: str
    description: str
    dimensions: list[str] = field(default_factory=list)

    def to_prompt_section(self) -> str:
        dims = "\n".join(f"- {d}" for d in self.dimensions)
        return f"Criteria: {self.description}\n\nSpecifically score:\n{dims}"


@dataclass
class JudgeScore:
    """Judge 평가 결과 (HARNESS_CORE 3.1)."""

    score: float
    verdict: Literal["pass", "warn", "fail"]
    issues: list[str]
    suggestions: list[str]
    judge_model: str
    cost_usd: float
    latency_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "verdict": self.verdict,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "judge_model": self.judge_model,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
        }

    def summary_line(self) -> str:
        emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌"}[self.verdict]
        return f"Judge[{self.judge_model}]: {self.score:.0f}/100 {emoji} ({self.verdict})"


JUDGE_PROMPT_TEMPLATE = """# IDENTITY
You are an evaluation expert for the WorldFork game system.
Your job is to score LLM responses on multiple criteria, not as the original LLM.

# TASK
Evaluate the following response based on the given criteria.
Be objective. Do NOT favor the response just because it sounds plausible.

# {criteria_section}

# CONTEXT
{context_description}

# RESPONSE TO EVALUATE
---
{response}
---

# OUTPUT FORMAT
Respond ONLY with valid JSON, no markdown fences, no preamble.

Schema:
{{
  "score": <0-100>,
  "verdict": "pass" | "warn" | "fail",
  "issues": [<list of specific issues found, empty if none>],
  "suggestions": [<list of concrete improvements, empty if none>]
}}

Score guidelines:
- 95-100: Excellent, no issues
- 85-94: Good, minor issues
- 70-84: Acceptable, some issues
- 50-69: Weak, multiple issues
- 0-49: Severely flawed

Verdict guidelines:
- "pass": score >= 85
- "warn": score 70-84
- "fail": score < 70

Output JSON now:"""


def build_judge_prompt(
    response: str,
    criteria: JudgeCriteria,
    context: dict[str, Any] | None = None,
) -> Prompt:
    """Judge prompt 빌드."""
    context = context or {}
    context_desc = (
        "\n".join(f"- {k}: {v}" for k, v in context.items())
        or "(no additional context)"
    )

    text = JUDGE_PROMPT_TEMPLATE.format(
        criteria_section=criteria.to_prompt_section(),
        context_description=context_desc,
        response=response,
    )

    return Prompt(
        system="You are a strict, objective evaluator.",
        user=text,
    )


class LLMJudge:
    """다른 모델로 LLM 응답 평가 (HARNESS_CORE 3.1).

    judge_client는 generator와 다른 family여야 한다 (Cross-Model 정책).
    실제 강제는 CrossModelEnforcer가 담당.
    """

    def __init__(self, judge_client: LLMClient) -> None:
        self.judge = judge_client

    def evaluate(
        self,
        response: str,
        criteria: JudgeCriteria,
        context: dict[str, Any] | None = None,
    ) -> JudgeScore:
        """LLM 응답을 criteria로 평가."""
        prompt = build_judge_prompt(response, criteria, context)

        result = self.judge.generate_json(prompt, schema=JUDGE_SCHEMA)
        parsed = result.parsed

        score_raw = parsed.get("score", 0)
        try:
            score = float(score_raw)
        except (TypeError, ValueError):
            score = 0.0
        score = max(0.0, min(100.0, score))

        verdict_raw = parsed.get("verdict", "")
        verdict: Literal["pass", "warn", "fail"]
        if verdict_raw in ("pass", "warn", "fail"):
            verdict = verdict_raw
        else:
            verdict = "fail" if score < 70 else ("warn" if score < 85 else "pass")

        issues_raw = parsed.get("issues", [])
        suggestions_raw = parsed.get("suggestions", [])
        issues = [str(x) for x in issues_raw] if isinstance(issues_raw, list) else []
        suggestions = (
            [str(x) for x in suggestions_raw]
            if isinstance(suggestions_raw, list)
            else []
        )

        return JudgeScore(
            score=score,
            verdict=verdict,
            issues=issues,
            suggestions=suggestions,
            judge_model=self.judge.model_name,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
        )
