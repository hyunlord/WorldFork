"""Mechanical Checker의 룰 추상화 (HARNESS_CORE 2장).

Day 3: Rule ABC + CheckFailure + MechanicalResult.
이후:
  - Day 4: LLM Judge용 Metric (다른 모듈)
  - Tier 1+: 게임 도메인 룰 추가
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

SeverityLevel = Literal["critical", "major", "minor"]


@dataclass
class CheckFailure:
    """단일 룰 실패 정보."""

    rule: str
    severity: SeverityLevel
    detail: str
    suggestion: str = ""


@dataclass
class MechanicalResult:
    """Mechanical 검증 종합 결과."""

    passed: bool
    score: float
    failures: list[CheckFailure] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "failures": [
                {
                    "rule": f.rule,
                    "severity": f.severity,
                    "detail": f.detail,
                    "suggestion": f.suggestion,
                }
                for f in self.failures
            ],
        }

    def critical_count(self) -> int:
        return sum(1 for f in self.failures if f.severity == "critical")

    def major_count(self) -> int:
        return sum(1 for f in self.failures if f.severity == "major")

    def minor_count(self) -> int:
        return sum(1 for f in self.failures if f.severity == "minor")

    def summary_line(self) -> str:
        """콘솔 출력용 한 줄 요약."""
        total_rules = self._passed_rules + len(self.failures)
        if self.passed:
            return f"Mechanical: {self._passed_rules}/{total_rules} 통과 ✅"
        violations = ", ".join(
            f"{f.rule}({f.severity})" for f in self.failures
        )
        return (
            f"Mechanical: {self._passed_rules}/{total_rules} ⚠️ "
            f"위반: {violations}"
        )

    def passed_rules(self) -> int:
        return self._passed_rules

    _passed_rules: int = 0  # MechanicalChecker.check()가 채움


class Rule(ABC):
    """Mechanical 룰 추상 클래스."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """룰 식별자 (예: 'json_validity', 'korean_ratio')."""
        ...

    @property
    @abstractmethod
    def severity(self) -> SeverityLevel:
        ...

    @abstractmethod
    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        """룰 검증.

        Returns:
            None: 통과 / CheckFailure: 실패
        """
        ...
