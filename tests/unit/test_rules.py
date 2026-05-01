"""Day 3: Mechanical 룰 단위 테스트."""

from core.verify.game_rules import WorldConsistencyRule
from core.verify.korean_rules import (
    IPLeakageRule,
    SpeechStyleConsistencyRule,
    detect_speech_style,
)
from core.verify.mechanical import MechanicalChecker, build_check_context
from core.verify.rule import CheckFailure, MechanicalResult
from core.verify.standard_rules import (
    AIBreakoutRule,
    JsonValidityRule,
    KoreanRatioRule,
    LengthRule,
)


class TestJsonValidityRule:
    rule = JsonValidityRule()

    def test_no_check_when_not_required(self) -> None:
        assert self.rule.check("not json", {}) is None

    def test_valid_json_passes(self) -> None:
        ctx = {"requires_json": True}
        assert self.rule.check('{"k": 1}', ctx) is None

    def test_invalid_json_fails(self) -> None:
        ctx = {"requires_json": True}
        result = self.rule.check("not json", ctx)
        assert result is not None
        assert result.severity == "critical"
        assert result.rule == "json_validity"


class TestKoreanRatioRule:
    rule = KoreanRatioRule()

    def test_no_check_when_not_korean(self) -> None:
        assert self.rule.check("Hello world", {"language": "en"}) is None

    def test_pure_korean_passes(self) -> None:
        ctx = {"language": "ko"}
        assert self.rule.check("안녕하세요. 오늘은 좋은 날입니다.", ctx) is None

    def test_pure_english_fails(self) -> None:
        ctx = {"language": "ko"}
        result = self.rule.check("Hello world this is english text here", ctx)
        assert result is not None
        assert "korean_ratio" in result.rule

    def test_mixed_at_threshold_passes(self) -> None:
        ctx = {"language": "ko"}
        # 한국어 7자 / 전체 12자 = 58% (50% threshold 통과)
        assert self.rule.check("안녕하세요반갑hello", ctx) is None


class TestLengthRule:
    rule = LengthRule()

    def test_normal_passes(self) -> None:
        ctx = {"max_length": 1000}
        assert self.rule.check("short response", ctx) is None

    def test_too_long_fails(self) -> None:
        ctx = {"max_length": 100}
        long_text = "a" * 200  # 1.5 * 100 = 150 초과
        result = self.rule.check(long_text, ctx)
        assert result is not None
        assert result.severity == "minor"

    def test_too_short_fails(self) -> None:
        result = self.rule.check("hi", {})
        assert result is not None
        assert result.severity == "major"


class TestAIBreakoutRule:
    rule = AIBreakoutRule()

    def test_normal_passes(self) -> None:
        ctx = {"character_response": True}
        assert self.rule.check("셰인이 인사한다.", ctx) is None

    def test_ai_mention_fails(self) -> None:
        ctx = {"character_response": True}
        result = self.rule.check("저는 AI 어시스턴트입니다.", ctx)
        assert result is not None
        assert result.rule == "ai_breakout"

    def test_chatgpt_mention_fails(self) -> None:
        ctx = {"character_response": True}
        result = self.rule.check("저는 ChatGPT가 아니라 셰인입니다.", ctx)
        assert result is not None
        assert "ChatGPT" in str(result.detail) or "chatgpt" in str(result.detail).lower()


class TestWorldConsistencyRule:
    rule = WorldConsistencyRule()

    def test_no_check_when_no_forbidden(self) -> None:
        assert self.rule.check("어떤 응답이든", {}) is None

    def test_normal_passes(self) -> None:
        ctx = {"world_forbidden": ["스마트폰", "총", "자동차"]}
        assert self.rule.check("셰인이 검을 들었다.", ctx) is None

    def test_forbidden_element_fails(self) -> None:
        ctx = {"world_forbidden": ["스마트폰", "총"]}
        result = self.rule.check("셰인이 스마트폰을 꺼냈다.", ctx)
        assert result is not None
        assert "스마트폰" in str(result.detail)


class TestDetectSpeechStyle:
    def test_formal(self) -> None:
        assert detect_speech_style("안녕하세요. 오셨군요.") == "formal"
        assert detect_speech_style("그렇습니다.") == "formal"  # "니다." lookbehind로 오탐 방지

    def test_informal(self) -> None:
        assert detect_speech_style("야 너 뭐해.") == "informal"
        assert detect_speech_style("간다구나!") == "informal"  # "(?<!니)다" + "구나!" 모두 informal

    def test_mixed(self) -> None:
        assert detect_speech_style("알겠습니다. 빨리 가구나!") == "mixed"  # 격식 + 반말 공존

    def test_unknown(self) -> None:
        assert detect_speech_style("Hello") == "unknown"


class TestSpeechStyleConsistencyRule:
    rule = SpeechStyleConsistencyRule()

    def test_no_check_when_not_korean(self) -> None:
        assert self.rule.check("anything", {"language": "en"}) is None

    def test_no_check_when_no_styles(self) -> None:
        assert self.rule.check("응답", {"language": "ko"}) is None

    def test_no_quoted_speech_passes(self) -> None:
        ctx = {
            "language": "ko",
            "character_speech_styles": {"셰인": "formal"},
        }
        assert self.rule.check("셰인이 인사를 한다.", ctx) is None


class TestIPLeakageRule:
    rule = IPLeakageRule()

    def test_no_check_when_no_forbidden(self) -> None:
        assert self.rule.check("anything", {}) is None

    def test_normal_passes(self) -> None:
        ctx = {"ip_forbidden_terms": ["비요른", "라프도니아"]}
        assert self.rule.check("투르윈이 라스카니아 길드로 갔다.", ctx) is None

    def test_ip_leak_fails(self) -> None:
        ctx = {"ip_forbidden_terms": ["비요른", "라프도니아"]}
        result = self.rule.check("비요른이 라프도니아에 도착했다.", ctx)
        assert result is not None
        assert result.severity == "critical"
        assert "비요른" in str(result.detail)

    def test_case_insensitive(self) -> None:
        ctx = {"ip_forbidden_terms": ["ChatGPT"]}
        result = self.rule.check("나는 chatgpt다.", ctx)
        assert result is not None


class TestMechanicalChecker:
    def test_default_rules_count(self) -> None:
        checker = MechanicalChecker()
        # 4 standard + 1 game + 2 korean + 2 encoding = 9
        assert len(checker.rules) == 9

    def test_all_pass(self) -> None:
        checker = MechanicalChecker()
        ctx = {
            "language": "ko",
            "character_response": True,
        }
        result = checker.check("셰인이 인사를 한다. 오셨군요.", ctx)
        assert result.passed
        assert result.score == 100.0

    def test_critical_failure(self) -> None:
        checker = MechanicalChecker()
        ctx = {
            "language": "ko",
            "character_response": True,
            "ip_forbidden_terms": ["비요른"],
        }
        result = checker.check("비요른이 등장한다.", ctx)
        assert not result.passed
        assert result.score == 0.0
        assert result.critical_count() == 1

    def test_summary_line(self) -> None:
        checker = MechanicalChecker()
        result = checker.check("정상 응답입니다.", {"language": "ko"})
        line = result.summary_line()
        assert "Mechanical:" in line

    def test_passed_rules_set(self) -> None:
        checker = MechanicalChecker()
        result = checker.check("좋은 응답입니다.", {"language": "ko"})
        assert result.passed_rules() == len(checker.rules)


class TestMechanicalResult:
    def test_to_dict(self) -> None:
        f = CheckFailure(rule="test", severity="major", detail="detail")
        r = MechanicalResult(passed=False, score=70.0, failures=[f])
        d = r.to_dict()
        assert d["passed"] is False
        assert d["score"] == 70.0
        assert len(d["failures"]) == 1
        assert d["failures"][0]["rule"] == "test"

    def test_count_methods(self) -> None:
        failures = [
            CheckFailure(rule="a", severity="critical", detail="x"),
            CheckFailure(rule="b", severity="major", detail="x"),
            CheckFailure(rule="c", severity="minor", detail="x"),
        ]
        r = MechanicalResult(passed=False, score=0.0, failures=failures)
        assert r.critical_count() == 1
        assert r.major_count() == 1
        assert r.minor_count() == 1


class TestBuildCheckContext:
    def test_extracts_ip_forbidden(self) -> None:
        scenario = {
            "mechanical_rules": [
                {"rule": "ip_leakage", "forbidden_terms": ["비요른", "라프도니아"]},
            ],
            "characters": [],
        }
        ctx = build_check_context(scenario)
        assert "비요른" in ctx["ip_forbidden_terms"]
        assert "라프도니아" in ctx["ip_forbidden_terms"]

    def test_extracts_world_forbidden(self) -> None:
        scenario = {
            "mechanical_rules": [
                {"rule": "world_consistency", "forbidden_elements": ["총", "자동차"]},
            ],
            "characters": [],
        }
        ctx = build_check_context(scenario)
        assert "총" in ctx["world_forbidden"]

    def test_real_scenario_loads(self) -> None:
        from service.game.loop import load_scenario

        scenario = load_scenario("novice_dungeon_run")
        ctx = build_check_context(scenario)

        assert "비요른" in ctx["ip_forbidden_terms"]
        assert "라프도니아" in ctx["ip_forbidden_terms"]
        assert len(ctx["world_forbidden"]) > 0
        assert "총" in ctx["world_forbidden"] or "스마트폰" in ctx["world_forbidden"]
        assert "셰인" in ctx["character_speech_styles"]
        assert ctx["character_speech_styles"]["셰인"] == "formal"
