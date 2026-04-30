"""EvalRunner — 자동 평가 실행 (HARNESS_CORE 5+6).

Day 5: 단순 runner (인프라만).
Day 6+: AI Playtester 통합.
Tier 1+: 병렬 + 캐싱.
"""

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from core.llm.client import LLMClient, Prompt
from core.verify.integrated import IntegratedVerifier
from core.verify.llm_judge import JudgeCriteria

from .scoring import EvalScore, score_results
from .spec import EvalItem, EvalSpec, latest_version

RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"


@dataclass
class EvalAttempt:
    """단일 EvalItem 평가 결과."""

    item_id: str
    category: str
    response_text: str
    mechanical_passed: bool
    mechanical_score: float
    judge_score: float | None
    judge_verdict: str | None
    final_passed: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class EvalRunResult:
    """전체 eval run 결과."""

    run_id: str
    timestamp: str
    git_sha: str
    config: dict[str, Any]
    attempts: list[EvalAttempt] = field(default_factory=list)
    score: EvalScore | None = None

    def total_count(self) -> int:
        return len(self.attempts)

    def passed_count(self) -> int:
        return sum(1 for a in self.attempts if a.final_passed)

    def pass_rate(self) -> float:
        if not self.attempts:
            return 0.0
        return self.passed_count() / self.total_count()


def _git_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=False,
            cwd=Path(__file__).resolve().parents[2],
        )
        return r.stdout.strip() if r.returncode == 0 else "no-git"
    except FileNotFoundError:
        return "no-git"


class EvalRunner:
    """카테고리별 EvalSet 실행 + 평가."""

    def __init__(self, client: LLMClient, verifier: IntegratedVerifier):
        self.client = client
        self.verifier = verifier

    def run_item(self, item: EvalItem) -> EvalAttempt:
        """단일 EvalItem 실행."""
        prompt = Prompt(
            system=item.prompt.get("system", ""),
            user=item.prompt.get("user", ""),
        )

        try:
            response = self.client.generate(prompt)
            response_text = response.text
        except Exception as e:
            return EvalAttempt(
                item_id=item.id,
                category=item.category,
                response_text=f"<ERROR: {e}>",
                mechanical_passed=False,
                mechanical_score=0.0,
                judge_score=None,
                judge_verdict=None,
                final_passed=False,
                issues=[f"Generation failed: {e}"],
            )

        criteria = JudgeCriteria(
            name=item.criteria,
            description=str(item.expected_behavior),
            dimensions=[],
        )
        try:
            verify_result = self.verifier.verify(response_text, item.context, criteria=criteria)
        except Exception as e:
            return EvalAttempt(
                item_id=item.id,
                category=item.category,
                response_text=response_text,
                mechanical_passed=False,
                mechanical_score=0.0,
                judge_score=None,
                judge_verdict=None,
                final_passed=False,
                issues=[f"Verification failed: {e}"],
            )

        issues: list[str] = [
            f"[{f.rule}] {f.detail}"
            for f in verify_result.mechanical.failures
        ]
        if verify_result.judge:
            issues.extend(verify_result.judge.issues)

        return EvalAttempt(
            item_id=item.id,
            category=item.category,
            response_text=response_text,
            mechanical_passed=verify_result.mechanical.passed,
            mechanical_score=verify_result.mechanical.score,
            judge_score=verify_result.judge.score if verify_result.judge else None,
            judge_verdict=verify_result.judge.verdict if verify_result.judge else None,
            final_passed=verify_result.passed,
            issues=issues,
        )

    def run_category(
        self,
        category: str,
        version: str | None = None,
        n: int | None = None,
    ) -> EvalRunResult:
        """카테고리 전체 (또는 n개) 실행."""
        if version is None:
            version = latest_version(category)
            if version is None:
                raise FileNotFoundError(f"No eval set for category: {category}")

        spec = EvalSpec.load(category, version)
        items = spec.items[:n] if n else spec.items

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + _git_sha()
        result = EvalRunResult(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            git_sha=_git_sha(),
            config={
                "category": category,
                "version": version,
                "n": len(items),
                "client_model": self.client.model_name,
                "fingerprint": spec.fingerprint,
            },
        )

        for i, item in enumerate(items, 1):
            print(f"  [{i}/{len(items)}] {item.id}...", flush=True)
            attempt = self.run_item(item)
            result.attempts.append(attempt)

        result.score = score_results(result.attempts)
        return result

    def save(self, result: EvalRunResult) -> Path:
        """결과를 runs/{run_id}/에 저장."""
        out_dir = RUNS_DIR / result.run_id
        out_dir.mkdir(parents=True, exist_ok=True)

        (out_dir / "config.yaml").write_text(
            yaml.safe_dump(result.config, allow_unicode=True),
            encoding="utf-8",
        )

        (out_dir / "eval_results.json").write_text(
            json.dumps({
                "run_id": result.run_id,
                "timestamp": result.timestamp,
                "git_sha": result.git_sha,
                "score": asdict(result.score) if result.score else None,
                "attempts": [asdict(a) for a in result.attempts],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary = self._format_summary(result)
        (out_dir / "summary.md").write_text(summary, encoding="utf-8")

        return out_dir

    @staticmethod
    def _format_summary(result: EvalRunResult) -> str:
        lines = [
            f"# Eval Run {result.run_id}",
            "",
            f"- Timestamp: {result.timestamp}",
            f"- Git SHA: {result.git_sha}",
            f"- Config: {result.config}",
            "",
            "## 결과",
            f"- 전체: {result.total_count()}",
            f"- 통과: {result.passed_count()} ({result.pass_rate():.1%})",
        ]

        if result.score:
            lines.extend([
                "",
                "## 점수",
                f"- Total: {result.score.total:.1f}/100",
                f"- Mechanical avg: {result.score.mechanical_avg:.1f}",
                (
                    f"- Judge avg: {result.score.judge_avg:.1f}"
                    if result.score.judge_avg
                    else "- Judge: N/A"
                ),
            ])

        failed = [a for a in result.attempts if not a.final_passed]
        if failed:
            lines.extend(["", "## 실패 케이스"])
            for a in failed[:10]:
                lines.append(f"- `{a.item_id}` ({a.category})")
                for issue in a.issues[:3]:
                    lines.append(f"  - {issue}")

        return "\n".join(lines) + "\n"
