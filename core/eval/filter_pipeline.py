"""Filter Pipeline (HARNESS_CORE 5.5).

LLM 응답에서 구조화된 출력 추출 (lm-eval 패턴 차용).

체인:
  1. GBNFNativeFilter        — 이미 valid JSON
  2. MarkdownFenceFilter     — ```json ... ```
  3. FirstJsonObjectFilter   — 텍스트 안 첫 { ... }
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class FilterResult:
    """필터 적용 결과."""

    succeeded: bool
    parsed: dict[str, Any] | None
    error: str | None
    filter_used: str


class Filter(ABC):
    """LLM 출력 후처리 단계."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def apply(self, raw_output: str, context: dict[str, Any]) -> FilterResult: ...


class GBNFNativeFilter(Filter):
    """이미 valid JSON 응답."""

    @property
    def name(self) -> str:
        return "gbnf_native"

    def apply(self, raw_output: str, context: dict[str, Any]) -> FilterResult:
        try:
            parsed = json.loads(raw_output.strip())
            if not isinstance(parsed, dict):
                return FilterResult(False, None, "Not a JSON object", self.name)
            return FilterResult(True, parsed, None, self.name)
        except json.JSONDecodeError as e:
            return FilterResult(False, None, str(e), self.name)


class MarkdownFenceFilter(Filter):
    """```json ... ``` 펜스 추출."""

    PATTERN = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)

    @property
    def name(self) -> str:
        return "markdown_fence"

    def apply(self, raw_output: str, context: dict[str, Any]) -> FilterResult:
        match = self.PATTERN.search(raw_output)
        if not match:
            return FilterResult(False, None, "No markdown fence", self.name)
        try:
            parsed = json.loads(match.group(1).strip())
            if not isinstance(parsed, dict):
                return FilterResult(False, None, "Not a JSON object", self.name)
            return FilterResult(True, parsed, None, self.name)
        except json.JSONDecodeError as e:
            return FilterResult(False, None, str(e), self.name)


class FirstJsonObjectFilter(Filter):
    """텍스트 안 첫 { ... } 추출 (중괄호 매칭)."""

    @property
    def name(self) -> str:
        return "first_json_object"

    def apply(self, raw_output: str, context: dict[str, Any]) -> FilterResult:
        depth = 0
        start = -1

        for i, c in enumerate(raw_output):
            if c == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = raw_output[start : i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return FilterResult(True, parsed, None, self.name)
                    except json.JSONDecodeError:
                        pass
                    start = -1

        return FilterResult(False, None, "No complete JSON object found", self.name)


class FilterPipeline:
    """다중 필터를 우선순위 순으로."""

    def __init__(self, filters: list[Filter] | None = None):
        if filters is None:
            filters = self._standard_chain()
        self.filters = filters

    @staticmethod
    def _standard_chain() -> list[Filter]:
        return [
            GBNFNativeFilter(),
            MarkdownFenceFilter(),
            FirstJsonObjectFilter(),
        ]

    def extract(self, raw_output: str, context: dict[str, Any] | None = None) -> FilterResult:
        context = context or {}
        errors: list[str] = []

        for f in self.filters:
            result = f.apply(raw_output, context)
            if result.succeeded:
                return result
            errors.append(f"{f.name}: {result.error}")

        return FilterResult(
            succeeded=False,
            parsed=None,
            error=f"All filters failed: {'; '.join(errors)}",
            filter_used="",
        )


STANDARD_FILTER_PIPELINE = FilterPipeline()
