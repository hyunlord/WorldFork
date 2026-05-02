"""Anti-pattern 자동 감지 (★ 자료 LAYER1 3.3 + 우리 함정 정확).

LLM 호출 0회. 정규식 + 정적 분석.
Verify Agent 진짜 호출 전에 빠른 cheap check.
"""

import re
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AntiPattern:
    """알려진 anti-pattern."""

    id: str
    severity: Literal["critical", "major", "minor"]
    description: str
    pattern: re.Pattern[str]
    suggestion: str = ""


@dataclass
class AntiPatternMatch:
    """검출 결과."""

    anti_pattern: AntiPattern
    file: str
    line: int
    matched_text: str


# ============================================================
# Patterns (★ 우리 함정 정확)
# ============================================================

PATTERNS: list[AntiPattern] = [
    AntiPattern(
        id="hardcoded_score",
        severity="critical",
        description=(
            "Hardcoded score detected. All scores must come from real evaluation."
        ),
        # 세 위치만 허용: .score (속성), (score (kwarg), ^score (독립 변수)
        # MAX_REVIEW_SCORE / _score 접미사는 매칭 X
        pattern=re.compile(
            r"(?:(?<=\.)|(?<=\()|(?<![_A-Za-z\d]))score\s*=\s*"
            r"(?:25|50|65|70|75|80|85|90|95|100)\b",
        ),
        suggestion="Use real LLM call result instead of hardcoded number.",
    ),
    AntiPattern(
        id="info_leak_in_retry",
        severity="critical",
        description=(
            "Score / verdict / threshold leaked to retry feedback. "
            "★ Self-rationalization risk. (AutoDev info isolation)"
        ),
        pattern=re.compile(
            r"retry.*(?:score|verdict|threshold|passed)\s*[=:]",
            re.IGNORECASE,
        ),
        suggestion="Pass only issues + suggestions to retry, not scores.",
    ),
    AntiPattern(
        id="same_model_generate_verify",
        severity="critical",
        description=(
            "Same model used for generate + verify. ★ Cross-Model violation."
        ),
        pattern=re.compile(
            r"(?:generator|coder)\s*=\s*(\w+).*?(?:verifier|reviewer)\s*=\s*\1",
            re.DOTALL,
        ),
        suggestion="Use different model_key for verify (e.g., codex vs claude).",
    ),
    AntiPattern(
        id="made_but_never_used",
        severity="major",
        description=(
            "Class/function declared but never actually used in production code. "
            "★ Self-rationalization through 'we have it' (W2 D5 진단)."
        ),
        pattern=re.compile(
            r"^class\s+(\w+).*?:\s*\n.*?\"\"\".*?(?:TODO|FIXME|placeholder)",
            re.DOTALL | re.MULTILINE,
        ),
        suggestion="Either use it in production code, or remove (YAGNI).",
    ),
    AntiPattern(
        id="mock_only_test",
        severity="major",
        description=(
            "Test uses Mock everywhere — does not validate real behavior. "
            "★ W2 D2-D4 함정 (test pass != system works)."
        ),
        pattern=re.compile(
            r"def test_\w+.*?:\s*\n(?:[^\n]*\n){1,15}\s*"
            r"(?:assert\s+\w+\.(?:passed|success|ok)\b|\s*pass\s*$)",
            re.DOTALL,
        ),
        suggestion=(
            "Add at least 1 integration test that uses real LLM "
            "(or document why Mock-only is sufficient)."
        ),
    ),
    AntiPattern(
        id="external_pkg_added",
        severity="critical",
        description="New external package added to pyproject.toml.",
        # 버전 지정자(>=,<=,==,~=,!=,>,<) 포함한 줄만 — JSON/config 오탐 방지
        pattern=re.compile(
            r"^\+\s*['\"](?!anthropic|httpx|pydantic|pyyaml|"
            r"python-dotenv|jupyterlab|huggingface-hub|"
            r"pytest|pytest-asyncio|pytest-cov|pytest-mock|"
            r"hypothesis|ruff|mypy|types-PyYAML|"
            r"openai|google-generativeai|sqlalchemy|"
            r"llama-cpp-python|streamlit)"
            r"[a-zA-Z][a-zA-Z0-9_.-]*(?:>=|<=|==|~=|!=|>|<|\[)",
            re.MULTILINE,
        ),
        suggestion="External packages 0건 streak. Add to whitelist if exception.",
    ),
]


def check_anti_patterns(
    diff_or_files: str,
    file_path: str = "<diff>",
) -> list[AntiPatternMatch]:
    """Anti-pattern 검출.

    Args:
        diff_or_files: git diff 텍스트 또는 파일 내용
        file_path: 파일 경로 (디버깅)

    Returns:
        매칭 리스트
    """
    matches: list[AntiPatternMatch] = []

    for ap in PATTERNS:
        for match in ap.pattern.finditer(diff_or_files):
            line_n = diff_or_files[: match.start()].count("\n") + 1
            matches.append(
                AntiPatternMatch(
                    anti_pattern=ap,
                    file=file_path,
                    line=line_n,
                    matched_text=match.group(0)[:100],
                )
            )

    return matches


def severity_score_penalty(matches: list[AntiPatternMatch]) -> int:
    """검출 결과 → 점수 차감.

    Critical: -10
    Major: -5
    Minor: -2
    """
    penalty = 0
    for m in matches:
        if m.anti_pattern.severity == "critical":
            penalty += 10
        elif m.anti_pattern.severity == "major":
            penalty += 5
        else:
            penalty += 2
    return penalty
