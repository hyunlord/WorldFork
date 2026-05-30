"""감응도 element 위력 보정 — combat 통합 테스트 (12f89a7 element + 13deef0 weakness)."""

from __future__ import annotations

from service.sim.combat import execute_player_attack
from service.sim.enemy import enemy_from_dict


def _undead(hp: int = 1000) -> list:
    return [enemy_from_dict({
        "name": "스켈레톤", "enemy_type": "undead",
        "hp": hp, "max_hp": hp, "defense": 0,
    })]


def test_element_attack_with_sensitivity_amplified() -> None:
    """불 공격 + 불 감응도 → element 위력 보정 (crit 고정)."""
    # base 20, undead 불 약점 ×1.5 = 30, 불 감응도 10 → ×1.2 = 36
    _, log = execute_player_attack(
        _undead(), 0, 20, "공격", ["물리", "불"],
        rand_func=lambda: 0.99,
        attack_sensitivities={"불": 10},
    )
    assert log.damage_dealt == 36  # int(30 × 1.2)


def test_element_attack_no_sensitivity() -> None:
    """불 공격 + 감응도 없음 → weakness만 (1.5x)."""
    _, log = execute_player_attack(
        _undead(), 0, 20, "공격", ["물리", "불"],
        rand_func=lambda: 0.99,
        attack_sensitivities={},
    )
    assert log.damage_dealt == 30  # 20 × 1.5, 보정 없음


def test_physical_only_sensitivity_ignored() -> None:
    """물리 단독 공격 → 불 감응도 있어도 무관."""
    _, log = execute_player_attack(
        _undead(), 0, 20, "공격", ["물리"],
        rand_func=lambda: 0.99,
        attack_sensitivities={"불": 50},
    )
    assert log.damage_dealt == 20  # 물리 1.0x, 감응도 무관


def test_context_total_sensitivities_flows() -> None:
    """ActionContext.total_sensitivities — 흡수 정수에서 파생."""
    from service.sim.action_context import ActionContext

    ctx = ActionContext(
        current_hp=100, max_hp=100, inventory=[], location="1층",
        absorbed_essences=[{
            "essence_name": "빙정 정수", "stat_bundle": {}, "skills": [],
            "grade": 5, "resistances": {}, "etc_abilities": [],
            "attack_elements": [], "sensitivities": {"냉기": 3},
        }],
    )
    assert ctx.total_sensitivities == {"냉기": 3}
