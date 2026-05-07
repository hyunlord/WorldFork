"""GM Agent (★ Tier 1.5 D4 — IntegratedVerifier + Cross-Model 강제).

★ D4 변경:
  - Cross-Model 강제 (game_llm ≠ verify_llm, 본인 #18)
  - judge_score / total_score / verify_passed 반환
  - TruncationDetectionRule 포함 Mechanical 검증
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from core.llm.client import LLMClient, LLMResponse, Prompt
from core.llm.game_token_policy import compute_game_max_tokens
from core.verify.integrated import IntegratedVerifier
from core.verify.llm_judge import JudgeCriteria, LLMJudge
from core.verify.mechanical import MechanicalChecker
from service.pipeline.types import Plan

from .init_from_plan import build_game_context
from .state import GameState

# ★ 게임 응답 검증 기준 (★ Cross-Model LLM Judge용, A1.5)
GAME_CRITERIA = JudgeCriteria(
    name="game_response_quality",
    description="한국어 텍스트 어드벤처 게임 응답의 품질 평가",
    dimensions=[
        "한국어 자연스러움 (한자/외국어 혼입 X)",
        "캐릭터 페르소나 일관성",
        "세계관 일관성",
        "사용자 행동에 대한 적절한 반응",
        "응답 완결성 (잘림 X)",
    ],
)


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

    main_name = ctx["main_character_name"]

    # ★ Tier 2 D12: v2_characters 진짜 사용 (★ Made But Never Used 차단)
    # build_game_context()가 제공하는 v2 schema 정보를 prompt에 진짜 반영
    v2_block = ""
    v2_chars = ctx.get("v2_characters") or {}
    if v2_chars:
        v2_lines = []
        for name, info in v2_chars.items():
            parts = [f"  - {name}"]
            race = info.get("race")
            sub_race = info.get("sub_race")
            if race:
                if sub_race:
                    parts.append(f"종족: {race}/{sub_race}")
                else:
                    parts.append(f"종족: {race}")
            hp = info.get("hp")
            hp_max = info.get("hp_max")
            if hp is not None and hp_max:
                parts.append(f"HP: {hp}/{hp_max}")
            v2_lines.append(", ".join(parts))
        v2_block = "캐릭터 스탯 (★ 작품 본질):\n" + "\n".join(v2_lines) + "\n\n"

    return (
        f"당신은 한국어 텍스트 어드벤처 게임의 GM입니다.\n\n"
        f"세계관:\n"
        f"- 작품: {ctx['work_name']} ({ctx['work_genre']})\n"
        f"- 배경: {ctx['world_setting']}\n"
        f"- 톤: {ctx['world_tone']}\n"
        f"- 규칙: {', '.join(ctx['world_rules'])}\n\n"
        f"등장 인물:\n"
        f"- 주인공: {main_name} ({ctx['main_character_role']})\n"
        f"{supporting_line}\n"
        f"{v2_block}"
        f"현재 위치: {ctx['current_location']}\n"
        f"현재 턴: {ctx['current_turn']}\n\n"
        f"스타일 규칙:\n"
        f"- 격식체 사용 (...입니다, ...있습니다)\n"
        f"- 자연스러운 격식 (공문서체 X)\n"
        f"- 응답 길이는 유저 액션에 비례\n"
        f"- ★ 한국어만 (한자 X)\n"
        f"- ★ 응답은 반드시 완전한 문장으로 끝낼 것 (다/요/까/.)\n\n"
        f"호칭 규칙 (★ 본인 finding #5):\n"
        f"- 주인공 호칭은 '{main_name}'으로 일관되게\n"
        f"- '플레이어', '플레이어님' 같은 메타 단어 절대 사용 X\n"
        f"- 또는 2인칭 '당신'을 일관되게 사용 (★ 섞어 쓰기 X)\n\n"
        f"진행 규칙 (★ 본인 finding #4):\n"
        f"- 매 턴 위치 변화 또는 새 이벤트가 발생 (★ 단순 반복 X)\n"
        f"- 같은 묘사 / 같은 선택지 반복 절대 X\n"
        f"- 주인공 행동에 따라 NPC, 환경, 단서가 진짜 다르게 등장\n"
        f"- 이전 턴의 결과가 현재 턴에 반영 (★ 인과관계)\n\n"
        f"응답 구조 (★ 본인 finding #1):\n"
        f"- 묘사: 2-4 문장 (★ 현재 상황, 감각, 분위기)\n"
        f"- 선택지: 매 턴 정확히 3개 (★ 첫 턴 포함)\n"
        f"  - 형식: '1. ...', '2. ...', '3. ...' (★ 새 줄 분리)\n"
        f"  - 각 선택지는 서로 다른 방향 / 결과를 암시\n"
        f"  - 단순 변형 X (★ '빠르게'/'천천히' 같은 속도 차이만 X)\n"
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
        verify_llm: LLMClient | None = None,
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
        mechanical = mechanical_checker or MechanicalChecker()
        self._checker = mechanical  # 호환성 유지 (★ 기존 tests용)

        # ★ ★ A1.5: IntegratedVerifier (Mechanical + LLM Judge 진짜 통합)
        # verify_llm 있으면 LLMJudge 활성화 (★ Cross-Model)
        judge: LLMJudge | None = None
        if verify_llm is not None:
            judge = LLMJudge(judge_client=verify_llm)
        self._verifier = IntegratedVerifier(
            mechanical=mechanical,
            judge=judge,
            skip_judge_on_critical=True,  # critical 시 judge 스킵 (비용/지연 ↓)
        )

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
            max_tokens = compute_game_max_tokens(user_action)

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

        # ★ ★ ★ A1.5: 통합 검증 (Mechanical + LLM Judge, ★ verify_llm 진짜 호출!)
        verify_ctx: dict[str, Any] = {
            "language": "ko",
            "character_response": True,
            "user_input": user_action,
        }
        # criteria는 verify_llm 있을 때만 (★ judge 호출 결정)
        criteria = GAME_CRITERIA if self._verify_llm is not None else None
        integrated_result = self._verifier.verify(
            response.text, verify_ctx, criteria=criteria
        )
        mech_result = integrated_result.mechanical

        # ★ 통합 점수: Judge 호출됐으면 judge.score, 아니면 Mechanical 기준
        if integrated_result.judge is not None:
            total_score = integrated_result.judge.score
        else:
            # ★ hardcoded 100.0 차단 (codex 5.5 진단) — mech_result.score 진짜 점수
            total_score = mech_result.score
        verify_passed = integrated_result.passed

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
        """최근 history + 현재 액션으로 user prompt 구성.

        ★ 본인 풀 플레이 finding 반영:
          - finding #3: history 1턴 → 3턴, 200자 → 500자 (★ 이전 선택 반영)
          - finding #1: 첫 턴 (state.turn==0) 명시 (★ 빈 입력도 시작)
          - finding #4: 일반 턴에서 '결과 반영 + 새 이벤트' 명시
        """
        parts: list[str] = []

        # ★ 최근 3턴 (★ finding #3, 1 → 3)
        if state.history:
            recent_turns = state.history[-3:]
            for h in recent_turns:
                parts.append(
                    f"[이전 턴 {h.turn}]\n"
                    f"플레이어: {h.user_action}\n"
                    f"GM: {h.gm_response[:500]}\n"  # ★ 200 → 500
                )

        # ★ 현재 턴 — 첫 턴 vs 일반 턴 분기 (★ finding #1, #4)
        if state.turn == 0:
            parts.append(
                f"[현재 턴 {state.turn + 1}] (★ 게임 시작)\n"
                f"플레이어: {user_action or '시작'}\n"
                f"GM: 시작 위치 묘사 + 3가지 행동 선택지 제공"
            )
        elif state.history:
            parts.append(
                f"[현재 턴 {state.turn + 1}]\n"
                f"플레이어가 '{user_action}'를 선택했음.\n"
                f"위 선택의 결과를 반영하여 진행 + 새 3가지 선택지 제공.\n"
                f"이전 묘사와 다른 새 위치/이벤트/단서 등장 (★ 단순 반복 X).\n"
                f"플레이어: {user_action}"
            )
        else:
            parts.append(f"[현재 턴 {state.turn + 1}]\n플레이어: {user_action}")

        return "\n".join(parts)
