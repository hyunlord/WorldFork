"""AI Playtester Runner — 인프라만 (Day 6).

실제 30턴 시뮬은 Tier 1+ 본격 (DGX 후).
"""

from dataclasses import dataclass, field
from typing import Any

from core.llm.client import LLMClient

from .persona import Persona, is_compatible


@dataclass
class PlaytesterFinding:
    """페르소나가 발견한 이슈."""

    severity: str
    category: str
    turn_n: int
    description: str
    reproduction_input: str = ""
    reproduction_response: str = ""


@dataclass
class PlaytesterSessionResult:
    """페르소나 1회 세션 결과."""

    persona_id: str
    completed: bool
    n_turns_played: int
    elapsed_seconds: float
    fun_rating: int
    would_replay: bool
    abandoned: bool
    abandon_reason: str | None
    abandon_turn: int | None
    findings: list[PlaytesterFinding] = field(default_factory=list)
    playthrough_log: list[dict[str, Any]] = field(default_factory=list)


class PlaytesterError(Exception):
    """Playtester 실행 오류."""
    pass


class PlaytesterRunner:
    """AI Playtester 실행기.

    Day 6: 인프라만 (실제 30턴은 Tier 1+).
    """

    def __init__(
        self,
        persona: Persona,
        game_client: LLMClient,
        playtester_client: LLMClient,
    ) -> None:
        if not is_compatible(persona, game_client.model_name):
            raise PlaytesterError(
                f"Persona '{persona.id}' incompatible with game LLM "
                f"'{game_client.model_name}' (forbidden: {persona.forbidden_game_llms})"
            )

        self.persona = persona
        self.game_client = game_client
        self.playtester_client = playtester_client

    def run_session(
        self,
        scenario_id: str,
        max_turns: int = 30,
        time_limit_seconds: float = 1800,
    ) -> PlaytesterSessionResult:
        """페르소나로 게임 1회 시뮬레이트.

        Day 6 placeholder: Tier 1+에서 본격 구현.
        """
        raise NotImplementedError(
            "PlaytesterRunner.run_session() is Tier 1+ feature. "
            "Day 6 provides infrastructure only."
        )
