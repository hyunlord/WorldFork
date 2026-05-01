"""Tier 1 W1 D2: Local LLM Baseline Runner.

50 케이스 × 3 Local 모델 = 150 호출.
두 verifier 모드:
  - Mode 1: Cross-Model strict (claude-code) — 자료 권장
  - Mode 2: Local-only (27B Q2) — ★ 본인 인사이트

메모리 안전:
  - 직렬 실행 (병렬 X)
  - 각 호출 사이 sleep 0.1
  - 결과 즉시 디스크 저장 (메모리 누적 X)
"""

import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.eval.spec import EvalItem, EvalSpec, list_categories
from core.llm.client import LLMClient, Prompt
from core.llm.local_client import (
    get_qwen35_9b_q3,
    get_qwen36_27b_q2,
    get_qwen36_27b_q3,
)
from core.verify.llm_judge import JudgeCriteria, JudgeScore, LLMJudge
from core.verify.mechanical import MechanicalChecker


def _git_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).resolve().parents[2],
        )
        return r.stdout.strip() if r.returncode == 0 else "no-git"
    except FileNotFoundError:
        return "no-git"


@dataclass
class BaselineAttempt:
    """단일 케이스 측정."""

    item_id: str
    category: str
    generator: str

    # Mechanical
    mechanical_passed: bool
    mechanical_score: float

    # LLM Judge Mode 1 (Cross-Model strict)
    judge_cm_score: float | None
    judge_cm_verdict: str | None
    judge_cm_model: str | None

    # LLM Judge Mode 2 (Local-only, ★ 본인 인사이트)
    judge_local_score: float | None
    judge_local_verdict: str | None
    judge_local_model: str | None

    response_text: str
    response_latency_ms: int
    response_tokens_out: int

    issues: list[str] = field(default_factory=list)


@dataclass
class BaselineRunResult:
    """전체 baseline 측정 결과."""

    timestamp: str
    git_sha: str
    config: dict[str, Any]
    attempts: list[BaselineAttempt] = field(default_factory=list)


class BaselineRunner:
    """Tier 1 baseline 측정.

    ★ 두 verifier 모드 동시 측정 (같은 응답을 두 번 verify):
      - Cross-Model strict (자료 원칙)
      - Local-only (본인 인사이트)
    """

    def __init__(
        self,
        generators: dict[str, LLMClient],
        cm_verifier: LLMClient,
        local_verifier: LLMClient,
    ) -> None:
        self.generators = generators
        self.cm_verifier = cm_verifier
        self.local_verifier = local_verifier

        self.mechanical = MechanicalChecker()
        self.cm_judge = LLMJudge(judge_client=cm_verifier)
        self.local_judge = LLMJudge(judge_client=local_verifier)

    def run_item(
        self,
        generator_key: str,
        item: EvalItem,
    ) -> BaselineAttempt:
        """단일 EvalItem × 단일 generator 측정."""
        client = self.generators[generator_key]
        prompt = Prompt(
            system=item.prompt.get("system", ""),
            user=item.prompt.get("user", ""),
        )

        try:
            start = time.time()
            response = client.generate(prompt, max_tokens=200)
            latency_ms = int((time.time() - start) * 1000)
        except Exception as e:
            return BaselineAttempt(
                item_id=item.id,
                category=item.category,
                generator=generator_key,
                mechanical_passed=False,
                mechanical_score=0.0,
                judge_cm_score=None,
                judge_cm_verdict=None,
                judge_cm_model=None,
                judge_local_score=None,
                judge_local_verdict=None,
                judge_local_model=None,
                response_text=f"<ERROR: {e}>",
                response_latency_ms=0,
                response_tokens_out=0,
                issues=[f"Generation failed: {e}"],
            )

        mech_result = self.mechanical.check(response.text, item.context)

        criteria = JudgeCriteria(
            name=item.criteria,
            description=str(item.expected_behavior),
            dimensions=[],
        )

        # Mode 1: Cross-Model strict
        judge_cm_score: float | None = None
        judge_cm_verdict: str | None = None
        judge_cm_model: str | None = None
        try:
            cm_result: JudgeScore = self.cm_judge.evaluate(
                response=response.text,
                criteria=criteria,
                context=item.context,
            )
            judge_cm_score = cm_result.score
            judge_cm_verdict = cm_result.verdict
            judge_cm_model = self.cm_verifier.model_name
        except Exception as e:
            print(f"    [CM Judge fail] {e}")

        # Mode 2: Local-only (★ 본인 인사이트)
        judge_local_score: float | None = None
        judge_local_verdict: str | None = None
        judge_local_model: str | None = None
        try:
            local_result: JudgeScore = self.local_judge.evaluate(
                response=response.text,
                criteria=criteria,
                context=item.context,
            )
            judge_local_score = local_result.score
            judge_local_verdict = local_result.verdict
            judge_local_model = self.local_verifier.model_name
        except Exception as e:
            print(f"    [Local Judge fail] {e}")

        return BaselineAttempt(
            item_id=item.id,
            category=item.category,
            generator=generator_key,
            mechanical_passed=mech_result.passed,
            mechanical_score=mech_result.score,
            judge_cm_score=judge_cm_score,
            judge_cm_verdict=judge_cm_verdict,
            judge_cm_model=judge_cm_model,
            judge_local_score=judge_local_score,
            judge_local_verdict=judge_local_verdict,
            judge_local_model=judge_local_model,
            response_text=response.text,
            response_latency_ms=latency_ms,
            response_tokens_out=response.output_tokens,
            issues=[
                f"[{f.rule}] {f.detail}"
                for f in mech_result.failures
            ],
        )

    def run_all(
        self,
        n_per_category: int = 10,
        sleep_between: float = 0.1,
    ) -> BaselineRunResult:
        """전체 baseline 실행 (직렬, 메모리 안전).

        Args:
            n_per_category: 카테고리당 케이스 수 (기본 10)
            sleep_between: 각 호출 사이 sleep (서버 안정)
        """
        result = BaselineRunResult(
            timestamp=datetime.now().isoformat(),
            git_sha=_git_sha(),
            config={
                "n_per_category": n_per_category,
                "generators": list(self.generators.keys()),
                "cm_verifier": self.cm_verifier.model_name,
                "local_verifier": self.local_verifier.model_name,
            },
        )

        categories = list_categories()
        total_cases = len(categories) * n_per_category
        total_calls = total_cases * len(self.generators)

        print("=== Baseline Runner ===")
        print(f"  Generators: {list(self.generators.keys())}")
        print(f"  CM Verifier: {self.cm_verifier.model_name}")
        print(f"  Local Verifier: {self.local_verifier.model_name}")
        print(f"  Categories: {len(categories)}")
        print(f"  Total cases: {total_cases}")
        print(f"  Total LLM calls: ~{total_calls * 3} (gen + 2 judge)")
        print()

        call_count = 0

        for cat in categories:
            print(f"\n--- Category: {cat} ---")
            spec = EvalSpec.load(cat, "v1")
            items = spec.items[:n_per_category]

            for item in items:
                for gen_key in self.generators:
                    call_count += 1
                    print(
                        f"  [{call_count}/{total_calls}] {gen_key} | {item.id}",
                        flush=True,
                    )
                    attempt = self.run_item(gen_key, item)
                    result.attempts.append(attempt)

                    if call_count % 10 == 0:
                        self._save_partial(result)

                    time.sleep(sleep_between)

        return result

    def _save_partial(self, result: BaselineRunResult) -> None:
        path = Path("runs/tier_1_w1_d2_baseline.partial.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "timestamp": result.timestamp,
            "git_sha": result.git_sha,
            "config": result.config,
            "attempts_so_far": len(result.attempts),
            "attempts": [asdict(a) for a in result.attempts],
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def save(self, result: BaselineRunResult) -> Path:
        """최종 결과 저장."""
        path = Path("runs/tier_1_w1_d2_baseline.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "timestamp": result.timestamp,
            "git_sha": result.git_sha,
            "config": result.config,
            "attempts": [asdict(a) for a in result.attempts],
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path


def make_default_runner(cm_verifier: LLMClient | None = None) -> BaselineRunner:
    """기본 설정 BaselineRunner 생성."""
    from core.llm.cli_client import CLIClient

    generators: dict[str, LLMClient] = {
        "qwen36-27b-q3": get_qwen36_27b_q3(),
        "qwen36-27b-q2": get_qwen36_27b_q2(),
        "qwen35-9b-q3": get_qwen35_9b_q3(),
    }
    _cm = cm_verifier if cm_verifier is not None else CLIClient(model_key="claude_code")
    _local = get_qwen36_27b_q2()

    return BaselineRunner(
        generators=generators,
        cm_verifier=_cm,
        local_verifier=_local,
    )
