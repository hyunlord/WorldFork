"""Mechanical Checker — 모든 룰 통합 (HARNESS_CORE 2.1)."""

from typing import Any

from .encoding_rules import get_encoding_rules
from .game_rules import get_game_rules
from .korean_rules import get_korean_rules
from .length_rules import get_length_rules
from .rule import CheckFailure, MechanicalResult, Rule
from .standard_rules import get_standard_rules


class MechanicalChecker:
    """LLM 호출 0회. 즉시 실패 케이스 잡기.

    HARNESS_CORE 2장 패턴.
    """

    def __init__(self, rules: list[Rule] | None = None):
        if rules is None:
            rules = self._default_rules()
        self.rules = rules

    @staticmethod
    def _default_rules() -> list[Rule]:
        return [
            *get_standard_rules(),
            *get_game_rules(),
            *get_korean_rules(),
            *get_encoding_rules(),
            *get_length_rules(),  # ★ W1 D6 verbose 대응
        ]

    def check(self, response: str, context: dict[str, Any]) -> MechanicalResult:
        failures: list[CheckFailure] = []
        passed_count = 0

        for rule in self.rules:
            failure = rule.check(response, context)
            if failure is None:
                passed_count += 1
            else:
                failures.append(failure)

        score = self._compute_score(failures)
        passed = (
            sum(1 for f in failures if f.severity == "critical") == 0
            and sum(1 for f in failures if f.severity == "major") == 0
        )

        result = MechanicalResult(
            passed=passed,
            score=score,
            failures=failures,
        )
        result._passed_rules = passed_count
        return result

    @staticmethod
    def _compute_score(failures: list[CheckFailure]) -> float:
        if any(f.severity == "critical" for f in failures):
            return 0.0
        score = 100.0
        for f in failures:
            if f.severity == "major":
                score -= 30
            elif f.severity == "minor":
                score -= 10
        return max(0.0, score)


def build_check_context(
    scenario: dict[str, Any],
    game_state: Any | None = None,
    requires_json: bool = False,
    max_length: int = 1500,
) -> dict[str, Any]:
    """시나리오에서 Mechanical 검증 context 빌드."""
    ip_forbidden: list[str] = []
    for rule in scenario.get("mechanical_rules", []):
        if rule.get("rule") == "ip_leakage":
            ip_forbidden = rule.get("forbidden_terms", [])
            break

    world_forbidden: list[str] = []
    for rule in scenario.get("mechanical_rules", []):
        if rule.get("rule") == "world_consistency":
            world_forbidden = rule.get("forbidden_elements", [])
            break

    char_styles: dict[str, str] = {}
    for char in scenario.get("characters", []):
        persona = char.get("persona", "").lower()
        if "격식체" in persona or "...입니다" in persona or "...셨군요" in persona:
            char_styles[char["name"]] = "formal"
        elif "사투리" in persona or "...구먼" in persona or "...그래" in persona:
            char_styles[char["name"]] = "informal"

    scenario_chars = [c["name"] for c in scenario.get("characters", [])]
    pc = scenario.get("setting", {}).get("player_character", {})
    if pc.get("name"):
        scenario_chars.append(pc["name"])

    return {
        "language": "ko",
        "character_response": True,
        "requires_json": requires_json,
        "max_length": max_length,
        "ip_forbidden_terms": ip_forbidden,
        "world_forbidden": world_forbidden,
        "character_speech_styles": char_styles,
        "scenario_character_names": scenario_chars,
        "game_state": game_state,
    }
