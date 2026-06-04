"""Audit step 5 fix — enemy flee 로직 단위 테스트 (ep_0008 / ep_0013 / ep_0054)."""

from __future__ import annotations

from service.sim.enemy import Enemy
from service.sim.enemy_ai import compose_flee_narrative, should_enemy_flee


def _make_enemy(hp: int, max_hp: int, name: str = "오크") -> Enemy:
    return Enemy(
        name=name,
        race="오크",
        grade=8,
        hp=hp,
        max_hp=max_hp,
        attack=10,
        defense=2,
        abilities=["기본 공격"],
    )


# ── HP 기반 도주 (ep_0054) ──


def test_lone_enemy_no_flee_at_low_hp() -> None:
    """★ 단독 적은 저HP로 도주하지 않고 죽을 때까지 싸운다 (처치/XP 보장)."""
    e = _make_enemy(hp=10, max_hp=100)
    assert should_enemy_flee(e, initial_count=1, current_count=1) is False


def test_group_member_flees_at_low_hp() -> None:
    """집단(2마리 이상)에서 개별 HP < 25%면 사기 붕괴로 도주."""
    e = _make_enemy(hp=24, max_hp=100)
    assert should_enemy_flee(e, initial_count=2, current_count=2) is True


def test_no_flee_when_hp_at_25pct_group() -> None:
    e = _make_enemy(hp=25, max_hp=100)
    assert should_enemy_flee(e, initial_count=2, current_count=2) is False


def test_no_flee_when_hp_above_25pct() -> None:
    e = _make_enemy(hp=60, max_hp=100)
    assert should_enemy_flee(e, initial_count=1, current_count=1) is False


# ── 수적 열세 도주 (ep_0008 / ep_0013) ──


def test_flee_when_half_allies_dead() -> None:
    e = _make_enemy(hp=80, max_hp=100)
    # 4마리로 시작 → 2마리 이하 남음
    assert should_enemy_flee(e, initial_count=4, current_count=2) is True


def test_flee_when_majority_dead() -> None:
    e = _make_enemy(hp=80, max_hp=100)
    # 3마리로 시작 → 1마리 남음 (절반 이하)
    assert should_enemy_flee(e, initial_count=3, current_count=1) is True


def test_no_flee_single_enemy_numerical() -> None:
    """1마리 단독으로는 수적 열세 조건 미적용."""
    e = _make_enemy(hp=80, max_hp=100)
    assert should_enemy_flee(e, initial_count=1, current_count=1) is False


def test_no_flee_when_initial_count_1() -> None:
    """initial_count < 2이면 수적 열세 조건 발동 안 함."""
    e = _make_enemy(hp=80, max_hp=100)
    assert should_enemy_flee(e, initial_count=1, current_count=1) is False


def test_no_flee_when_majority_alive() -> None:
    e = _make_enemy(hp=80, max_hp=100)
    # 4마리 시작 → 3마리 생존 (절반 이상)
    assert should_enemy_flee(e, initial_count=4, current_count=3) is False


# ── 도주 연출 ──


def test_compose_flee_narrative_with_final() -> None:
    narrative = compose_flee_narrative("구울")
    assert "구울이" in narrative
    assert "도망쳤다" in narrative


def test_compose_flee_narrative_no_final() -> None:
    narrative = compose_flee_narrative("벤시")
    assert "벤시가" in narrative
    assert "도망쳤다" in narrative


def test_compose_flee_narrative_orc() -> None:
    narrative = compose_flee_narrative("오크")
    assert "오크가" in narrative
