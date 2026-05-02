"""응답 길이 적절성 룰 (★ W1 D6 verbose 근본 대응).

W1 D5 Round 3 측정에서 verbose 41% 발견. 원인 분석:
    - max_tokens 고정 (300+) → 짧은 액션에도 장황한 응답
    - system prompt만으로 길이 제어 부족

이중 방어:
    1. core/llm/dynamic_token_limiter — 토큰 예산 자체를 자른다 (사전)
    2. LengthAppropriatenessRule (이 파일) — Mechanical 사후 검증
"""

from typing import Any

from .rule import CheckFailure, Rule, SeverityLevel


class LengthAppropriatenessRule(Rule):
    """user_input 대비 응답 길이 적절성.

    검증:
        user 5자 이하  → 응답 200자 이하 (1-2 문장)
        user 15자 이하 → 응답 400자 이하 (2-3 문장)
        user 50자 이하 → 응답 800자 이하 (3-5 문장)
        user 50자+    → 응답 1500자 이하

    severity:
        - 1.5배 초과 → major
        - 1.5배 이내 초과 → minor

    skip:
        - context.user_input 없으면 (legacy 호출자 호환)
    """

    @property
    def rule_id(self) -> str:
        return "length_appropriateness"

    @property
    def severity(self) -> SeverityLevel:
        # 동적 — check()가 ratio별로 지정
        return "major"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        user_input = str(context.get("user_input", ""))
        if not user_input:
            return None  # legacy/eval 호출 — skip

        allowed = self._allowed_response_length(len(user_input))
        if len(response) <= allowed:
            return None

        ratio_severity: SeverityLevel = (
            "major" if len(response) > allowed * 1.5 else "minor"
        )
        return CheckFailure(
            rule=self.rule_id,
            severity=ratio_severity,
            detail=(
                f"응답 {len(response)}자, user {len(user_input)}자 "
                f"→ 허용 {allowed}자 초과"
            ),
            suggestion=(
                "유저 액션이 짧으면 응답도 1-2 문장으로 짧게. "
                "system prompt + dynamic max_tokens 점검."
            ),
        )

    @staticmethod
    def _allowed_response_length(user_len: int) -> int:
        if user_len <= 5:
            return 200
        if user_len <= 15:
            return 400
        if user_len <= 50:
            return 800
        return 1500


class TruncationDetectionRule(Rule):
    """응답 잘림 검출 (★ W2 D5 본인 짚음 정공법).

    한국어 종결 어미 / 문장 부호로 끝나지 않으면 잘림 의심.
    context['language'] == 'ko' 일 때만 활성.
    """

    KOREAN_ENDINGS: tuple[str, ...] = (
        "다", "요", "음", "함", "임", "까", "지", "네", "야", "나",
    )
    PUNCTUATION: tuple[str, ...] = (".", "!", "?", "…", '"', "'", "」", "』", "]", ")")

    @property
    def rule_id(self) -> str:
        return "korean_truncation"

    @property
    def severity(self) -> SeverityLevel:
        return "major"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        if context.get("language") != "ko":
            return None

        text = response.strip()
        if not text:
            return CheckFailure(
                rule=self.rule_id,
                severity="major",
                detail="empty response",
                suggestion="응답이 비어있습니다. LLM 호출을 확인하세요.",
            )

        last_char = text[-1]
        if last_char in self.PUNCTUATION:
            return None

        for ending in self.KOREAN_ENDINGS:
            if text.endswith(ending):
                return None

        return CheckFailure(
            rule=self.rule_id,
            severity="major",
            detail=f"Korean response truncated (ends with '{text[-3:]}')",
            suggestion="응답이 문장 중간에 잘렸습니다. max_tokens 증가 또는 재시도.",
        )


def get_length_rules() -> list[Rule]:
    return [LengthAppropriatenessRule(), TruncationDetectionRule()]
