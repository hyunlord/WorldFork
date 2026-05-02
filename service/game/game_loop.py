"""Game Loop (★ Tier 1.5 D4 — TaskContext + HookManager 진짜 활용).

★ D4 변경:
  - TaskContext로 turn 추적 (★ Made-but-Never-Used 해결!)
  - HookManager 12 이벤트 통합
  - judge_score / total_score / verify_passed 전달
"""

from dataclasses import dataclass, field
from typing import Any

from core.harness.hooks import HookEvent, HookManager
from core.harness.task_context import TaskContext, TaskStatus
from service.pipeline.policies import DEFAULT_LAYER2_POLICY, Layer2Policy
from service.pipeline.types import Plan

from .gm_agent import GMAgent, GMResponse, MockGMAgent
from .state import GameState


@dataclass
class GameLoopResult:
    """단일 turn 결과 (★ D4 풍부 정보)."""

    response: str
    game_state: GameState
    attempts: int = 1
    cost_usd: float = 0.0
    fallback_used: bool = False
    error: str | None = None
    mechanical_passed: bool = True
    mechanical_failures: list[str] = field(default_factory=list)

    # ★ D4 추가 (TaskContext + 점수)
    task_context: TaskContext | None = None
    judge_score: float | None = None
    total_score: float = 0.0
    verify_passed: bool = True


def classify_action(user_action: str) -> str:
    """행동 분류 (rule-based, ★ LLM X, 자료 Stage 7 step 1)."""
    if not user_action:
        return "empty"

    action_lower = user_action.lower()

    if any(kw in action_lower for kw in ["공격", "베", "찌르", "때리", "싸"]):
        return "combat"
    if any(kw in action_lower for kw in ["살펴", "관찰", "보", "살피"]):
        return "explore"
    if any(kw in action_lower for kw in ["말", "대화", "물어", "묻"]):
        return "dialogue"
    if any(kw in action_lower for kw in ["가", "이동", "들어", "나오"]):
        return "movement"
    if any(kw in action_lower for kw in ["쉬", "휴식", "잠"]):
        return "rest"

    return "other"


class GameLoop:
    """Game Loop 본체 (★ Tier 1.5 D4).

    매 turn:
      1. ★ TaskContext 생성 (Layer 1 자산 진짜 활용)
      2. 행동 분류 (rule-based)
      3. HookManager 이벤트 (TASK_START → ... → TASK_COMPLETE/FAIL)
      4. Retry max 3 (★ 자료 정신)
      5. Fallback chain
    """

    def __init__(
        self,
        gm_agent: GMAgent | MockGMAgent,
        hook_manager: HookManager | None = None,
        policy: Layer2Policy = DEFAULT_LAYER2_POLICY,
    ) -> None:
        self._gm = gm_agent
        self._hooks = hook_manager or HookManager()
        self._policy = policy

    def process_action(
        self,
        plan: Plan,
        state: GameState,
        user_action: str,
    ) -> GameLoopResult:
        """단일 사용자 행동 처리 (★ D4 TaskContext + HookManager 진짜 활용)."""
        # 1. ★ TaskContext 생성 (Made-but-Never-Used 해결!)
        task = TaskContext(
            description=f"Turn {state.turn + 1}: {user_action[:50]}",
            layer="2",
        )
        task.status = TaskStatus.CODING

        # 2. 행동 분류
        action_type = classify_action(user_action)

        # 3. TASK_START hook
        ctx = self._hooks.trigger(
            HookEvent.TASK_START,
            payload={"task_id": task.task_id, "action_type": action_type},
        )
        if ctx.abort:
            task.mark_completed(success=False)
            return GameLoopResult(
                response="(시스템 오류 발생. 다시 시도해 주세요.)",
                game_state=state,
                attempts=0,
                fallback_used=True,
                error=ctx.abort_reason,
                task_context=task,
                verify_passed=False,
            )

        # 4. Retry 루프
        last_response: GMResponse | None = None

        for attempt in range(self._policy.max_retries + 1):
            # PRE_CODE hook
            self._hooks.trigger(
                HookEvent.PRE_CODE,
                payload={"attempt": attempt + 1},
            )

            response = self._gm.generate_response(plan, state, user_action)
            last_response = response

            task.log_code_attempt(
                succeeded=not bool(response.error),
                details={"attempt": attempt + 1, "score": response.total_score},
            )

            # POST_CODE hook (빌드 게이트)
            post_ctx = self._hooks.trigger(
                HookEvent.POST_CODE,
                payload={"build_passed": not bool(response.error)},
            )
            if post_ctx.abort or response.error:
                if attempt < self._policy.max_retries:
                    self._hooks.trigger(HookEvent.ON_RETRY, payload={"attempt": attempt + 1})
                continue

            # PRE_VERIFY hook
            self._hooks.trigger(HookEvent.PRE_VERIFY, payload={"attempt": attempt + 1})

            task.log_verify_attempt(
                score=int(response.total_score),
                verdict="pass" if response.verify_passed else "fail",
                details={"mech": response.mechanical_passed},
            )

            # POST_VERIFY hook
            self._hooks.trigger(
                HookEvent.POST_VERIFY,
                payload={
                    "verify_score": int(response.total_score),
                    "attempt": attempt + 1,
                },
            )

            if response.verify_passed:
                state.add_turn(
                    user_action=user_action,
                    gm_response=response.text,
                    cost_usd=response.cost_usd,
                    latency_ms=response.latency_ms,
                )
                self._hooks.trigger(
                    HookEvent.TASK_COMPLETE,
                    payload={"task_id": task.task_id, "score": response.total_score},
                )
                task.mark_completed(success=True)

                return GameLoopResult(
                    response=response.text,
                    game_state=state,
                    attempts=attempt + 1,
                    cost_usd=response.cost_usd,
                    mechanical_passed=response.mechanical_passed,
                    task_context=task,
                    judge_score=response.judge_score,
                    total_score=response.total_score,
                    verify_passed=True,
                )

            if attempt < self._policy.max_retries:
                self._hooks.trigger(HookEvent.ON_RETRY, payload={"attempt": attempt + 1})

        # 5. 모든 retry 실패 → Fallback
        self._hooks.trigger(
            HookEvent.TASK_FAIL, payload={"task_id": task.task_id}
        )
        task.mark_completed(success=False)

        if last_response is not None:
            fallback_text = self._fallback_message(last_response)
            return GameLoopResult(
                response=fallback_text,
                game_state=state,
                attempts=self._policy.max_retries + 1,
                cost_usd=last_response.cost_usd,
                fallback_used=True,
                error=last_response.error or "Mechanical failures",
                mechanical_passed=False,
                mechanical_failures=last_response.mechanical_failures,
                task_context=task,
                total_score=last_response.total_score,
                verify_passed=False,
            )

        return GameLoopResult(
            response="(시스템 오류 발생. 다시 시도해 주세요.)",
            game_state=state,
            attempts=0,
            fallback_used=True,
            error="No response generated",
            task_context=task,
            verify_passed=False,
        )

    @staticmethod
    def _fallback_message(last_response: GMResponse) -> str:
        if last_response.error:
            return (
                "잠시 응답을 생성하는 데 어려움이 있습니다. "
                "다른 행동을 시도해 주세요."
            )
        return (
            "응답이 만족스럽지 않아 재시도했지만 실패했습니다. "
            "다른 행동을 시도해 주시거나, 더 구체적으로 입력해 주세요."
        )


def build_game_loop_context(result: GameLoopResult) -> dict[str, Any]:
    """GameLoopResult를 로그용 dict로 변환 (★ play_w2_d5.py 활용)."""
    ctx: dict[str, Any] = {
        "attempts": result.attempts,
        "mechanical_passed": result.mechanical_passed,
        "mechanical_failures": result.mechanical_failures,
        "total_score": result.total_score,
        "verify_passed": result.verify_passed,
        "fallback_used": result.fallback_used,
        "cost_usd": result.cost_usd,
    }
    if result.judge_score is not None:
        ctx["judge_score"] = result.judge_score
    if result.task_context is not None:
        ctx["task_id"] = result.task_context.task_id
        ctx["task_succeeded"] = result.task_context.success
    return ctx
