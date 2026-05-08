"""SimRunner 단위 테스트 (★ 1차 commit, schema만)."""

from __future__ import annotations

from service.sim.sim_runner import SimRunner
from service.sim.types import SimConfig, SimResult


def test_sim_runner_init_default() -> None:
    config = SimConfig()
    runner = SimRunner(config=config)
    assert runner.config.max_turns == 50
    assert runner.player_agent is not None  # mock 자동


def test_sim_runner_run_returns_result() -> None:
    """run() schema 반환 (★ 1차 commit, 진짜 시뮬 X)."""
    config = SimConfig(max_turns=5)
    runner = SimRunner(config=config)

    result = runner.run()

    assert isinstance(result, SimResult)
    assert result.total_turns == 5
    assert result.completed_turns == 0
    assert "not_yet_implemented_1차" in result.end_reason


def test_sim_runner_initialize_party_empty() -> None:
    """initialize_party — 1차 commit은 빈 dict (★ 2차 commit이 본격)."""
    config = SimConfig()
    runner = SimRunner(config=config)

    party = runner.initialize_party()
    assert party == {}


def test_sim_runner_config_summary_in_result() -> None:
    """config 진짜 result에 반영."""
    config = SimConfig(
        max_turns=10,
        player_llm_model="9b-test",
        gm_llm_model="27b-test",
    )
    runner = SimRunner(config=config)

    result = runner.run()
    assert "max_turns=10" in result.config_summary
    assert "9b-test" in result.config_summary
    assert "27b-test" in result.config_summary
