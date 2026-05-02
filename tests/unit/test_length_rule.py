"""W1 D6 + Tier 1.5 D4: LengthAppropriatenessRule + TruncationDetectionRule 테스트."""

from core.verify.length_rules import LengthAppropriatenessRule, TruncationDetectionRule


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


class TestTruncationDetectionRule:
    """★ Tier 1.5 D4: W2 D5 본인 짚음 정공법."""

    def test_truncated_korean_fails(self) -> None:
        """★ W2 D5 실제 잘린 응답 → 실패 (minor — 검출은 하되 gate 차단 X)."""
        rule = TruncationDetectionRule()
        result = rule.check("당신의 뒤에는 조력자 셰", {"language": "ko"})
        assert result is not None
        assert result.rule == "korean_truncation"
        assert result.severity == "minor"

    def test_sentence_end_passes(self) -> None:
        """마침표로 끝나는 응답 → 통과."""
        rule = TruncationDetectionRule()
        result = rule.check("던전에 들어왔습니다.", {"language": "ko"})
        assert result is None

    def test_korean_ending_passes(self) -> None:
        """한국어 종결 어미로 끝나는 응답 → 통과."""
        rule = TruncationDetectionRule()
        result = rule.check("무엇을 하시겠습니까", {"language": "ko"})
        assert result is None

    def test_non_korean_language_skipped(self) -> None:
        """language != 'ko' → skip."""
        rule = TruncationDetectionRule()
        result = rule.check("what do you want to do", {"language": "en"})
        assert result is None

    def test_no_language_skipped(self) -> None:
        """language 없음 → skip."""
        rule = TruncationDetectionRule()
        result = rule.check("what do you want", {})
        assert result is None

    def test_empty_response_fails(self) -> None:
        rule = TruncationDetectionRule()
        result = rule.check("", {"language": "ko"})
        assert result is not None
        assert "empty" in result.detail
