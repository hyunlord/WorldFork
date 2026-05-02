"""Game Loop (★ 자료 2.2 Stage 7 핵심).

매 사용자 행동마다:
  1. 행동 분류 (rule-based, ★ LLM X)
  2. GM Agent 응답 생성
  3. Retry (max 3) — Mechanical fail 시 재시도
  4. Fallback chain — 모두 실패 시
  5. Game state 업데이트
"""

from dataclasses import dataclass, field

from service.pipeline.policies import DEFAULT_LAYER2_POLICY, Layer2Policy
from service.pipeline.types import Plan

from .gm_agent import GMAgent, GMResponse, MockGMAgent
from .state import GameState


@dataclass
class GameLoopResult:
    """단일 turn 결과."""

    response: str
    game_state: GameState
    attempts: int = 1
    cost_usd: float = 0.0
    fallback_used: bool = False
    error: str | None = None
    mechanical_passed: bool = True
    mechanical_failures: list[str] = field(default_factory=list)


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
    """Game Loop 본체 (★ 자료 Stage 7).

    Retry + Fallback 포함.
    """

    def __init__(
        self,
        gm_agent: GMAgent | MockGMAgent,
        policy: Layer2Policy = DEFAULT_LAYER2_POLICY,
    ) -> None:
        self._gm = gm_agent
        self._policy = policy

    def process_action(
        self,
        plan: Plan,
        state: GameState,
        user_action: str,
    ) -> GameLoopResult:
        """단일 사용자 행동 처리."""
        last_response: GMResponse | None = None

        for attempt in range(self._policy.max_retries + 1):
            response = self._gm.generate_response(plan, state, user_action)
            last_response = response

            if response.error:
                continue

            if response.mechanical_passed:
                state.add_turn(
                    user_action=user_action,
                    gm_response=response.text,
                    cost_usd=response.cost_usd,
                    latency_ms=response.latency_ms,
                )
                return GameLoopResult(
                    response=response.text,
                    game_state=state,
                    attempts=attempt + 1,
                    cost_usd=response.cost_usd,
                    mechanical_passed=True,
                )

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
            )

        return GameLoopResult(
            response="(시스템 오류 발생. 다시 시도해 주세요.)",
            game_state=state,
            attempts=0,
            fallback_used=True,
            error="No response generated",
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
