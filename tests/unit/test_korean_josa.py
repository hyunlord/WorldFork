"""Audit step 5 fix — service/util/korean.py 조사 헬퍼 단위 테스트."""

from __future__ import annotations

import pytest

from service.util.korean import eul_reul, eun_neun, has_final_consonant, i_ga


@pytest.mark.parametrize(
    "name,expected",
    [
        ("오크", False),    # 크 — 받침 없음
        ("구울", True),     # 울 — 받침 ㄹ
        ("스켈레톤", True), # 톤 — 받침 ㄴ
        ("고블린", True),   # 린 — 받침 ㄴ
        ("카샨", True),     # 샨 — 받침 ㄴ
        ("바포메트", False), # 트 — 받침 없음
        ("트롤", True),     # 받침 ㄹ
        ("벤시", False),    # 받침 없음
    ],
)
def test_has_final_consonant(name: str, expected: bool) -> None:
    assert has_final_consonant(name) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("오크", "를"),   # 받침 없음 → 를 (크는 받침 없음)
        ("구울", "을"),   # 받침 ㄹ → 을
        ("카샨", "을"),   # 받침 ㄴ → 을
        ("스켈레톤", "을"),  # 받침 ㄴ → 을
        ("고블린", "을"),  # 린 받침 ㄴ → 을
        ("바포메트", "를"),  # 트 받침 없음 → 를
        ("트롤", "을"),   # 받침 ㄹ → 을
        ("벤시", "를"),   # 받침 없음 → 를
    ],
)
def test_eul_reul(name: str, expected: str) -> None:
    assert eul_reul(name) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("구울", "이"),   # 받침 ㄹ → 이
        ("벤시", "가"),   # 받침 없음 → 가
        ("카샨", "이"),   # 받침 ㄴ → 이
        ("오크", "가"),   # 크 받침 없음 → 가 (오크의 크 — 종성 없음)
    ],
)
def test_i_ga(name: str, expected: str) -> None:
    assert i_ga(name) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("구울", "은"),   # 받침 ㄹ → 은
        ("벤시", "는"),   # 받침 없음 → 는
    ],
)
def test_eun_neun(name: str, expected: str) -> None:
    assert eun_neun(name) == expected


def test_empty_string_returns_false() -> None:
    assert has_final_consonant("") is False


def test_eul_reul_empty() -> None:
    # 빈 문자열 — 받침 없음 처리
    assert eul_reul("") == "를"
