"""6 페르소나 배치 실행 (직렬, 메모리 안전).

★ Tier 1 W1 D4:
  - 6 페르소나 × 1세션 = 6 호출
  - 직렬 실행 (병렬 X)
  - 각 세션 사이 sleep 5 (CLI / GPU 안정)

★ Tier 1 W1 D5:
  - backup_cli fallback (shutil.which 가용성 체크)
"""

import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.llm.cli_client import CLIClient, _load_registry
from core.llm.client import LLMClient

from .persona import Persona, list_personas, load_persona
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
                playtester = self._create_playtester_with_fallback(persona)

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

    def _create_playtester_with_fallback(self, persona: Persona) -> CLIClient:
        """CLI 가용성 확인 후 backup_cli fallback.

        Args:
            persona: cli_to_use / backup_cli 필드 사용

        Returns:
            CLIClient (primary 가능이면 primary, 아니면 backup)

        Raises:
            PlaytesterError: primary / backup 둘 다 불가 시
        """
        primary_key = persona.cli_to_use.replace("-", "_")

        if self._is_cli_available(primary_key):
            return CLIClient(model_key=primary_key)

        print(f"    [fallback] {primary_key} not available, trying backup")

        if persona.backup_cli is None:
            raise PlaytesterError(
                f"Persona '{persona.id}' has no backup_cli, "
                f"primary {primary_key} unavailable"
            )

        backup_key = persona.backup_cli.replace("-", "_")

        # Cross-Model 강제: backup_cli도 forbidden_game_llms에 없어야 함
        if backup_key in persona.forbidden_game_llms:
            raise PlaytesterError(
                f"Persona '{persona.id}' backup_cli '{backup_key}' is in "
                f"forbidden_game_llms. Cannot fallback."
            )

        if self._is_cli_available(backup_key):
            print(f"    [fallback] using backup {backup_key}")
            return CLIClient(model_key=backup_key)

        raise PlaytesterError(
            f"Persona '{persona.id}': backup {backup_key} also unavailable"
        )

    @staticmethod
    def _is_cli_available(cli_key: str) -> bool:
        """CLI 명령이 시스템 PATH에 있는지 확인."""
        try:
            registry = _load_registry()
            command: str = registry["models"][cli_key]["command"]
            return shutil.which(command) is not None
        except Exception:
            return False

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
