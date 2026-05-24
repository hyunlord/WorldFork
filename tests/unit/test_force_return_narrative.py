"""audit-step168h fix — 강제 귀환 narrative 본문 정합 검증 (ep_0016 + ep_0036)."""

from __future__ import annotations

from service.api.v2_freeform_router import _force_return_narrative  # noqa: PLC2701


def test_force_return_includes_ep_0016_light_quote() -> None:
    """ep_0016:1 빛 연출 인용 포함."""
    narrative = _force_return_narrative()
    assert "빛이 눈앞을 뒤덮고" in narrative
    assert "그보다 옅은 빛이 얹어지며 시야가 돌아온다" in narrative


def test_force_return_includes_ep_0016_gaze_quote() -> None:
    """ep_0016 '멍하니 하늘을 올려다보았다' 직접 인용 포함."""
    narrative = _force_return_narrative()
    assert "멍하니 하늘을 올려다보았다" in narrative


def test_force_return_includes_location() -> None:
    """라프도니아 차원광장 위치 명시."""
    narrative = _force_return_narrative()
    assert "라프도니아 차원광장" in narrative


def test_force_return_includes_ep_0036_system_messages() -> None:
    """ep_0036:300-302 시스템 메시지 포함."""
    narrative = _force_return_narrative()
    assert "「미궁이 폐쇄되었습니다.」" in narrative
    assert "「캐릭터가 라프도니아로 이동합니다.」" in narrative


def test_force_return_first_person() -> None:
    """1인칭 어조 — '비요른은' 잔존 없음."""
    narrative = _force_return_narrative()
    assert "나는" in narrative
    assert "비요른은" not in narrative


def test_force_return_1min_warning_bundled() -> None:
    """1분 경고 포함 (safeguard)."""
    narrative = _force_return_narrative()
    assert "「층계 폐쇄까지 1분 남았습니다.」" in narrative
