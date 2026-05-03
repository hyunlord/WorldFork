"""게임 GM 응답 token 정책 (★ Tier 2 D6 진짜 진척).

★ 본인 W2 D5 정공법 흐름:
  W2 D5: '...조력자 셰' 잘림 (본인 ^C)
  D2 (Tier 2): 60% 잘림 측정
  D3 (Tier 2): 88% 효과 입증 + 회수 (★ 자의적 차단)
  D4 (Tier 2): architectural 시도 + 회수 (★ 자의적 차단)
  D5 (Tier 2): prompt 명확화 (EXCLUSIONS)
  ★ D6 (Tier 2): ★ 진짜 fix (★ 새 prompt EXCLUSIONS 작동 입증 후)

★ 정신:
  dynamic_token_limiter는 chat 응답 가정 (verbose 방어, 80-500)
  game_token_policy는 게임 GM 응답 가정 (풍부 묘사, 200-1000)

★ scope:
  - GMAgent 전용 (★ service/game/gm_agent.py)
  - dynamic_token_limiter / PlaytesterRunner / tests 그대로

★ 측정 입증 (Tier 2 D3):
  잘림 60% → 7% (★ 88% 감소)
"""


def compute_game_max_tokens(user_action: str) -> int:
    """게임 GM 응답용 max_tokens 동적 결정.

    ★ Tier 2 D2 baseline: 잘림 60%
    ★ Tier 2 D3 효과 측정: 88% 감소 입증
    ★ Tier 2 D6: 진짜 적용

    이전 dynamic_token_limiter (80-500) 한계:
        - "주변을 살펴봅니다" (9자) → 150 tokens (★ 부족!)
        - 게임 GM 응답 풍부 묘사 X
        - ★ 30턴 중 18턴(60%) 잘림

    신규 정책 (200-1000):
        - 짧아도 풍부한 묘사 보장
        - verbose 방어는 system prompt + Mechanical 룰

    Args:
        user_action: 사용자 액션

    Returns:
        max_tokens (200-1000)
    """
    char_count = len(user_action.strip())

    if char_count == 0:
        return 200  # safety
    if char_count <= 5:
        # "다음", "ok", "위" 등 — 짧아도 게임 묘사 풍부
        return 200
    if char_count <= 15:
        # "주변 살피기", "검 잡기" 등 — 게임 GM 본격 응답
        return 400
    if char_count <= 50:
        # "조심스럽게 던전 안으로 들어가서 횃불을 든다"
        return 600
    if char_count <= 150:
        return 800
    # 매우 긴 액션 (RP 페르소나)
    return 1000
