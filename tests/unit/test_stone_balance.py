"""Audit C1 — stone_balance 누적 + TIP message 단위 테스트."""

from service.api.v2_freeform_router import _build_tip_message


def test_tip_message_on_change():
    msg = _build_tip_message(140, 0)
    assert msg is not None
    assert "140스톤" in msg
    assert "「TIP:" in msg
    assert "」" in msg


def test_no_tip_when_unchanged():
    assert _build_tip_message(0, 0) is None
    assert _build_tip_message(500, 500) is None


def test_tip_format_large_number():
    msg = _build_tip_message(1_403_520, 0)
    assert msg is not None
    assert "1,403,520스톤" in msg


def test_tip_decrease():
    # 구매로 잔액 감소해도 TIP 표시
    msg = _build_tip_message(300, 500)
    assert msg is not None
    assert "300스톤" in msg
