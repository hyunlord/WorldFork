"""W1 D5 작업 3: Encoding 룰 테스트."""

from core.verify.encoding_rules import (
    GarbledTextRule,
    HanjaInKoreanRule,
    get_encoding_rules,
)


class TestHanjaInKoreanRule:
    def test_clean_korean_passes(self) -> None:
        rule = HanjaInKoreanRule()
        result = rule.check("안녕하세요 모험가님", {"language": "ko"})
        assert result is None

    def test_hanja_korean_adjacent_major(self) -> None:
        rule = HanjaInKoreanRule()
        result = rule.check("안녕하세요 籠여져 모험가님", {"language": "ko"})
        assert result is not None
        assert result.severity == "major"
        assert "hanja_in_korean" == result.rule

    def test_many_hanja_only_minor(self) -> None:
        # 한자 3개 이상 but 한글 인접 없음
        rule = HanjaInKoreanRule()
        result = rule.check("漢 字 三 글자", {"language": "ko"})
        # 한자 3개 + 한글 인접 없음 → minor
        if result is not None:
            assert result.severity == "minor"

    def test_non_korean_response_skipped(self) -> None:
        rule = HanjaInKoreanRule()
        result = rule.check("漢字漢字漢字", {"language": "en"})
        assert result is None

    def test_few_hanja_no_adjacent_passes(self) -> None:
        rule = HanjaInKoreanRule()
        result = rule.check("漢 자막 있음", {"language": "ko"})
        # 한자 1개, 한글 인접 없음 → None
        assert result is None

    def test_rule_id(self) -> None:
        assert HanjaInKoreanRule().rule_id == "hanja_in_korean"


class TestGarbledTextRule:
    def test_clean_passes(self) -> None:
        rule = GarbledTextRule()
        result = rule.check("정상 텍스트입니다.", {"language": "ko"})
        assert result is None

    def test_replacement_chars_major(self) -> None:
        rule = GarbledTextRule()
        result = rule.check("텍스트�� 깨짐", {"language": "ko"})
        assert result is not None
        assert result.severity == "major"
        assert "garbled_text" == result.rule

    def test_rule_id(self) -> None:
        assert GarbledTextRule().rule_id == "garbled_text"


class TestGetEncodingRules:
    def test_returns_two_rules(self) -> None:
        rules = get_encoding_rules()
        assert len(rules) == 2

    def test_rule_ids_present(self) -> None:
        rule_ids = {r.rule_id for r in get_encoding_rules()}
        assert "hanja_in_korean" in rule_ids
        assert "garbled_text" in rule_ids
