"""흥정 메커니즘 단위 테스트 — 코드 판정(가격/성공률/「」 fact) 결정적 검증."""

from service.sim.barter import (
    BarterResult,
    compute_barter,
    format_barter_fact,
)


def test_barter_success_discount() -> None:
    # 낮은 rand → 성공 + 최소 할인(20%)
    r = compute_barter(100, player_level=1, rand_func=lambda: 0.0)
    assert r.success is True
    assert r.discount_pct == 20
    assert r.final_price == 80
    assert r.base_price == 100


def test_barter_failure_keeps_price() -> None:
    # 높은 rand → 성공률(0.45) 미달 → 실패, 제시가 그대로
    r = compute_barter(100, player_level=1, rand_func=lambda: 0.99)
    assert r.success is False
    assert r.final_price == r.base_price == 100
    assert r.discount_pct == 0


def test_barter_level_raises_success() -> None:
    # 레벨 보정: rand 0.6은 lv1(0.45) 실패하나 충분히 높은 레벨이면 성공.
    low = compute_barter(100, player_level=1, rand_func=lambda: 0.6)
    high = compute_barter(100, player_level=10, rand_func=lambda: 0.6)
    assert low.success is False
    assert high.success is True  # lv10 = 0.45 + 9*0.03 = 0.72 > 0.6


def test_barter_success_cap() -> None:
    # 성공률 상한 0.85 — rand 0.9는 어떤 레벨이든 실패.
    r = compute_barter(100, player_level=99, rand_func=lambda: 0.9)
    assert r.success is False


def test_format_fact_has_system_brackets() -> None:
    # ★ 시스템 「」 + 수치 명시(저점 해소 검증).
    win = format_barter_fact(BarterResult(100, 70, success=True, discount_pct=30), "마석")
    assert "「" in win and "」" in win
    assert "100" in win and "70" in win and "30%" in win
    lose = format_barter_fact(BarterResult(100, 100, success=False, discount_pct=0), "마석")
    assert "「협상 실패" in lose and "100" in lose


def test_final_price_floor() -> None:
    # 극단 할인에도 최소 1 스톤.
    r = compute_barter(1, player_level=1, rand_func=lambda: 0.0)
    assert r.final_price >= 1
