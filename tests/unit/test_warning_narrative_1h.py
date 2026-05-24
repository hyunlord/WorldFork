"""audit-step168h fix — 1h 경고 narrative 본문 정합 검증 (ep_0036:278)."""

from __future__ import annotations

from service.sim.dungeon_clock import check_warning


def _get_1h_message() -> str:
    result = check_warning(1, prev_hours=166.7, new_hours=167.2)
    assert result is not None and result.kind == "1h"
    return result.message


def test_warning_1h_canon_quote() -> None:
    """ep_0036:278 정확 인용 — '1시간도 안 남은 셈이군.'"""
    msg = _get_1h_message()
    assert "1시간도 안 남은 셈이군" in msg


def test_warning_1h_single_quote_format() -> None:
    """단따옴표 내부 독백 형식."""
    msg = _get_1h_message()
    assert msg.startswith("'") and msg.endswith("'")


def test_warning_1h_not_old_format() -> None:
    """기존 부정확 표현 제거 확인."""
    msg = _get_1h_message()
    assert "그러고 보면" not in msg
    assert "얼마 안 남은" not in msg
    assert "인데……" not in msg


def test_warning_1h_kind_unchanged() -> None:
    """kind 값은 여전히 '1h'."""
    result = check_warning(1, prev_hours=166.7, new_hours=167.2)
    assert result is not None
    assert result.kind == "1h"
