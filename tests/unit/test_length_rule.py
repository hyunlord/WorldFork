"""W1 D6: LengthAppropriatenessRule 단위 테스트 (★ verbose 대응)."""

from core.verify.length_rules import LengthAppropriatenessRule


class TestLengthAppropriatenessRule:
    def test_short_user_short_response_pass(self) -> None:
        rule = LengthAppropriatenessRule()
        result = rule.check("응답입니다.", {"user_input": "다음"})
        assert result is None

    def test_short_user_long_response_major(self) -> None:
        """짧은 user 액션 + 매우 긴 응답 → major (1.5배 초과)."""
        rule = LengthAppropriatenessRule()
        # user 2자 → allowed 200자, 401자 응답 → 1.5배 초과 → major
        long_response = "응답" * 200  # 400자 (실제로 200 한국어 char 2 = 400)
        # 길게 만들어서 1.5배(=300자) 초과
        long_response = "응답" * 200  # 400자
        result = rule.check(long_response, {"user_input": "ok"})
        assert result is not None
        assert result.severity == "major"
        assert result.rule == "length_appropriateness"

    def test_short_user_slightly_long_response_minor(self) -> None:
        """짧은 user + 1.0~1.5배 초과 응답 → minor."""
        rule = LengthAppropriatenessRule()
        # user "ok" → allowed 200자. 250자 응답 → 1.25배 → minor
        response = "x" * 250
        result = rule.check(response, {"user_input": "ok"})
        assert result is not None
        assert result.severity == "minor"

    def test_long_user_long_response_pass(self) -> None:
        """긴 user 액션 + 비례 긴 응답 → pass."""
        rule = LengthAppropriatenessRule()
        user_long = "조심스럽게 던전 안으로 들어가서 횃불을 든다"  # 23자
        # user 15자+ → allowed 800자
        response = "응답" * 200  # 400자
        result = rule.check(response, {"user_input": user_long})
        assert result is None

    def test_no_user_input_skipped(self) -> None:
        """user_input 없으면 skip (legacy 호환)."""
        rule = LengthAppropriatenessRule()
        result = rule.check("응답" * 500, {})
        assert result is None

    def test_empty_user_input_skipped(self) -> None:
        rule = LengthAppropriatenessRule()
        result = rule.check("응답" * 500, {"user_input": ""})
        assert result is None

    def test_medium_user_threshold(self) -> None:
        """user 50자 이하 → allowed 800자."""
        rule = LengthAppropriatenessRule()
        user_input = "x" * 30  # 30자, 15자 초과 50자 이하
        # 800자 응답 — pass
        response = "x" * 800
        assert rule.check(response, {"user_input": user_input}) is None
        # 1300자 응답 — 1.5배 초과 → major
        response_long = "x" * 1300
        result = rule.check(response_long, {"user_input": user_input})
        assert result is not None
        assert result.severity == "major"

    def test_rule_id(self) -> None:
        rule = LengthAppropriatenessRule()
        assert rule.rule_id == "length_appropriateness"
