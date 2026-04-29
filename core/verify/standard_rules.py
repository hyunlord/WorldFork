"""표준 Mechanical 룰 (HARNESS_CORE 2.2).

WorldFork의 모든 LLM 응답에 적용 가능한 일반 룰.
Day 3: 4개 룰 (json_validity / korean_ratio / length / ai_breakout).
"""

import json
from typing import Any

from .rule import CheckFailure, Rule, SeverityLevel


class JsonValidityRule(Rule):
    """JSON 응답이어야 할 때 파싱 가능한가."""

    @property
    def rule_id(self) -> str:
        return "json_validity"

    @property
    def severity(self) -> SeverityLevel:
        return "critical"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        if not context.get("requires_json"):
            return None
        try:
            json.loads(response)
            return None
        except json.JSONDecodeError as e:
            return CheckFailure(
                rule=self.rule_id,
                severity=self.severity,
                detail=f"JSON parse error: {e}",
                suggestion="Output valid JSON. No markdown fences, no preamble.",
            )


class KoreanRatioRule(Rule):
    """한국어 비율이 충분한가."""

    threshold: float = 0.5

    @property
    def rule_id(self) -> str:
        return "korean_ratio"

    @property
    def severity(self) -> SeverityLevel:
        return "major"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        if context.get("language") != "ko":
            return None

        korean_chars = sum(1 for c in response if 0xAC00 <= ord(c) <= 0xD7A3)
        meaningful_chars = sum(
            1 for c in response
            if c.isalnum() or 0xAC00 <= ord(c) <= 0xD7A3
        )

        if meaningful_chars == 0:
            return None

        ratio = korean_chars / meaningful_chars
        if ratio < self.threshold:
            return CheckFailure(
                rule=self.rule_id,
                severity=self.severity,
                detail=f"Korean ratio {ratio:.1%} < {self.threshold:.0%}",
                suggestion="Respond primarily in Korean. Avoid English unless necessary.",
            )
        return None


class LengthRule(Rule):
    """응답 길이가 적절한가."""

    @property
    def rule_id(self) -> str:
        return "length"

    @property
    def severity(self) -> SeverityLevel:
        return "minor"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        max_len = context.get("max_length", 1000)
        if len(response) > max_len * 1.5:
            return CheckFailure(
                rule=self.rule_id,
                severity=self.severity,
                detail=f"Response too long: {len(response)} chars (max {max_len})",
                suggestion=f"Keep response under {max_len} characters.",
            )
        if len(response.strip()) < 5:
            return CheckFailure(
                rule=self.rule_id,
                severity="major",
                detail=f"Response too short: {len(response.strip())} chars",
                suggestion="Provide a meaningful response.",
            )
        return None


class AIBreakoutRule(Rule):
    """AI 본능 누설 ('I am an AI', 'ChatGPT' 등)."""

    forbidden_phrases: list[str] = [
        "I'm an AI",
        "I am an AI",
        "as an AI",
        "as a language model",
        "language model",
        "ChatGPT",
        "GPT-4",
        "Claude",
        "Anthropic",
        "OpenAI",
        "AI 어시스턴트",
        "AI 언어 모델",
        "저는 AI",
        "저는 인공지능",
        "AI로서",
    ]

    @property
    def rule_id(self) -> str:
        return "ai_breakout"

    @property
    def severity(self) -> SeverityLevel:
        return "major"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        if not context.get("character_response", True):
            return None

        response_lower = response.lower()
        leaked = [
            p for p in self.forbidden_phrases
            if p.lower() in response_lower
        ]
        if leaked:
            return CheckFailure(
                rule=self.rule_id,
                severity=self.severity,
                detail=f"AI breakout phrases detected: {leaked}",
                suggestion="Stay in character. Do not mention being an AI / language model.",
            )
        return None


def get_standard_rules() -> list[Rule]:
    """표준 룰 4개 반환."""
    return [
        JsonValidityRule(),
        KoreanRatioRule(),
        LengthRule(),
        AIBreakoutRule(),
    ]
