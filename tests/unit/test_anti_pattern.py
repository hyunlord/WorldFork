"""Tier 1.5 D1 작업 4: Anti-pattern 테스트."""

from core.verify.anti_pattern_check import (
    PATTERNS,
    AntiPatternMatch,
    check_anti_patterns,
    severity_score_penalty,
)


class TestHardcodedScore:
    def test_detect_return_score_70(self) -> None:
        code = 'def fake_review():\n    return ReviewResult(score=70, verdict="pass")\n'
        matches = check_anti_patterns(code)
        assert any(m.anti_pattern.id == "hardcoded_score" for m in matches)

    def test_detect_score_assignment_95(self) -> None:
        code = "result.score = 95\n"
        matches = check_anti_patterns(code)
        assert any(m.anti_pattern.id == "hardcoded_score" for m in matches)

    def test_no_false_positive_real_eval(self) -> None:
        code = (
            "def real_review(text):\n"
            "    response = llm.call(text)\n"
            "    return ReviewResult(score=response.parsed_score, verdict=response.verdict)\n"
        )
        matches = check_anti_patterns(code)
        hardcoded = [m for m in matches if m.anti_pattern.id == "hardcoded_score"]
        assert len(hardcoded) == 0


class TestInfoLeakInRetry:
    def test_retry_with_score(self) -> None:
        code = "retry_feedback.score = 85\n"
        matches = check_anti_patterns(code)
        assert any(m.anti_pattern.id == "info_leak_in_retry" for m in matches)

    def test_retry_verdict_leak(self) -> None:
        code = "retry: verdict = pass\n"
        matches = check_anti_patterns(code)
        assert any(m.anti_pattern.id == "info_leak_in_retry" for m in matches)


class TestExternalPackage:
    def test_external_pkg_diff(self) -> None:
        diff = '+    "requests>=2.31",\n+    "numpy>=1.24",\n'
        matches = check_anti_patterns(diff)
        external = [m for m in matches if m.anti_pattern.id == "external_pkg_added"]
        assert len(external) >= 1

    def test_existing_pkg_no_alert(self) -> None:
        diff = '+    "anthropic>=0.40",\n'
        matches = check_anti_patterns(diff)
        external = [m for m in matches if m.anti_pattern.id == "external_pkg_added"]
        assert len(external) == 0

    def test_pytest_ok(self) -> None:
        diff = '+    "pytest>=8.0",\n'
        matches = check_anti_patterns(diff)
        external = [m for m in matches if m.anti_pattern.id == "external_pkg_added"]
        assert len(external) == 0


class TestSeverityPenalty:
    def test_critical_penalty(self) -> None:
        critical_pattern = next(p for p in PATTERNS if p.severity == "critical")
        match = AntiPatternMatch(
            anti_pattern=critical_pattern,
            file="x",
            line=1,
            matched_text="x",
        )
        penalty = severity_score_penalty([match])
        assert penalty == 10

    def test_major_penalty(self) -> None:
        major_pattern = next(p for p in PATTERNS if p.severity == "major")
        match = AntiPatternMatch(
            anti_pattern=major_pattern,
            file="x",
            line=1,
            matched_text="x",
        )
        penalty = severity_score_penalty([match])
        assert penalty == 5

    def test_empty_matches_zero(self) -> None:
        assert severity_score_penalty([]) == 0

    def test_cumulative_penalty(self) -> None:
        critical = next(p for p in PATTERNS if p.severity == "critical")
        major = next(p for p in PATTERNS if p.severity == "major")
        matches = [
            AntiPatternMatch(anti_pattern=critical, file="x", line=1, matched_text="x"),
            AntiPatternMatch(anti_pattern=major, file="x", line=2, matched_text="x"),
        ]
        assert severity_score_penalty(matches) == 15


class TestPatternsList:
    def test_patterns_not_empty(self) -> None:
        assert len(PATTERNS) >= 5

    def test_all_have_unique_ids(self) -> None:
        ids = [p.id for p in PATTERNS]
        assert len(ids) == len(set(ids))

    def test_critical_patterns_exist(self) -> None:
        critical = [p for p in PATTERNS if p.severity == "critical"]
        assert len(critical) >= 3

    def test_hardcoded_score_pattern_in_list(self) -> None:
        ids = [p.id for p in PATTERNS]
        assert "hardcoded_score" in ids
        assert "info_leak_in_retry" in ids
        assert "external_pkg_added" in ids
