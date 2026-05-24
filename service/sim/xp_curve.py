"""XP curve + 레벨업 + 영혼력 계산 (본문 정합).

ep_0022: 비요른 시작 레벨 1 (포탈 EXP +2 로 L2 달성).
ep_0022: 동일 몬스터 최초 1회만 XP.
ep_0022: 1레벨 = 정수 슬롯 1개.
ep_0035: 5등급 캠보르미어 EXP +5 (base = 10 - grade 공식 정합).
ep_0035: 수호자 처치 EXP +3 / 상위 변이종 EXP +1.
ep_0035: 레벨업 시 HP 변경 없음 — 영혼력(이능) + 슬롯만 증가.
wiki 008: L≤5 영혼력 +10/레벨, L>5 +30/레벨. cap=11.
wiki 008: 포탈 EXP +2 ≈ 8등급 마물 1개체 → 8등급 base = 2.
"""

from __future__ import annotations

# ── 시작 상수 (본문 정합) ─────────────────────────────────────────────────────
INITIAL_LEVEL: int = 1        # ep_0022: 비요른 L1 시작
INITIAL_MAX_ESSENCES: int = 1  # ep_0022: "1레벨=1개"
INITIAL_SOUL_POWER: int = 10  # L1 base

LEVEL_CAP: int = 11

# ── XP_CURVE ─────────────────────────────────────────────────────────────────
# 누적 XP threshold (index = level - 1).
# 사용자 확정: L1→L2: 6 / L2→L3: 30 / L3→L4: 150 (5배 패턴).
# L4 이상도 5배 패턴 연장.
XP_CURVE: list[int] = [
    0,            # L1
    6,            # L2  (+6)
    36,           # L3  (+30)
    186,          # L4  (+150)
    936,          # L5  (+750)
    4_686,        # L6  (+3,750)
    23_436,       # L7  (+18,750)
    117_186,      # L8  (+93,750)
    585_936,      # L9  (+468,750)
    2_929_686,    # L10 (+2,343,750)
    14_648_436,   # L11 (+11,718,750)
]


def xp_for_level(target_level: int) -> int:
    """target_level 달성에 필요한 최소 누적 XP."""
    if target_level <= 1:
        return 0
    idx = min(target_level - 1, LEVEL_CAP - 1)
    return XP_CURVE[idx]


def compute_level_for_xp(total_xp: int) -> int:
    """누적 XP → 현재 level."""
    level = 1
    for idx, threshold in enumerate(XP_CURVE):
        if total_xp >= threshold:
            level = idx + 1
    return min(level, LEVEL_CAP)


def soul_power_gain_on_level_up(new_level: int) -> int:
    """레벨업 시 영혼력 증가량. L≤5: +10, L>5: +30."""
    return 10 if new_level <= 5 else 30


def compute_soul_power_for_level(level: int) -> int:
    """레벨 → 누적 영혼력 (L1 base 10, 레벨업마다 soul_power_gain 누적)."""
    sp = INITIAL_SOUL_POWER
    for lvl in range(2, min(level, LEVEL_CAP) + 1):
        sp += soul_power_gain_on_level_up(lvl)
    return sp


def compute_xp_grant(
    enemy_grade: int | None,
    is_first_kill: bool,
    modifiers: list[str],
) -> int:
    """enemy 처치 시 XP 계산.

    base = 10 - grade (본문 정합):
    - wiki 008: 포탈 +2 ≈ 8등급 마물 → 8등급 base 2
    - ep_0035: 5등급 캠보르미어 EXP +5

    is_first_kill=False 시 0 (ep_0022: 동일 몬스터 최초 1회만).
    modifiers: "guardian" (+3) / "variant" (+1).
    """
    if not is_first_kill:
        return 0
    grade = enemy_grade if enemy_grade is not None else 5
    if grade < 1 or grade > 9:
        return 0
    base = 10 - grade  # 본문 정합: 9등급=1 / 8등급=2 / 5등급=5 / 1등급=9
    bonus = 0
    if "guardian" in modifiers:
        bonus += 3   # ep_0035: 수호자 처치 보너스 +3
    if "variant" in modifiers:
        bonus += 1   # ep_0035: 상위 변이종 처치 보너스 +1
    return base + bonus
