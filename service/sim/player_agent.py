"""PlayerAgent — 자동 player LLM (★ 9B 권장).

본인 본질:
- structured output (JSON action)
- 게임 컨텍스트 본 → 행동 결정
- 비용 ↓ (★ 9B Q3)

본 commit 1차: schema + MockPlayerAgent만 (★ 진짜 LLM은 2차 commit).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .types import PlayerAction, PlayerActionType


class PlayerLLMClient(Protocol):
    """PlayerAgent용 LLM client 인터페이스 (★ 2차 commit 통합)."""

    @property
    def model_name(self) -> str:
        ...

    def generate(self, prompt: Any, **kwargs: Any) -> Any:
        ...


@dataclass
class PlayerAgentResponse:
    """PlayerAgent 응답."""

    action: PlayerAction
    raw_text: str = ""
    cost_usd: float = 0.0
    latency_ms: int = 0


class MockPlayerAgent:
    """Mock PlayerAgent (★ 1차 commit, 단위 테스트가 caller).

    - 회전 mock action 반환
    - 2차 commit이 진짜 LLM 호출 + JSON parsing
    """

    def __init__(self, mock_actions: list[PlayerAction] | None = None) -> None:
        self._actions = mock_actions or [
            PlayerAction(
                action_type=PlayerActionType.WAIT,
                actor_name="비요른",
                rationale="기본 mock action",
            ),
        ]
        self._call_count = 0

    def generate_action(
        self,
        actor_name: str,
        game_context: dict[str, Any],
    ) -> PlayerAgentResponse:
        """단일 action 생성.

        본 commit (1차): mock 회전 (★ LLM X)
        2차 commit: 진짜 LLM 호출 + JSON parsing
        """
        action = self._actions[self._call_count % len(self._actions)]
        # actor_name 진짜 매핑 (★ caller가 전달한 actor)
        action_with_actor = PlayerAction(
            action_type=action.action_type,
            actor_name=actor_name,
            target=action.target,
            rationale=action.rationale,
        )
        self._call_count += 1
        return PlayerAgentResponse(
            action=action_with_actor,
            raw_text=f"mock action {action.action_type.value}",
            cost_usd=0.0,
            latency_ms=10,
        )
