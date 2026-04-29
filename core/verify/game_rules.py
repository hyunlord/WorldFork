"""게임 도메인 Mechanical 룰 (HARNESS_CORE 2.3).

게임 상태 / 세계관 일관성 검증.
Day 3: world_consistency.
Day 4+: game_state_consistency (NLU 기반) LLM Judge에서 본격.
"""

from typing import Any

from .rule import CheckFailure, Rule, SeverityLevel


class WorldConsistencyRule(Rule):
    """세계관 위반 감지 (예: 중세 판타지에 '스마트폰' 등장)."""

    @property
    def rule_id(self) -> str:
        return "world_consistency"

    @property
    def severity(self) -> SeverityLevel:
        return "major"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        forbidden_elements: list[str] = context.get("world_forbidden", [])
        if not forbidden_elements:
            return None

        response_lower = response.lower()
        found = [
            elem for elem in forbidden_elements
            if elem.lower() in response_lower
        ]
        if found:
            return CheckFailure(
                rule=self.rule_id,
                severity=self.severity,
                detail=f"World-inconsistent elements: {found}",
                suggestion=(
                    "Stay within the worldview. "
                    f"Avoid mentioning: {forbidden_elements}"
                ),
            )
        return None


def get_game_rules() -> list[Rule]:
    """게임 도메인 룰 반환."""
    return [
        WorldConsistencyRule(),
    ]
