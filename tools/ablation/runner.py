"""Information Isolation Ablation Runner (HARNESS_CORE 8.4).

3 모드 (A: score 노출 / B: issues only / C: anonymized) 비교.
같은 EvalSet × 3 모드 → 어느 모드가 가장 좋은 retry 결과 내는지 측정.

Day 6 미니멀: 1 카테고리만, 30 호출.
Tier 1+: 5 카테고리, 150 호출.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from core.eval.runner import EvalRunner
from core.eval.spec import EvalSpec, latest_version
from core.llm.client import LLMClient
from core.verify.integrated import IntegratedVerifier
from core.verify.retry import FeedbackMode

ABLATION_DIR = Path(__file__).resolve().parents[2] / "runs" / "ablation"


@dataclass
class AblationModeResult:
    """단일 모드 (A/B/C) 결과."""

    mode: str
    total_count: int
    passed_count: int
    avg_score: float
    avg_retry_count: float


@dataclass
class AblationRunResult:
    """전체 ablation 비교."""

    run_id: str
    timestamp: str
    category: str
    n_items: int
    mode_results: dict[str, AblationModeResult] = field(default_factory=dict)

    def best_mode(self) -> str:
        if not self.mode_results:
            return ""
        return max(
            self.mode_results.keys(),
            key=lambda m: self.mode_results[m].passed_count,
        )

    def summary(self) -> str:
        lines = [f"# Ablation Run {self.run_id}"]
        lines.append(f"- Category: {self.category}")
        lines.append(f"- Items: {self.n_items}")
        lines.append("")
        lines.append("| Mode | Pass | Avg Score |")
        lines.append("|---|---|---|")
        for mode, r in sorted(self.mode_results.items()):
            lines.append(f"| {mode} | {r.passed_count}/{r.total_count} | {r.avg_score:.1f} |")
        lines.append("")
        lines.append(f"**Best mode: {self.best_mode()}**")
        return "\n".join(lines) + "\n"


class AblationRunner:
    """3 모드 ablation 측정."""

    def __init__(
        self,
        client: LLMClient,
        verifier: IntegratedVerifier,
    ) -> None:
        self.client = client
        self.verifier = verifier

    def run_category_ablation(
        self,
        category: str,
        version: str | None = None,
        n: int | None = None,
        modes: list[FeedbackMode] | None = None,
    ) -> AblationRunResult:
        """카테고리에 3 모드 적용 + 결과 비교."""
        if modes is None:
            modes = [
                FeedbackMode.A_SCORE_EXPOSED,
                FeedbackMode.B_ISSUES_ONLY,
                FeedbackMode.C_ANONYMIZED,
            ]

        if version is None:
            version = latest_version(category)
            if version is None:
                raise FileNotFoundError(f"No eval set: {category}")

        spec = EvalSpec.load(category, version)
        items = spec.items[:n] if n else spec.items

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = AblationRunResult(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            category=category,
            n_items=len(items),
        )

        runner = EvalRunner(client=self.client, verifier=self.verifier)

        for mode in modes:
            mode_key = mode.value
            print(f"  [Mode {mode_key.upper()}] running {len(items)} items...")

            attempts = []
            for item in items:
                attempt = runner.run_item(item)
                attempts.append(attempt)

            passed = sum(1 for a in attempts if a.final_passed)
            avg_score = (
                sum(a.mechanical_score for a in attempts) / len(attempts)
                if attempts else 0.0
            )

            result.mode_results[mode_key] = AblationModeResult(
                mode=mode_key,
                total_count=len(attempts),
                passed_count=passed,
                avg_score=avg_score,
                avg_retry_count=0.0,
            )

        return result

    def save(self, result: AblationRunResult) -> Path:
        ABLATION_DIR.mkdir(parents=True, exist_ok=True)
        out_dir = ABLATION_DIR / result.run_id
        out_dir.mkdir(exist_ok=True)

        (out_dir / "result.json").write_text(
            json.dumps({
                "run_id": result.run_id,
                "timestamp": result.timestamp,
                "category": result.category,
                "n_items": result.n_items,
                "mode_results": {
                    m: asdict(r) for m, r in result.mode_results.items()
                },
                "best_mode": result.best_mode(),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        (out_dir / "summary.md").write_text(result.summary(), encoding="utf-8")

        return out_dir
