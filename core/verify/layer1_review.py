"""Layer 1 Verify Agent — Cross-LLM 코드 리뷰 (★ 자기 합리화 차단 시작).

자료 (HARNESS_LAYER1 3장) + 본인 자료 (AutoDev) 정합:
  - Cross-LLM: codex 또는 local qwen (★ claude 제외, 자기 합리화 차단)
  - 정보 격리: git diff만 전달 (★ 점수 X)
  - 5-section prompt (.autodev/agents/code_reviewer.md)
  - JSON output 강제
  - AntiPatternChecker 사전 cheap check
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from core.eval.filter_pipeline import STANDARD_FILTER_PIPELINE
from core.harness.prompt_loader import load_agent_prompt
from core.llm.client import LLMClient, LLMError, Prompt
from core.verify.anti_pattern_check import (
    AntiPatternMatch,
    check_anti_patterns,
    severity_score_penalty,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

MAX_REVIEW_SCORE = 25  # Verify Agent 만점

# 테스트 파일 섹션을 diff에서 제거 (anti-pattern 오탐 방지)
_TEST_PATHS = ("tests/", "test_", "_test.py")


def _strip_test_sections(diff: str) -> str:
    """git diff에서 테스트 파일 섹션 제거."""
    sections = re.split(r"(?=^diff --git )", diff, flags=re.MULTILINE)
    kept = []
    for section in sections:
        header_match = re.match(r"diff --git a/(\S+)", section)
        if header_match:
            file_path = header_match.group(1)
            if any(p in file_path for p in _TEST_PATHS):
                continue
        kept.append(section)
    return "".join(kept)


@dataclass
class ReviewIssue:
    """리뷰 결과의 단일 issue."""

    severity: Literal["critical", "major", "minor"]
    file: str
    line: int
    description: str
    category: str = "other"


@dataclass
class Layer1ReviewResult:
    """Verify Agent 결과 (★ Layer 1 cutoff 18+ 권장)."""

    score: int
    verdict: Literal["pass", "warn", "fail"]
    issues: list[ReviewIssue] = field(default_factory=list)
    summary: str = ""
    anti_pattern_matches: list[AntiPatternMatch] = field(default_factory=list)
    reviewer_model: str = ""
    raw_response: str = ""
    cost_usd: float = 0.0
    error: str | None = None

    @property
    def passed(self) -> bool:
        """자료 cutoff 18+ (72%)."""
        return self.verdict == "pass" and self.score >= 18 and self.error is None


class Layer1ReviewAgent:
    """git diff cross-model 리뷰.

    ★ 본인 환경:
      - Primary: codex (★ OpenAI family)
      - Secondary: local qwen 27B (★ qwen family)
      - ★ claude code (★ 작성자) 제외
    """

    def __init__(
        self,
        reviewer: LLMClient,
        forbidden_reviewers: tuple[str, ...] = ("claude-code", "claude_code", "claude"),
    ) -> None:
        """
        Args:
            reviewer: 검증 LLM
            forbidden_reviewers: ★ Cross-Model 강제. 작성자와 같은 family X.
        """
        self._reviewer = reviewer
        self._forbidden = forbidden_reviewers

        # ★ Cross-Model 검증 (★ 자기 합리화 차단)
        if self._reviewer.model_name in self._forbidden:
            raise ValueError(
                f"Reviewer '{self._reviewer.model_name}' is in forbidden list "
                f"{self._forbidden}. Cross-Model violation."
            )

    def review(
        self,
        ref_old: str = "HEAD~1",
        ref_new: str = "HEAD",
    ) -> Layer1ReviewResult:
        """git diff 가져와서 리뷰."""
        try:
            # 코드 파일만 diff (★ .md/.txt 제외 — 문서 리뷰 불필요)
            proc = subprocess.run(
                [
                    "git", "diff", f"{ref_old}..{ref_new}", "--",
                    "*.py", "*.sh", "*.yaml", "*.yml", "*.json", "*.toml",
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=REPO_ROOT,
            )
            diff = proc.stdout
        except FileNotFoundError:
            return self._fail_result("git not found")

        if not diff.strip():
            return Layer1ReviewResult(
                score=MAX_REVIEW_SCORE,
                verdict="pass",
                summary="No code changes to review (docs-only commit)",
                reviewer_model=self._reviewer.model_name,
            )

        # 2. AntiPattern 사전 cheap check (LLM 호출 0회, 테스트 파일 제외)
        diff_no_tests = _strip_test_sections(diff)
        ap_matches = check_anti_patterns(diff_no_tests, file_path=f"{ref_old}..{ref_new}")
        ap_penalty = severity_score_penalty(ap_matches)

        # 3. LLM 리뷰 (★ 정보 격리: 점수 / verdict 안 알려줌)
        try:
            llm_response = self._call_reviewer(diff)
        except LLMError as e:
            return self._fail_result(f"LLM call failed: {e}")

        # 4. JSON 파싱
        filter_result = STANDARD_FILTER_PIPELINE.extract(llm_response.text)
        if not filter_result.succeeded or not filter_result.parsed:
            return self._fail_result("JSON parsing failed")

        # 5. 결과 구조화
        try:
            data: dict[str, Any] = filter_result.parsed
            score = int(data.get("score", 0))
            verdict_raw = data.get("verdict", "fail")
            if verdict_raw not in ("pass", "warn", "fail"):
                verdict_raw = "fail"
            verdict: Literal["pass", "warn", "fail"] = verdict_raw

            issues: list[ReviewIssue] = []
            for item in data.get("issues", []):
                if not isinstance(item, dict):
                    continue
                issues.append(
                    ReviewIssue(
                        severity=item.get("severity", "major"),
                        file=str(item.get("file", "")),
                        line=int(item.get("line", 0)),
                        description=str(item.get("description", "")),
                        category=str(item.get("category", "other")),
                    )
                )

            summary = str(data.get("summary", ""))
        except (KeyError, TypeError, ValueError) as e:
            return self._fail_result(f"Result parsing failed: {e}")

        # 6. AntiPattern 페널티 적용
        if ap_matches:
            score = max(0, score - ap_penalty)
            for m in ap_matches:
                issues.append(
                    ReviewIssue(
                        severity=m.anti_pattern.severity,
                        file=m.file,
                        line=m.line,
                        description=f"[AntiPattern] {m.anti_pattern.description}",
                        category=m.anti_pattern.id,
                    )
                )
            if any(m.anti_pattern.severity == "critical" for m in ap_matches):
                verdict = "fail"

        cost = getattr(llm_response, "cost_usd", 0.0)
        return Layer1ReviewResult(
            score=score,
            verdict=verdict,
            issues=issues,
            summary=summary,
            anti_pattern_matches=ap_matches,
            reviewer_model=self._reviewer.model_name,
            raw_response=llm_response.text[:1000],
            cost_usd=float(cost),
        )

    def _call_reviewer(self, diff: str) -> Any:
        """LLM 호출 (★ 정보 격리)."""
        prompt_def = load_agent_prompt("code_reviewer")

        # 테스트 섹션 제거 + 크기 제한 (LLM timeout 방지)
        diff_trimmed = _strip_test_sections(diff)[:15000]

        # ★ 정보 격리: score / verdict / threshold 절대 안 줌 — diff만 전달
        user_text = (
            "# GIT DIFF (자기 합리화 차단 — 다른 LLM이 작성한 코드 리뷰)\n\n"
            f"```diff\n{diff_trimmed}\n```\n\n"
            "위 diff를 위 SPEC대로 리뷰. JSON only.\n"
        )

        prompt = Prompt(
            system="You are a strict code reviewer. Output JSON only.",
            user=prompt_def.body + "\n\n---\n\n" + user_text,
        )

        return self._reviewer.generate(prompt, max_tokens=2000)

    def _fail_result(self, error: str) -> Layer1ReviewResult:
        return Layer1ReviewResult(
            score=0,
            verdict="fail",
            error=error,
            reviewer_model=self._reviewer.model_name,
        )
