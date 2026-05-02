"""GM Agent (★ Layer 1 자산 활용).

Plan + GameState 컨텍스트로 게임 응답 생성.
Mechanical 룰 + dynamic_token_limiter 적용.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from core.llm.client import LLMResponse, Prompt
from core.llm.dynamic_token_limiter import compute_max_tokens
from core.verify.mechanical import MechanicalChecker
from service.pipeline.types import Plan

from .init_from_plan import build_game_context
from .state import GameState


class GameLLMClient(Protocol):
    @property
    def model_name(self) -> str: ...
    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse: ...


@dataclass
class GMResponse:
    """GM Agent 응답."""

    text: str
    cost_usd: float = 0.0
    latency_ms: int = 0
    mechanical_passed: bool = True
    mechanical_failures: list[str] = field(default_factory=list)
    error: str | None = None


def _gm_system_prompt(ctx: dict[str, Any]) -> str:
    """GM system prompt (★ Plan 컨텍스트 + Layer 1 스타일 룰)."""
    supporting_line = ""
    if ctx["supporting_characters"]:
        supporting_line = (
            "- 조연: "
            + ", ".join(
                f"{c['name']} ({c['role']})"
                for c in ctx["supporting_characters"]
            )
            + "\n"
        )

    return (
        f"당신은 한국어 텍스트 어드벤처 게임의 GM입니다.\n\n"
        f"세계관:\n"
        f"- 작품: {ctx['work_name']} ({ctx['work_genre']})\n"
        f"- 배경: {ctx['world_setting']}\n"
        f"- 톤: {ctx['world_tone']}\n"
        f"- 규칙: {', '.join(ctx['world_rules'])}\n\n"
        f"등장 인물:\n"
        f"- 주인공: {ctx['main_character_name']} ({ctx['main_character_role']})\n"
        f"{supporting_line}\n"
        f"현재 위치: {ctx['current_location']}\n"
        f"현재 턴: {ctx['current_turn']}\n\n"
        f"스타일 규칙:\n"
        f"- 격식체 사용 (...입니다, ...있습니다)\n"
        f"- 자연스러운 격식 (공문서체 X)\n"
        f"- 응답 길이는 유저 액션에 비례\n"
        f"- 한국어만\n"
        f"- 행동 선택지 3개 이하\n"
    )


class MockGMAgent:
    """Mock GM (★ Tier 1-2 본격 호출 X)."""

    def __init__(self, mock_responses: list[str] | None = None) -> None:
        self._responses = mock_responses or [
            "당신은 던전 입구에 도착했습니다. "
            "어두운 통로 앞에서 잠시 멈춰 섰습니다. 어떻게 하시겠습니까?",
        ]
        self._call_count = 0

    def generate_response(
        self,
        plan: Plan,
        state: GameState,
        user_action: str,
    ) -> GMResponse:
        text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return GMResponse(
            text=text,
            cost_usd=0.0,
            latency_ms=10,
            mechanical_passed=True,
            mechanical_failures=[],
        )


class GMAgent:
    """본체 GM Agent (★ Layer 1 자산 활용).

    흐름:
      1. Plan + State → 컨텍스트 빌드
      2. system prompt + user prompt
      3. dynamic max_tokens (Layer 1)
      4. LLM 호출
      5. Mechanical 검증 (Layer 1 10 룰)
      6. 응답 반환
    """

    def __init__(
        self,
        llm_client: GameLLMClient,
        mechanical_checker: MechanicalChecker | None = None,
    ) -> None:
        self._llm = llm_client
        self._checker = mechanical_checker or MechanicalChecker()

    def generate_response(
        self,
        plan: Plan,
        state: GameState,
        user_action: str,
    ) -> GMResponse:
        ctx = build_game_context(plan, state)
        system = _gm_system_prompt(ctx)
        user_prompt = self._build_user_prompt(state, user_action)
        prompt = Prompt(system=system, user=user_prompt)

        max_tokens = compute_max_tokens(user_action)

        try:
            response = self._llm.generate(prompt, max_tokens=max_tokens)
        except Exception as e:
            return GMResponse(
                text="",
                error=f"LLM call failed: {e}",
                mechanical_passed=False,
                mechanical_failures=[str(e)],
            )

        mech_ctx: dict[str, Any] = {
            "language": "ko",
            "character_response": True,
            "user_input": user_action,
        }
        mech_result = self._checker.check(response.text, mech_ctx)

        return GMResponse(
            text=response.text,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            mechanical_passed=mech_result.passed,
            mechanical_failures=[
                f"{f.rule}: {f.detail}" for f in mech_result.failures
            ],
        )

    @staticmethod
    def _build_user_prompt(state: GameState, user_action: str) -> str:
        """최근 history + 현재 액션으로 user prompt 구성."""
        parts: list[str] = []

        if state.history:
            recent = state.history[-1]
            parts.append(
                f"[이전 턴 {recent.turn}]\n"
                f"플레이어: {recent.user_action}\n"
                f"GM: {recent.gm_response[:200]}\n"
            )

        parts.append(f"[현재 턴 {state.turn + 1}]\n플레이어: {user_action}")

        return "\n".join(parts)
