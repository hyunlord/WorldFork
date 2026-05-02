"""GM Agent (★ Tier 1.5 D4 — IntegratedVerifier + Cross-Model 강제).

★ D4 변경:
  - Cross-Model 강제 (game_llm ≠ verify_llm, 본인 #18)
  - judge_score / total_score / verify_passed 반환
  - TruncationDetectionRule 포함 Mechanical 검증
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
    """GM Agent 응답 (★ D4 풍부 정보)."""

    text: str
    cost_usd: float = 0.0
    latency_ms: int = 0
    mechanical_passed: bool = True
    mechanical_failures: list[str] = field(default_factory=list)

    # ★ D4 추가
    judge_score: float | None = None
    judge_passed: bool | None = None
    total_score: float = 0.0   # 0-100
    verify_passed: bool = True

    error: str | None = None


def _gm_system_prompt(ctx: dict[str, Any]) -> str:
    """GM system prompt (★ Plan 컨텍스트 + 잘림 방지 명시)."""
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
        f"- ★ 한국어만 (한자 X)\n"
        f"- ★ 응답은 반드시 완전한 문장으로 끝낼 것 (다/요/까/.)\n"
        f"- 행동 선택지 3개 이하\n"
    )


class MockGMAgent:
    """Mock GM (★ 테스트용, Layer 2 통합 후도 유지)."""

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
            total_score=100.0,
            verify_passed=True,
        )


class GMAgent:
    """GM Agent (★ Tier 1.5 D4).

    흐름:
      1. Plan + State → 컨텍스트 빌드
      2. system prompt + user prompt
      3. dynamic max_tokens (Layer 1)
      4. LLM 호출 (game_llm)
      5. ★ Mechanical 검증 (TruncationDetectionRule 포함)
      6. ★ 통합 점수 반환

    ★ Cross-Model 강제 (본인 #18):
      - game_llm ≠ verify_llm
      - verify_llm 없으면 Mechanical만 (점수 = Mechanical 100%)
    """

    def __init__(
        self,
        game_llm: GameLLMClient,
        verify_llm: GameLLMClient | None = None,
        mechanical_checker: MechanicalChecker | None = None,
    ) -> None:
        """
        Args:
            game_llm: 게임 응답 생성 LLM
            verify_llm: Cross-Model 검증 LLM (None이면 Mechanical만)
                        game_llm과 같은 모델이면 ValueError
            mechanical_checker: Layer 1 자산 (TruncationDetectionRule 포함)
        """
        if verify_llm is not None and verify_llm.model_name == game_llm.model_name:
            raise ValueError(
                f"Cross-Model violation: game_llm and verify_llm both "
                f"'{game_llm.model_name}'. Use different models (★ 본인 #18)."
            )

        self._game_llm = game_llm
        self._verify_llm = verify_llm
        self._checker = mechanical_checker or MechanicalChecker()

    def generate_response(
        self,
        plan: Plan,
        state: GameState,
        user_action: str,
    ) -> GMResponse:
        """게임 응답 생성 + 검증."""
        ctx = build_game_context(plan, state)
        system = _gm_system_prompt(ctx)
        user_prompt = self._build_user_prompt(state, user_action)
        prompt = Prompt(system=system, user=user_prompt)

        if state.turn == 0:
            max_tokens = 800
        else:
            max_tokens = compute_max_tokens(user_action)

        try:
            response = self._game_llm.generate(prompt, max_tokens=max_tokens)
        except Exception as e:
            return GMResponse(
                text="",
                error=f"LLM call failed: {e}",
                mechanical_passed=False,
                mechanical_failures=[str(e)],
                total_score=0.0,
                verify_passed=False,
            )

        # ★ Mechanical 검증 (TruncationDetectionRule 포함)
        mech_ctx: dict[str, Any] = {
            "language": "ko",
            "character_response": True,
            "user_input": user_action,
        }
        mech_result = self._checker.check(response.text, mech_ctx)

        # ★ 통합 점수
        total_score = 100.0 if mech_result.passed else max(0.0, mech_result.score)
        verify_passed = mech_result.passed

        return GMResponse(
            text=response.text,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            mechanical_passed=mech_result.passed,
            mechanical_failures=[
                f"{f.rule}: {f.detail}" for f in mech_result.failures
            ],
            total_score=total_score,
            verify_passed=verify_passed,
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
