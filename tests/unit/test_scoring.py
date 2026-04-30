"""Day 5: Scoring 단위 테스트."""

from core.eval.runner import EvalAttempt
from core.eval.scoring import score_results


def _make_attempt(
    item_id: str,
    category: str = "test",
    mech_passed: bool = True,
    mech_score: float = 100.0,
    judge_score: float | None = None,
    final_passed: bool = True,
) -> EvalAttempt:
    return EvalAttempt(
        item_id=item_id,
        category=category,
        response_text="test",
        mechanical_passed=mech_passed,
        mechanical_score=mech_score,
        judge_score=judge_score,
        judge_verdict=(
            "pass" if judge_score and judge_score >= 85 else None
        ) if judge_score else None,
        final_passed=final_passed,
    )


class TestScoreResults:
    def test_empty(self) -> None:
        s = score_results([])
        assert s.total == 0
        assert s.pass_count == 0
        assert s.total_count == 0

    def test_all_pass_no_judge(self) -> None:
        attempts = [_make_attempt(f"a{i}") for i in range(5)]
        s = score_results(attempts)
        assert s.pass_count == 5
        assert s.mechanical_avg == 100.0
        assert s.judge_avg is None
        assert s.total == 100.0   # judge 없으면 mechanical 100%

    def test_with_judge(self) -> None:
        attempts = [
            _make_attempt(f"a{i}", mech_score=100.0, judge_score=80.0)
            for i in range(3)
        ]
        s = score_results(attempts)
        assert s.mechanical_avg == 100.0
        assert s.judge_avg == 80.0
        assert s.total == 90.0   # 50:50 가중

    def test_by_category(self) -> None:
        attempts = [
            _make_attempt("a1", category="cat1", mech_score=100.0),
            _make_attempt("a2", category="cat1", mech_score=80.0),
            _make_attempt("a3", category="cat2", mech_score=60.0, final_passed=False),
        ]
        s = score_results(attempts)
        assert s.by_category["cat1"]["count"] == 2.0
        assert s.by_category["cat1"]["mechanical_avg"] == 90.0
        assert s.by_category["cat2"]["pass_rate"] == 0.0

    def test_partial_judge(self) -> None:
        attempts = [
            _make_attempt("a1", mech_score=80.0, judge_score=90.0),
            _make_attempt("a2", mech_score=60.0),  # no judge
        ]
        s = score_results(attempts)
        assert s.judge_avg == 90.0   # only 1 judge score
        assert s.mechanical_avg == 70.0
