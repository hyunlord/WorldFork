"""Retry with Feedback (HARNESS_CORE 8장).

검증 실패 시 피드백과 함께 재시도.
Information Isolation 강제 (Mode B에서 점수 / verdict 누설 X).

v0.2 Ablation modes (HARNESS_CORE 8.4):
  A: score 노출
  B: issues only (default, 점수 누설 X)
  C: confidence band 익명화
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.llm.client import LLMClient, Prompt


class InformationLeakError(Exception):
    """Retry feedback에 금지 키 누설."""

    pass


class FeedbackMode(Enum):
    """v0.2 Ablation 모드 (HARNESS_CORE 8.4)."""

    A_SCORE_EXPOSED = "a"
    B_ISSUES_ONLY = "b"
    C_ANONYMIZED = "c"


@dataclass
class RetryFeedback:
    """재시도 prompt에 추가될 피드백."""

    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    mode: FeedbackMode = FeedbackMode.B_ISSUES_ONLY

    score: float | None = None
    verdict: str | None = None
    confidence_band: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "issues": list(self.issues),
            "suggestions": list(self.suggestions),
        }
        if self.mode == FeedbackMode.A_SCORE_EXPOSED:
            if self.score is not None:
                d["score"] = self.score
            if self.verdict is not None:
                d["verdict"] = self.verdict
        elif self.mode == FeedbackMode.C_ANONYMIZED:
            if self.confidence_band is not None:
                d["confidence_band"] = self.confidence_band
        return d

    def to_prompt_section(self) -> str:
        """재시도 prompt에 append 될 텍스트."""
        sections = ["[Previous attempt did not pass.]"]

        if self.mode == FeedbackMode.A_SCORE_EXPOSED:
            if self.score is not None and self.verdict is not None:
                sections.append(f"Score: {self.score:.0f}/100 ({self.verdict})")
        elif self.mode == FeedbackMode.C_ANONYMIZED:
            if self.confidence_band is not None:
                sections.append(f"Confidence: {self.confidence_band}")

        if self.issues:
            sections.append("Issues:")
            sections.extend(f"  - {i}" for i in self.issues)
        if self.suggestions:
            sections.append("Suggestions:")
            sections.extend(f"  - {s}" for s in self.suggestions)

        return "\n".join(sections)


FORBIDDEN_KEYS_FOR_B: set[str] = {"score", "verdict", "threshold", "passed"}


def validate_information_isolation(feedback: RetryFeedback) -> None:
    """Mode B에서 score / verdict 등 금지 키가 노출되지 않았는지 확인.

    Raises:
        InformationLeakError: 금지 키 발견
    """
    if feedback.mode != FeedbackMode.B_ISSUES_ONLY:
        return

    d = feedback.to_dict()
    leaked = set(d.keys()) & FORBIDDEN_KEYS_FOR_B
    if leaked:
        raise InformationLeakError(
            f"Information leak in mode B: forbidden keys {leaked} present in feedback. "
            f"Use mode A or C explicitly to expose score."
        )


@dataclass
class RetryAttempt:
    """단일 재시도 결과."""

    attempt_n: int
    response_text: str
    passed: bool
    score: float | None = None


@dataclass
class RetryResult:
    """전체 재시도 결과."""

    final_response: str
    attempts: list[RetryAttempt]
    succeeded: bool

    def total_attempts(self) -> int:
        return len(self.attempts)

    def summary(self) -> str:
        success_str = "✅" if self.succeeded else "❌"
        return f"Retry: {self.total_attempts()} attempts, {success_str}"


VerifyFn = Callable[[str, dict[str, Any]], tuple[bool, RetryFeedback]]


class RetryRunner:
    """검증 실패 시 피드백과 함께 재시도 (HARNESS_CORE 8장).

    verify_fn: (response_text, context) -> (passed, feedback)
    max_retries: 0이면 재시도 없음 (1회만), 1이면 1회 재시도 (최대 2회 호출).
    """

    def __init__(
        self,
        client: LLMClient,
        verify_fn: VerifyFn,
        max_retries: int = 0,
    ) -> None:
        self.client = client
        self.verify_fn = verify_fn
        self.max_retries = max_retries

    def run(
        self,
        prompt: Prompt,
        context: dict[str, Any] | None = None,
    ) -> RetryResult:
        """프롬프트 보내고 검증 실패 시 재시도."""
        context = context or {}
        attempts: list[RetryAttempt] = []
        current_prompt = prompt

        for attempt_n in range(self.max_retries + 1):
            response = self.client.generate(current_prompt)

            passed, feedback = self.verify_fn(response.text, context)

            attempts.append(
                RetryAttempt(
                    attempt_n=attempt_n,
                    response_text=response.text,
                    passed=passed,
                )
            )

            if passed:
                return RetryResult(
                    final_response=response.text,
                    attempts=attempts,
                    succeeded=True,
                )

            if attempt_n == self.max_retries:
                break

            # 재시도 전 정보 격리 강제
            validate_information_isolation(feedback)

            current_prompt = Prompt(
                system=prompt.system,
                user=prompt.user + "\n\n" + feedback.to_prompt_section(),
            )

        return RetryResult(
            final_response=attempts[-1].response_text,
            attempts=attempts,
            succeeded=False,
        )
