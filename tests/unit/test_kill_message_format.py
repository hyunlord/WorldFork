"""Audit step 5 fix — 처치 메시지 본문 정합 테스트."""

from __future__ import annotations

import pytest

from service.sim.combat import format_bonus_message, format_kill_message


@pytest.mark.parametrize(
    "name,xp,expected",
    [
        ("오크 전사", 8, "「오크 전사를 처치했습니다. EXP +8」"),   # 사 받침 없음 → 를
        ("카샨", 9, "「카샨을 처치했습니다. EXP +9」"),             # 샨 받침 ㄴ → 을
        ("구울", 2, "「구울을 처치했습니다. EXP +2」"),              # 울 받침 ㄹ → 을
        ("벤시 퀸", 4, "「벤시 퀸을 처치했습니다. EXP +4」"),       # 퀸 받침 ㄴ → 을
        ("고블린", 1, "「고블린을 처치했습니다. EXP +1」"),          # 린 받침 ㄴ → 을
    ],
)
def test_format_kill_message(name: str, xp: int, expected: str) -> None:
    assert format_kill_message(name, xp) == expected


def test_format_kill_message_guillemets() -> None:
    msg = format_kill_message("트롤", 5)
    assert msg.startswith("「")
    assert msg.endswith("」")


def test_format_kill_message_contains_exp() -> None:
    msg = format_kill_message("스켈레톤", 1)
    assert "EXP +1" in msg
    assert "처치했습니다" in msg


def test_format_bonus_message() -> None:
    msg = format_bonus_message("수호자", 3)
    assert msg == "「수호자 처치 보너스. EXP +3」"
    assert msg.startswith("「")
    assert msg.endswith("」")
