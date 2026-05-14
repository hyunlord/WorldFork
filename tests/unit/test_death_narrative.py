"""Phase 8 (b) — 죽음 narrative 본문 톤 정합 unit 본격.

검증 본질 (★ docs/FLOOR1_COMPLETION_REVIEW.md §2-2 (b) 본격 해결):
- A4 PARTY_DEFEATED 본격 text only → 본문 톤 narrative 보강
- 740화 본문 출처:
  * 37화: "미궁 속에서 탐험가가 죽는 게 일상다반사"
  * 19화: "매월 1일이 되는 자정에는 미궁이 열린다 ... 30일"
- 톤: 무덤덤 / 일상 (★ 비극 / 극적 표현 X)

본 commit cosmetic only — 한 달 후 재진입 / 부활 mechanism 본격 후속.
"""

from __future__ import annotations

from service.game.gm_agent import _format_simulation_status


def _ctx(status: str, reason: str = "", turn: int | None = None) -> dict:
    return {
        "v2_world_state": {
            "simulation_status": status,
            "simulation_over_reason": reason,
            "simulation_over_turn": turn,
        }
    }


# ─── 1. ACTIVE 본격 empty ───


def test_active_returns_empty() -> None:
    out = _format_simulation_status(_ctx("active"))
    assert out == ""


# ─── 2. TIME_LIMIT (★ A4 regression) ───


def test_time_limit_header_present() -> None:
    """A4 본격 본격 message 본격 — regression 검증."""
    out = _format_simulation_status(
        _ctx("time_limit", reason="7일 (168시간) 만료. ...", turn=80)
    )
    assert "7일 만료" in out
    assert "마을" in out


# ─── 3. PARTY_DEFEATED narrative (★ 본 commit 본격) ───


def test_party_defeated_header() -> None:
    out = _format_simulation_status(
        _ctx(
            "party_defeated",
            reason="탐사대 전원이 미궁에서 쓰러졌다.",
            turn=50,
        )
    )
    assert "쓰러짐" in out
    assert "50" in out  # ★ turn marker


def test_party_defeated_cites_37hwa_tone() -> None:
    """37화 본문 직접 quote '일상다반사' 본격 포함."""
    out = _format_simulation_status(
        _ctx(
            "party_defeated",
            reason="탐사대 전원이 미궁에서 쓰러졌다.",
            turn=50,
        )
    )
    assert "일상다반사" in out
    assert "37화" in out  # ★ 본문 출처 명시 (★ 정직 정공법)


def test_party_defeated_mentions_dungeon_swallows() -> None:
    """본문 정합: 시체 = 미궁 연료, 흔적 사라짐 (★ 168/404화 정합)."""
    out = _format_simulation_status(
        _ctx(
            "party_defeated",
            reason="탐사대 전원이 미궁에서 쓰러졌다.",
            turn=50,
        )
    )
    assert "미궁이 삼킨다" in out or "흔적" in out


def test_party_defeated_mentions_19hwa_monthly() -> None:
    """19화 본문 정합: 매월 1일 미궁 재개 (★ 한 달 뒤)."""
    out = _format_simulation_status(
        _ctx(
            "party_defeated",
            reason="탐사대 전원이 미궁에서 쓰러졌다.",
            turn=50,
        )
    )
    assert "한 달" in out
    assert "19화" in out  # ★ 본문 출처 명시


def test_party_defeated_avoids_dramatic_words() -> None:
    """본문 톤 정합 — 비극적 / 극적 표현 X (★ 무덤덤 / 일상)."""
    out = _format_simulation_status(
        _ctx(
            "party_defeated",
            reason="탐사대 전원이 미궁에서 쓰러졌다.",
            turn=50,
        )
    )
    dramatic = ["비극", "참혹", "끔찍", "절망", "통곡", "오열"]
    for word in dramatic:
        assert word not in out, (
            f"'{word}' 본격 본문 톤 위반 (★ 37화 '일상다반사' 정합)"
        )


def test_party_defeated_directive_no_revival() -> None:
    """본문 정합: 회생 / 부활 X (★ A4 기존 정합 본격 본격)."""
    out = _format_simulation_status(
        _ctx(
            "party_defeated",
            reason="탐사대 전원이 미궁에서 쓰러졌다.",
            turn=50,
        )
    )
    assert "회생" in out or "부활" in out


def test_party_defeated_directive_no_more_actions() -> None:
    """본문 정합: 더 이상 행동 / 선택지 X (★ 종료 상태)."""
    out = _format_simulation_status(
        _ctx(
            "party_defeated",
            reason="탐사대 전원이 미궁에서 쓰러졌다.",
            turn=50,
        )
    )
    assert "행동" in out
    assert "선택지" in out


def test_party_defeated_reason_text_included() -> None:
    """reason text 본격 prompt 본격 포함 (★ check_party_defeated 본격 정합)."""
    out = _format_simulation_status(
        _ctx(
            "party_defeated",
            reason="탐사대 전원이 미궁에서 쓰러졌다.",
            turn=50,
        )
    )
    assert "탐사대 전원이 미궁에서 쓰러졌다" in out


# ─── 4. FLOOR_TRANSITION (★ regression — 본 commit 본격 변경 X) ───


def test_floor_transition_unchanged() -> None:
    """C 본격 transition message 본격 본격 변경 X (★ regression)."""
    out = _format_simulation_status(
        _ctx("transition", reason="2층 진입.", turn=30)
    )
    assert "현재 2층" in out
    assert "왕복" in out
