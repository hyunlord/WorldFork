"""game_token_policy 테스트 (★ Tier 2 D6)."""

from core.llm.game_token_policy import compute_game_max_tokens


class TestGameTokenPolicy:
    def test_empty_action(self) -> None:
        assert compute_game_max_tokens("") == 200

    def test_very_short_action(self) -> None:
        assert compute_game_max_tokens("다음") == 200
        assert compute_game_max_tokens("ok") == 200

    def test_short_action_400(self) -> None:
        # "주변을 살펴봅니다" (9자)
        assert compute_game_max_tokens("주변을 살펴봅니다") == 400
        assert compute_game_max_tokens("발자국 소리를 따라갑니다") == 400

    def test_medium_action_600(self) -> None:
        action = "조심스럽게 던전 안으로 들어가서 횃불을 든다"
        # 25자 → 600
        assert compute_game_max_tokens(action) == 600

    def test_long_action_800(self) -> None:
        assert compute_game_max_tokens("x" * 100) == 800

    def test_very_long_1000(self) -> None:
        assert compute_game_max_tokens("x" * 200) == 1000

    def test_strip_whitespace(self) -> None:
        assert compute_game_max_tokens("   다음   ") == 200
