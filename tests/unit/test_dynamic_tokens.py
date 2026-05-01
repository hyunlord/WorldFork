"""W1 D6: dynamic_token_limiter 단위 테스트."""

from core.llm.dynamic_token_limiter import compute_max_tokens


def test_empty_action() -> None:
    assert compute_max_tokens("") == 100


def test_very_short_action() -> None:
    assert compute_max_tokens("다음") == 80
    assert compute_max_tokens("ok") == 80
    assert compute_max_tokens("위") == 80


def test_short_action() -> None:
    """6-15자."""
    assert compute_max_tokens("주변 살피기") == 150  # 6자
    assert compute_max_tokens("던전 안으로 진입") == 150  # 9자


def test_medium_action() -> None:
    """16-50자."""
    assert compute_max_tokens(
        "조심스럽게 던전 안으로 들어가서 횃불을 든다"
    ) == 250


def test_long_action() -> None:
    """51-150자."""
    assert compute_max_tokens("x" * 100) == 400


def test_very_long_action() -> None:
    """150자+."""
    assert compute_max_tokens("x" * 200) == 500


def test_whitespace_only_treated_as_empty() -> None:
    # strip() 후 0자 → safety 100
    assert compute_max_tokens("   ") == 100
