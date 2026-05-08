"""Comparator v2 본격 검증 (★ B commit model combination 비교)."""

from __future__ import annotations

import pytest

from service.sim.comparator import (
    ModelCombination,
    ModelComparisonResult,
    compare_model_combinations,
)


def _result(
    label: str,
    diversity: int,
    runtime: float = 400.0,
    top: tuple[tuple[str, int, float], ...] = (("explore", 30, 60.0),),
) -> ModelComparisonResult:
    return ModelComparisonResult(
        combo=ModelCombination(
            player_model="X", gm_model="Y", label=label
        ),
        diversity_score=diversity,
        survived_to_end=True,
        floor_exit_attempted=False,
        light_management_used=True,
        completed_turns=50,
        total_turns=50,
        total_player_cost_usd=0.0,
        total_player_latency_s=130.0,
        total_gm_cost_usd=0.0,
        total_gm_latency_s=250.0,
        total_runtime_s=runtime,
        top_actions=top,
    )


def test_model_combination_display_name() -> None:
    combo = ModelCombination(
        player_model="qwen35_9b_q3",
        gm_model="qwen36_27b_q2",
        label="9B+27B",
    )
    name = combo.display_name()
    assert "qwen35_9b_q3" in name
    assert "qwen36_27b_q2" in name


def test_model_combination_frozen() -> None:
    combo = ModelCombination(
        player_model="9B", gm_model="27B", label="A"
    )
    with pytest.raises((AttributeError, Exception)):
        combo.label = "X"  # type: ignore[misc]


def test_compare_model_combinations_empty() -> None:
    text = compare_model_combinations([])
    assert "비교 결과 X" in text


def test_compare_model_combinations_table() -> None:
    """비교 매트릭스 본격 출력."""
    results = [
        _result(
            "9B+27B",
            diversity=4,
            runtime=400.0,
            top=(
                ("activate_light", 24, 48.0),
                ("absorb_essence", 22, 44.0),
            ),
        ),
        _result(
            "27B+27B",
            diversity=8,
            runtime=700.0,
            top=(
                ("absorb_essence", 12, 24.0),
                ("attack", 10, 20.0),
            ),
        ),
    ]

    text = compare_model_combinations(results)
    assert "9B+27B" in text
    assert "27B+27B" in text
    assert "최고 diversity" in text
    # 8/13이 더 높음 → 27B+27B가 best로 선정
    assert "27B+27B" in text.split("최고 diversity")[1]
    assert "최저 runtime" in text


def test_build_model_comparison_result_from_analysis() -> None:
    """SimAnalysis → ModelComparisonResult 변환."""
    from unittest.mock import MagicMock

    from service.sim.comparator import build_model_comparison_result

    combo = ModelCombination(
        player_model="9B", gm_model="27B", label="X"
    )

    analysis = MagicMock()
    analysis.diversity_score = 5
    analysis.survived_to_end = True
    analysis.floor_exit_attempted = False
    analysis.light_management_used = True
    analysis.completed_turns = 50
    analysis.total_turns = 50
    analysis.total_player_cost_usd = 0.0
    analysis.total_latency_seconds = 130.0

    freq1 = MagicMock()
    freq1.action_type.value = "explore"
    freq1.count = 30
    freq1.percentage = 60.0
    freq2 = MagicMock()
    freq2.action_type.value = "move"
    freq2.count = 10
    freq2.percentage = 20.0
    analysis.action_frequencies = [freq1, freq2]

    result = build_model_comparison_result(
        combo, analysis, runtime_s=400.0, gm_cost_usd=0.0, gm_latency_s=250.0
    )

    assert result.combo == combo
    assert result.diversity_score == 5
    assert result.total_runtime_s == 400.0
    assert len(result.top_actions) == 2
    assert result.top_actions[0] == ("explore", 30, 60.0)
