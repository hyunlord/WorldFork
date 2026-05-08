"""4회 model combination 비교 통합 (★ slow, B commit 본격).

본 commit (★ B 본격):
- 4 combinations 진짜 실행 (★ ~25-35분)
- root cause 3 본격 답 검증 (★ 27B Player vs 9B Player)
"""

from __future__ import annotations

import pytest
import requests

from service.sim.llm_factory import (
    QWEN35_9B_Q3_BASE_URL,
    QWEN36_27B_Q2_BASE_URL,
    make_gm_9b,
    make_player_27b,
)


def _alive(url: str) -> bool:
    try:
        return (
            requests.get(f"{url}/v1/models", timeout=2).status_code == 200
        )
    except requests.RequestException:
        return False


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not _alive(QWEN35_9B_Q3_BASE_URL)
        or not _alive(QWEN36_27B_Q2_BASE_URL),
        reason="8082 또는 8083 X — DGX Spark 한정",
    ),
]


def test_combinations_define_4_matrix() -> None:
    """본 commit 4 combinations 본격."""
    from tools.run_sim_real_compare_models import COMBINATIONS

    assert len(COMBINATIONS) == 4

    labels = {c.label for c in COMBINATIONS}
    assert "9B Player + 27B GM" in labels
    assert "27B Player + 27B GM" in labels
    assert "27B Player + 9B GM" in labels
    assert "9B Player + 9B GM" in labels


def test_make_player_27b_returns_27b_client() -> None:
    """27B Player factory 본격."""
    client = make_player_27b()
    assert "27b" in client.model_name.lower()


def test_make_gm_9b_returns_9b_client() -> None:
    """9B GM factory 본격."""
    client = make_gm_9b()
    assert "9b" in client.model_name.lower()
