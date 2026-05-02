"""Eval Smoke Test — 카테고리별 2건 × 5 = 10건 빠른 회귀 검증.

★ D1.5 목표: 95%+ pass rate (verify.sh [4/5] 20점 평가 기준)
LLM 호출: Qwen3.5-9B Q3 (8083) — 5초 이하
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.eval.spec import EvalItem, EvalSpec, latest_version, list_categories
from core.llm.client import LLMClient, Prompt
from core.verify.mechanical import MechanicalChecker

EVALS_DIR = Path(__file__).resolve().parents[2] / "evals"

# 카테고리별 샘플링 수 (전체 10건: 5 카테고리 × 2)
SAMPLES_PER_CATEGORY = 2

# 통과 기준
PASS_RATE_THRESHOLD = 0.95


@dataclass
class SmokeAttempt:
    """단일 항목 결과."""

    item_id: str
    category: str
    response_text: str
    mechanical_passed: bool
    mechanical_score: float
    issues: list[str] = field(default_factory=list)


@dataclass
class SmokeResult:
    """전체 smoke 결과."""

    attempts: list[SmokeAttempt] = field(default_factory=list)
    total: int = 0
    passed: int = 0

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    @property
    def succeeded(self) -> bool:
        return self.pass_rate >= PASS_RATE_THRESHOLD


def _sample_items(
    categories: list[str],
    n: int = SAMPLES_PER_CATEGORY,
) -> list[EvalItem]:
    """각 카테고리에서 n건 샘플링 (인덱스 0..n-1 고정)."""
    items: list[EvalItem] = []
    for cat in categories:
        ver = latest_version(cat)
        if ver is None:
            continue
        try:
            spec = EvalSpec.load(cat, ver)
        except FileNotFoundError:
            continue
        items.extend(spec.items[:n])
    return items


def run_smoke(
    llm: LLMClient,
    categories: list[str] | None = None,
    n: int = SAMPLES_PER_CATEGORY,
) -> SmokeResult:
    """Smoke test 실행.

    Args:
        llm: 응답 생성 LLM (Qwen3.5-9B Q3 권장)
        categories: None이면 evals/ 전체 카테고리
        n: 카테고리당 샘플 수
    """
    if categories is None:
        categories = list_categories()

    items = _sample_items(categories, n)
    checker = MechanicalChecker()
    result = SmokeResult(total=len(items))

    for item in items:
        attempt = _run_single(item, llm, checker)
        result.attempts.append(attempt)
        if attempt.mechanical_passed:
            result.passed += 1

    return result


def _run_single(
    item: EvalItem,
    llm: LLMClient,
    checker: MechanicalChecker,
) -> SmokeAttempt:
    """단일 항목 실행."""
    prompt = Prompt(
        system=item.prompt.get("system", ""),
        user=item.prompt.get("user", ""),
    )

    try:
        resp = llm.generate(prompt, max_tokens=256)
        text = resp.text
    except Exception as e:
        return SmokeAttempt(
            item_id=item.id,
            category=item.category,
            response_text="",
            mechanical_passed=False,
            mechanical_score=0.0,
            issues=[f"LLM error: {e}"],
        )

    context: dict[str, Any] = {
        **item.context,
        "category": item.category,
        "expected_behavior": item.expected_behavior,
    }
    mech = checker.check(text, context)

    return SmokeAttempt(
        item_id=item.id,
        category=item.category,
        response_text=text,
        mechanical_passed=mech.passed,
        mechanical_score=mech.score,
        issues=[f.rule for f in mech.failures],
    )
