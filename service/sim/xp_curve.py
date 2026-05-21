"""Phase D step 6d — XP curve + level logic (본문 정합).

ep_0022: 동일 몬스터 최초 1회만 XP.
ep_0035: 레벨업 시 HP 변경 X — 영혼력(이능) + 정수 슬롯만.
wiki 008: L≤5 영혼력 +10, L>5 +30. cap=11.
"""

from __future__ import annotations

# 누적 XP threshold — index=level-1, 해당 값 이상 시 그 레벨 달성
# L1→L2: 5 / L2→L3: 15 / ... / L10→L11: 5000
XP_CURVE: list[int] = [
    0,      # L1 — 시작점
    5,      # L2
    20,     # L3
    55,     # L4
    130,    # L5
    280,    # L6
    580,    # L7
    1180,   # L8
    2380,   # L9
    4880,   # L10
    9880,   # L11
]

LEVEL_CAP = 11
INITIAL_LEVEL = 4        # 비요른 시작 레벨 (본문 정합)
INITIAL_SOUL_POWER = 40  # L1 base 10 + L2 +10 + L3 +10 + L4 +10


def xp_for_level(target_level: int) -> int:
    """target_level 달성에 필요한 최소 누적 XP."""
    if target_level <= 1:
        return 0
    idx = min(target_level - 1, LEVEL_CAP - 1)
    return XP_CURVE[idx]


def compute_level_for_xp(total_xp: int) -> int:
    """누적 XP → 현재 level (ep_0022 curve 정합)."""
    level = 1
    for idx, threshold in enumerate(XP_CURVE):
        if total_xp >= threshold:
            level = idx + 1
    return min(level, LEVEL_CAP)


def soul_power_gain_on_level_up(new_level: int) -> int:
    """레벨업 시 영혼력 증가량 (ep_0022/wiki 정합). L≤5: +10, L>5: +30."""
    return 10 if new_level <= 5 else 30


def compute_xp_grant(
    enemy_grade: int | None,
    is_first_kill: bool,
    modifiers: list[str],
) -> int:
    """enemy 처치 시 XP 계산.

    is_first_kill=False 시 0 (ep_0022: 동일 몬스터 최초 1회만).
    modifiers: "guardian" (+3) / "variant" (+1) / "stratum_boss" (base+99, +15)
    """
    if not is_first_kill:
        return 0
    grade = enemy_grade if enemy_grade is not None else 1
    base = grade  # grade × 1 (ep_0375: 킹슬라임=9등급 → EXP+4+수호자+3)
    bonus = 0
    if "stratum_boss" in modifiers:
        base += 99   # 계층군주 base ≈ 100 (ep_0489: 드레드피어 EXP+100)
        bonus += 15  # 계층군주 처치 보너스 +15
    if "guardian" in modifiers:
        bonus += 3   # 수호자 처치 보너스 +3
    if "variant" in modifiers:
        bonus += 1   # 상위 변이종 처치 보너스 +1
    return base + bonus
