"""6 페르소나 배치 실행 (직렬, 메모리 안전).

★ Tier 1 W1 D4:
  - 6 페르소나 × 1세션 = 6 호출
  - 직렬 실행 (병렬 X)
  - 각 세션 사이 sleep 5 (CLI / GPU 안정)
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.llm.cli_client import CLIClient
from core.llm.client import LLMClient

from .persona import list_personas, load_persona
from .runner import (
    PlaytesterError,
    PlaytesterRunner,
    PlaytesterSessionResult,
)


@dataclass
class BatchRunResult:
    """배치 실행 결과."""

    timestamp: str
    work_name: str
    sessions: list[PlaytesterSessionResult] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)


class BatchRunner:
    """6 페르소나 배치 (Tier 1)."""

    def __init__(
        self,
        game_client: LLMClient,
        sleep_between: float = 5.0,
    ) -> None:
        self.game_client = game_client
        self.sleep_between = sleep_between

    def run_all(
        self,
        work_name: str = "novice_dungeon_run",
        max_turns_per_session: int = 30,
        tier_0_personas: list[str] | None = None,
        tier_1_personas: list[str] | None = None,
    ) -> BatchRunResult:
        """모든 페르소나 1회씩 실행 (직렬)."""
        if tier_0_personas is None:
            tier_0_personas = list_personas("tier_0")
        if tier_1_personas is None:
            tier_1_personas = list_personas("tier_1")

        result = BatchRunResult(
            timestamp=datetime.now().isoformat(),
            work_name=work_name,
        )

        all_personas: list[tuple[str, str]] = (
            [(pid, "tier_0") for pid in tier_0_personas]
            + [(pid, "tier_1") for pid in tier_1_personas]
        )

        print(f"=== Batch Run: {len(all_personas)} personas ===")
        print(f"  Game LLM: {self.game_client.model_name}")
        print(f"  Work: {work_name}")
        print()

        for i, (pid, tier) in enumerate(all_personas, 1):
            print(f"[{i}/{len(all_personas)}] {pid} ({tier})")

            try:
                persona = load_persona(pid, tier=tier)
                # cli_to_use: "claude-code" → "claude_code"
                cli_key = persona.cli_to_use.replace("-", "_")
                playtester = CLIClient(model_key=cli_key)

                runner = PlaytesterRunner(
                    persona=persona,
                    game_client=self.game_client,
                    playtester_client=playtester,
                )

                session = runner.run_session(
                    work_name=work_name,
                    max_turns=max_turns_per_session,
                )
                result.sessions.append(session)

                print(
                    f"    Completed: {session.completed}, "
                    f"turns: {session.n_turns_played}, "
                    f"fun: {session.fun_rating}, "
                    f"findings: {len(session.findings)}"
                )

                PlaytesterRunner.save(session)

            except PlaytesterError as e:
                print(f"    SKIPPED: {e}")
                result.skipped.append((pid, str(e)))
            except Exception as e:
                print(f"    ERROR: {e}")
                result.skipped.append((pid, f"unexpected: {e}"))

            if i < len(all_personas):
                print(f"    sleep {self.sleep_between}s...")
                time.sleep(self.sleep_between)

        return result

    @staticmethod
    def aggregate_findings(result: BatchRunResult) -> dict[str, Any]:
        """배치 결과 집계."""
        all_findings = [f for s in result.sessions for f in s.findings]

        by_severity: dict[str, int] = {}
        for f in all_findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

        by_category: dict[str, int] = {}
        for f in all_findings:
            by_category[f.category] = by_category.get(f.category, 0) + 1

        by_persona: dict[str, dict[str, Any]] = {
            s.persona_id: {
                "completed": s.completed,
                "fun": s.fun_rating,
                "findings": len(s.findings),
                "turns": s.n_turns_played,
            }
            for s in result.sessions
        }

        avg_fun = (
            sum(s.fun_rating for s in result.sessions) / len(result.sessions)
            if result.sessions
            else 0.0
        )

        return {
            "total_sessions": len(result.sessions),
            "skipped": len(result.skipped),
            "total_findings": len(all_findings),
            "by_severity": by_severity,
            "by_category": by_category,
            "by_persona": by_persona,
            "avg_fun": avg_fun,
        }
