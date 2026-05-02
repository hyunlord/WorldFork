"""Coding Loop max 3 retry (★ 본인 자료 AutoDev 정확).

흐름:
  PreCode → Coder → PostCode (★ 빌드 게이트)
    → PreVerify → Verifier → PostVerify
    → 점수 < cutoff → OnRetry → 재시도 (max 3)
    → 3번 모두 실패 → needs_replan=True

★ 본인 자료 정신:
  - 정보 격리: retry feedback에 점수 / verdict 전달 X
  - 매 단계 hook 호출
  - PostCode = 빌드 게이트 (blocking)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .hooks import HookEvent, HookManager
from .task_context import TaskContext, TaskStatus


@dataclass
class CodingResult:
    """Coding Loop 결과."""

    succeeded: bool
    final_score: int = 0
    final_verdict: str = "fail"
    attempts: int = 0
    issues_for_retry: list[str] = field(default_factory=list)
    abort_reason: str = ""
    needs_replan: bool = False


CoderFn = Callable[[list[str]], dict[str, Any]]
VerifierFn = Callable[[dict[str, Any]], dict[str, Any]]


class CodingLoop:
    """Coding Loop max 3 retry.

    각 retry는 ★ 정보 격리:
      - issues + suggestions만 전달
      - 점수 / verdict 절대 안 알려줌 (★ 본인 자료)
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        hook_manager: HookManager,
        coder: CoderFn,
        verifier: VerifierFn,
        cutoff_score: int = 95,
    ) -> None:
        """
        Args:
            hook_manager: 12 이벤트 manager
            coder: (issues_for_retry: list[str]) → code output dict
            verifier: (code_output: dict) → {score, verdict, issues}
            cutoff_score: 통과 점수 (★ 본인 #19)
        """
        self._hooks = hook_manager
        self._coder = coder
        self._verifier = verifier
        self._cutoff = cutoff_score

    def run(self, task: TaskContext) -> CodingResult:
        """Coding Loop 실행.

        Returns:
            CodingResult with succeeded=True if cutoff met within MAX_RETRIES.
        """
        result = CodingResult(succeeded=False)

        # 매 retry feedback (★ 정보 격리: 점수 X, issues만)
        retry_feedback: list[str] = []

        for attempt in range(1, self.MAX_RETRIES + 1):
            task.status = TaskStatus.CODING

            # PreCode hook
            ctx = self._hooks.trigger(
                HookEvent.PRE_CODE,
                payload={"attempt": attempt, "feedback": retry_feedback},
            )
            if ctx.abort:
                result.abort_reason = ctx.abort_reason
                return result

            # Coder 호출
            try:
                code_output = self._coder(retry_feedback)
            except Exception as e:
                task.log_code_attempt(False, {"error": str(e)})
                result.abort_reason = f"Coder failed: {e}"
                return result

            task.log_code_attempt(True, code_output)

            # PostCode hook (★ 빌드 게이트)
            build_passed = bool(code_output.get("build_passed", True))
            ctx = self._hooks.trigger(
                HookEvent.POST_CODE,
                payload={"build_passed": build_passed, "attempt": attempt},
            )
            if ctx.abort:
                result.abort_reason = ctx.abort_reason
                continue  # 빌드 fail → 재시도

            # PreVerify hook
            self._hooks.trigger(
                HookEvent.PRE_VERIFY,
                payload={"attempt": attempt},
            )

            # Verifier 호출
            task.status = TaskStatus.VERIFYING
            try:
                verify_output = self._verifier(code_output)
            except Exception as e:
                task.log_verify_attempt(0, "error", {"error": str(e)})
                result.abort_reason = f"Verifier failed: {e}"
                return result

            score = int(verify_output.get("score", 0))
            verdict = str(verify_output.get("verdict", "fail"))
            issues: list[Any] = verify_output.get("issues", [])

            task.log_verify_attempt(score, verdict, {"issues_count": len(issues)})

            # PostVerify hook (점수 임계값 체크)
            ctx = self._hooks.trigger(
                HookEvent.POST_VERIFY,
                payload={"score": score, "threshold": self._cutoff, "attempt": attempt},
            )

            # ★ 통과
            if not ctx.abort and verdict == "pass" and score >= self._cutoff:
                result.succeeded = True
                result.final_score = score
                result.final_verdict = verdict
                result.attempts = attempt
                return result

            # ★ 재시도 — 정보 격리 (★ 본인 자료)
            # issues / descriptions만 (점수 X)
            issue_texts = [
                str(i.get("description", i)) if isinstance(i, dict) else str(i)
                for i in issues
            ]
            retry_feedback = issue_texts

            # OnRetry hook
            self._hooks.trigger(
                HookEvent.ON_RETRY,
                payload={"attempt": attempt, "issues_count": len(issues)},
            )

            task.status = TaskStatus.RETRYING

        # ★ 3번 모두 실패
        result.attempts = self.MAX_RETRIES
        result.issues_for_retry = retry_feedback
        result.needs_replan = True
        return result
