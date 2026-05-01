"""Layer 2 정책 (자료 HARNESS_LAYER2 1).

| 항목 | Layer 2 (서비스) | 이유 |
|---|---|---|
| Threshold | 70+ | 게임 응답 약간 관대 (재미 우선) |
| Retries | 3 | 자동 재시도 (사용자 노출 X) |
| 검증 범위 | Mechanical 우선 | 실시간성 |
| 실패 시 | 재생성 → fallback | 끊김 없게 |
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Layer2Policy:
    """Layer 2 정책 (★ 자료 1).

    Layer 1 (개발 하네스)와 다른 값:
      threshold: 70 vs 80
      retries: 3 vs 1
    """

    # Verification
    threshold_score: int = 70
    max_retries: int = 3

    # Plan Verify (Plan은 시작 단계라 더 엄격)
    plan_verify_threshold: int = 80

    # Mechanical 우선 (실시간성)
    use_mechanical_first: bool = True
    fallback_to_judge_score: int = 50

    # IP Leakage
    ip_leakage_strict: bool = True
    ip_masking_required: bool = True

    # Cost
    max_cost_per_session_usd: float = 5.0
    warn_cost_threshold: float = 1.0

    # Fallback chain (로컬 → API → 사용자)
    fallback_chain: tuple[str, ...] = (
        "qwen35-9b-q3",
        "qwen36-27b-q2",
        "claude_haiku_3_5",
        "user_notification",
    )


DEFAULT_LAYER2_POLICY = Layer2Policy()
