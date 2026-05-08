"""AI Playtester LLM client 생성 헬퍼.

본인 본질 (★ 본 commit):
- qwen35_9b_q3 9B Q3 (★ 8083포트) 진짜 호출
- LocalLLMClient 인스턴스 생성
- thinking OFF (★ LocalLLMClient default)
- player_agent.PlayerAgent에 주입
"""

from __future__ import annotations

from core.llm.client import LLMClient
from core.llm.local_client import LocalLLMClient

# ─── qwen35_9b_q3 (★ AI Playtester player 권장) ───

QWEN35_9B_Q3_BASE_URL = "http://localhost:8083"
QWEN35_9B_Q3_MODEL_KEY = "qwen35_9b_q3"


def make_player_llm_client(
    base_url: str = QWEN35_9B_Q3_BASE_URL,
    model_key: str = QWEN35_9B_Q3_MODEL_KEY,
    timeout: int = 60,
) -> LLMClient:
    """PlayerAgent용 LLM client 생성 — qwen35_9b_q3 default.

    Args:
        base_url: LLM 서버 base url (★ default 8083 = 9B Q3)
        model_key: 모델 식별자
        timeout: HTTP timeout (초)

    Returns:
        LocalLLMClient (★ thinking OFF default)
    """
    return LocalLLMClient(
        model_key=model_key,
        base_url=base_url,
        timeout=timeout,
    )


# ─── qwen36_27b_q2 (★ SimGMAgent 본격, 8082포트) ───

QWEN36_27B_Q2_BASE_URL = "http://localhost:8082"
QWEN36_27B_Q2_MODEL_KEY = "qwen36_27b_q2"


def make_gm_llm_client(
    base_url: str = QWEN36_27B_Q2_BASE_URL,
    model_key: str = QWEN36_27B_Q2_MODEL_KEY,
    timeout: int = 120,
) -> LLMClient:
    """SimGMAgent용 LLM client 생성 — qwen36_27b_q2 default.

    본 commit (★ C 본격) production caller:
    - tools/run_sim_real.py
    - tests/integration/test_sim_real_gm_player.py
    """
    return LocalLLMClient(
        model_key=model_key,
        base_url=base_url,
        timeout=timeout,
    )


# ─── B commit 본격: 4회 비교 매트릭스 helpers ───


def make_player_27b() -> LLMClient:
    """Player에 27B Q2 (★ B commit root cause 3 답)."""
    return make_player_llm_client(
        base_url=QWEN36_27B_Q2_BASE_URL,
        model_key=QWEN36_27B_Q2_MODEL_KEY,
        timeout=120,
    )


def make_gm_9b() -> LLMClient:
    """GM에 9B Q3 (★ B commit 비교 본질)."""
    return make_gm_llm_client(
        base_url=QWEN35_9B_Q3_BASE_URL,
        model_key=QWEN35_9B_Q3_MODEL_KEY,
        timeout=60,
    )
