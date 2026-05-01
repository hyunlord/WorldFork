"""Tier 1 W1 D4: BatchRunner 단위 테스트 (Mock 기반)."""

from typing import Any

from core.llm.client import LLMClient, LLMResponse, Prompt
from tools.ai_playtester.batch import BatchRunner, BatchRunResult
from tools.ai_playtester.runner import PlaytesterFinding, PlaytesterSessionResult


class MockGameLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "qwen35-9b-q3"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text="게임 시작 응답",
            model="qwen35-9b-q3",
            cost_usd=0.0,
            latency_ms=500,
            input_tokens=20,
            output_tokens=50,
        )


def _make_session(
    persona_id: str,
    completed: bool = False,
    fun_rating: int = 2,
    n_turns: int = 5,
    findings: list[PlaytesterFinding] | None = None,
) -> PlaytesterSessionResult:
    return PlaytesterSessionResult(
        persona_id=persona_id,
        work_name="novice_dungeon_run",
        completed=completed,
        n_turns_played=n_turns,
        elapsed_seconds=30.0,
        fun_rating=fun_rating,
        would_replay=False,
        abandoned=not completed,
        abandon_reason=None,
        abandon_turn=None,
        findings=findings or [],
    )


class TestBatchRunnerInit:
    def test_game_client_stored(self) -> None:
        runner = BatchRunner(game_client=MockGameLLM(), sleep_between=0.01)
        assert runner.game_client.model_name == "qwen35-9b-q3"

    def test_sleep_between_stored(self) -> None:
        runner = BatchRunner(game_client=MockGameLLM(), sleep_between=0.5)
        assert runner.sleep_between == 0.5


class TestBatchAggregateFindings:
    def test_empty_result(self) -> None:
        result = BatchRunResult(timestamp="t", work_name="w")
        agg = BatchRunner.aggregate_findings(result)
        assert agg["total_sessions"] == 0
        assert agg["total_findings"] == 0
        assert agg["avg_fun"] == 0.0

    def test_single_session_no_findings(self) -> None:
        result = BatchRunResult(
            timestamp="t",
            work_name="w",
            sessions=[_make_session("roleplayer", completed=True, fun_rating=4, n_turns=30)],
        )
        agg = BatchRunner.aggregate_findings(result)
        assert agg["total_sessions"] == 1
        assert agg["total_findings"] == 0
        assert agg["avg_fun"] == 4.0

    def test_findings_counted_by_severity(self) -> None:
        findings = [
            PlaytesterFinding(severity="major", category="verbose", turn_n=3, description="x"),
            PlaytesterFinding(severity="major", category="verbose", turn_n=5, description="y"),
            PlaytesterFinding(severity="minor", category="ux", turn_n=7, description="z"),
        ]
        result = BatchRunResult(
            timestamp="t",
            work_name="w",
            sessions=[_make_session("casual_korean_player", findings=findings)],
        )
        agg = BatchRunner.aggregate_findings(result)
        assert agg["total_findings"] == 3
        assert agg["by_severity"]["major"] == 2
        assert agg["by_severity"]["minor"] == 1

    def test_findings_counted_by_category(self) -> None:
        findings = [
            PlaytesterFinding(severity="major", category="verbose", turn_n=1, description="a"),
            PlaytesterFinding(severity="major", category="verbose", turn_n=2, description="b"),
            PlaytesterFinding(severity="minor", category="ux", turn_n=3, description="c"),
        ]
        result = BatchRunResult(
            timestamp="t",
            work_name="w",
            sessions=[_make_session("speed_runner", findings=findings)],
        )
        agg = BatchRunner.aggregate_findings(result)
        assert agg["by_category"]["verbose"] == 2
        assert agg["by_category"]["ux"] == 1

    def test_by_persona_populated(self) -> None:
        result = BatchRunResult(
            timestamp="t",
            work_name="w",
            sessions=[
                _make_session("casual_korean_player", fun_rating=2, n_turns=14),
                _make_session("roleplayer", completed=True, fun_rating=4, n_turns=30),
            ],
        )
        agg = BatchRunner.aggregate_findings(result)
        assert "casual_korean_player" in agg["by_persona"]
        assert "roleplayer" in agg["by_persona"]
        assert agg["by_persona"]["roleplayer"]["completed"] is True
        assert agg["by_persona"]["roleplayer"]["fun"] == 4

    def test_avg_fun_calculated(self) -> None:
        result = BatchRunResult(
            timestamp="t",
            work_name="w",
            sessions=[
                _make_session("p1", fun_rating=2),
                _make_session("p2", fun_rating=4),
            ],
        )
        agg = BatchRunner.aggregate_findings(result)
        assert agg["avg_fun"] == 3.0

    def test_skipped_counted(self) -> None:
        result = BatchRunResult(
            timestamp="t",
            work_name="w",
            sessions=[_make_session("p1")],
            skipped=[("confused_beginner", "CLI not found"), ("troll", "refused")],
        )
        agg = BatchRunner.aggregate_findings(result)
        assert agg["skipped"] == 2

    def test_multi_session_all_findings_aggregated(self) -> None:
        f1 = [PlaytesterFinding(severity="major", category="verbose", turn_n=1, description="a")]
        f2 = [
            PlaytesterFinding(severity="minor", category="ux", turn_n=2, description="b"),
            PlaytesterFinding(severity="critical", category="broken_ux", turn_n=3, description="c"),
        ]
        result = BatchRunResult(
            timestamp="t",
            work_name="w",
            sessions=[
                _make_session("p1", findings=f1),
                _make_session("p2", findings=f2),
            ],
        )
        agg = BatchRunner.aggregate_findings(result)
        assert agg["total_findings"] == 3
        assert agg["by_severity"]["major"] == 1
        assert agg["by_severity"]["minor"] == 1
        assert agg["by_severity"]["critical"] == 1
