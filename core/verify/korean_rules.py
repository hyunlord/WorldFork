"""한국어 특화 Mechanical 룰 (★ WorldFork 차별화).

외부 Eval 도구들 (promptfoo / deepeval / ragas / lm-eval) 어디에도 없는
한국어 특화 검증.

Day 3:
  - SpeechStyleConsistencyRule: 캐릭터별 격식체/반말 일관성
  - IPLeakageRule: 작품 IP 누출 감지

이후:
  - Tier 1+: 더 정교한 한국어 NLU
"""

import re
from typing import Any

from .rule import CheckFailure, Rule, SeverityLevel

# 격식체 종결어미 (입니다, 습니다, 셨습니다, 입니까, 셨군요 등)
FORMAL_ENDINGS = [
    "습니다", "입니다", "ㅂ니다", "ㅂ니까", "습니까",
    "셨습니다", "셨군요", "시지요", "이세요", "세요",
    "어요", "예요", "이에요",
]

# 반말 종결어미 — "다." 계열 제외 (습니다./입니다.와 오탐 방지)
INFORMAL_ENDINGS = [
    "야.", "야!", "야?", "야,",
    "어.", "어!", "어?", "어,",
    "해.", "해!", "해?", "해,",
    "지.", "지!", "지?", "지,",
    "냐?", "냐!",
    "구나.", "구나!",
]

# 격식체 어미 "니다" 뒤에 오는 "다"를 제외한 반말 "다" 감지
# (?<!니)다[.!?,] — "습니다./입니다." 직후는 오탐이므로 제외
_INFORMAL_DA = re.compile(r"(?<!니)다[.!?,]")


def detect_speech_style(text: str) -> str:
    """발화의 격식 스타일 감지.

    Returns:
        "formal" | "informal" | "mixed" | "unknown"
    """
    formal_count = sum(1 for ending in FORMAL_ENDINGS if ending in text)
    informal_count = sum(1 for ending in INFORMAL_ENDINGS if ending in text)
    if _INFORMAL_DA.search(text):
        informal_count += 1

    if formal_count > 0 and informal_count == 0:
        return "formal"
    if informal_count > 0 and formal_count == 0:
        return "informal"
    if formal_count > 0 and informal_count > 0:
        return "mixed"
    return "unknown"


class SpeechStyleConsistencyRule(Rule):
    """캐릭터별 발화 스타일 일관성.

    Day 3 미니멀: 응답 안에 mixed style 발화가 있으면 경고.
    정확한 화자 추론은 Day 4 LLM Judge에서.
    """

    @property
    def rule_id(self) -> str:
        return "korean_speech_consistency"

    @property
    def severity(self) -> SeverityLevel:
        return "major"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        if context.get("language") != "ko":
            return None

        char_styles: dict[str, str] = context.get("character_speech_styles", {})
        if not char_styles:
            return None

        utterances = re.findall(r'"([^"]+)"', response)
        if not utterances:
            return None

        violations: list[str] = []
        for utterance in utterances:
            detected_style = detect_speech_style(utterance)
            if detected_style == "mixed":
                violations.append(f'"{utterance[:40]}..." (mixed style)')

        if violations:
            return CheckFailure(
                rule=self.rule_id,
                severity=self.severity,
                detail=f"Mixed speech styles in utterances: {violations}",
                suggestion=(
                    "Each character should use consistent speech style "
                    "(formal vs informal). "
                    "See scenario character personas for expected style."
                ),
            )

        return None


class IPLeakageRule(Rule):
    """작품 IP 누출 감지 (★ WorldFork 핵심 차별화).

    원작 캐릭터명 / 작가명 / 작품명 / 고유 설정 직접 사용 차단.
    """

    @property
    def rule_id(self) -> str:
        return "ip_leakage"

    @property
    def severity(self) -> SeverityLevel:
        return "critical"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        forbidden_terms: list[str] = context.get("ip_forbidden_terms", [])
        if not forbidden_terms:
            return None

        response_lower = response.lower()
        leaked = [
            term for term in forbidden_terms
            if term.lower() in response_lower
        ]
        if leaked:
            return CheckFailure(
                rule=self.rule_id,
                severity=self.severity,
                detail=f"IP leakage detected: {leaked}",
                suggestion=(
                    "Do not use original work names / character names. "
                    "Use only the renamed characters from the scenario."
                ),
            )
        return None


def get_korean_rules() -> list[Rule]:
    """한국어 특화 룰 반환."""
    return [
        SpeechStyleConsistencyRule(),
        IPLeakageRule(),
    ]
