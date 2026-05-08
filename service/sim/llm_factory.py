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
