"""User action 길이별 max_tokens 동적 결정 (★ W1 D6 verbose 근본 대응).

원칙:
    유저가 짧게 → 응답 짧게
    유저가 길게 → 응답 길게

W1 D5 Round 3 측정에서 verbose 41% 발견. 원인:
    - max_tokens 고정 (300+) → 짧은 액션에도 장황한 응답
    - system prompt만으로 길이 제어 부족

해결:
    - 동적 max_tokens (80-500) — 토큰 예산 자체를 자른다
    - LengthAppropriatenessRule (Mechanical) — 사후 검증
    - system prompt 갱신 — '짧으면 짧게'
"""


def compute_max_tokens(user_action: str) -> int:
    """user_action 길이별 max_tokens 동적 결정.

    Args:
        user_action: 사용자 액션 (예: "다음", "주변 살피기", "...길게...")

    Returns:
        max_tokens (80-500)
    """
    char_count = len(user_action.strip())

    if char_count == 0:
        return 100  # safety
    if char_count <= 5:
        # "다음", "ok", "위" 등
        return 80
    if char_count <= 15:
        # "주변 살피기", "검 잡기" 등
        return 150
    if char_count <= 50:
        # "조심스럽게 던전 안으로 들어가서 횃불을 든다"
        return 250
    if char_count <= 150:
        return 400
    # 매우 긴 액션 (RP 페르소나)
    return 500
