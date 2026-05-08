"""LLM factory 단위 테스트 (★ AI Playtester LLM 호출)."""

from __future__ import annotations

from core.llm.local_client import LocalLLMClient
from service.sim.llm_factory import (
    QWEN35_9B_Q3_BASE_URL,
    QWEN35_9B_Q3_MODEL_KEY,
    make_player_llm_client,
)


def test_make_player_llm_client_default() -> None:
    """qwen35_9b_q3 default."""
    client = make_player_llm_client()
    assert isinstance(client, LocalLLMClient)
    assert client.model_name == QWEN35_9B_Q3_MODEL_KEY


def test_make_player_llm_client_custom_url() -> None:
    client = make_player_llm_client(
        base_url="http://custom:9000",
        model_key="custom_model",
    )
    assert client.model_name == "custom_model"


def test_default_constants() -> None:
    """default url/key 본격 검증."""
    assert QWEN35_9B_Q3_BASE_URL == "http://localhost:8083"
    assert QWEN35_9B_Q3_MODEL_KEY == "qwen35_9b_q3"
