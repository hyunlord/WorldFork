"""enemy_type → weakness_types 자동 유도 + player 공격 1.5x/면역 0x 검증.

★ 핵심: weakness/immunity multiplier는 compute_damage_multiplier(기존)가 담당.
이 테스트는 enemy_from_dict가 enemy_type 정합 weakness_types를 유도해
combat 1.5x/0x가 실제 발현되는지 확인 (★ 배선 gap fix).
"""

from __future__ import annotations

from service.sim.combat import compute_damage_multiplier, execute_player_attack
from service.sim.enemy import Enemy, EnemyType, enemy_from_dict

# ── enemy_from_dict weakness 자동 유도 ──────────────────────────────────────


def test_undead_dict_derives_weakness() -> None:
    """enemy_type=undead, weakness_types 미지정 → 신성력/불 유도."""
    e = enemy_from_dict({"name": "스켈레톤", "enemy_type": "undead"})
    assert e.enemy_type == EnemyType.UNDEAD
    assert set(e.weakness_types) == {"신성력", "불"}


def test_cold_beast_dict_derives_weakness() -> None:
    e = enemy_from_dict({"name": "예티", "enemy_type": "cold_beast"})
    assert e.enemy_type == EnemyType.COLD_BEAST
    assert e.weakness_types == ["전격"]


def test_dark_dict_derives_weakness() -> None:
    e = enemy_from_dict({"name": "그림자", "enemy_type": "dark"})
    assert e.enemy_type == EnemyType.DARK
    assert set(e.weakness_types) == {"태양", "빛"}


def test_name_inferred_type_derives_weakness() -> None:
    """enemy_type 미지정이라도 name 정합 추론 → weakness 유도."""
    e = enemy_from_dict({"name": "구울"})
    assert e.enemy_type == EnemyType.UNDEAD
    assert set(e.weakness_types) == {"신성력", "불"}


def test_explicit_weakness_preserved() -> None:
    """명시 weakness_types는 보존 (자동 유도 X)."""
    e = enemy_from_dict({
        "name": "변종", "enemy_type": "undead", "weakness_types": ["전격"],
    })
    assert e.weakness_types == ["전격"]


def test_physical_no_weakness() -> None:
    """육체형 — weakness 없음."""
    e = enemy_from_dict({"name": "산적", "enemy_type": "physical"})
    assert e.weakness_types == []


def test_spirit_no_weakness_types() -> None:
    """영체 — weakness_types 비어있음 (면역은 별도 처리)."""
    e = enemy_from_dict({"name": "원혼", "enemy_type": "spirit"})
    assert e.enemy_type == EnemyType.SPIRIT
    assert e.weakness_types == []


# ── combat multiplier 발현 (★ 기존 compute_damage_multiplier 정합) ──────────


def test_undead_weakness_15x_via_fire() -> None:
    """언데드 + 불 element → 1.5x."""
    e = enemy_from_dict({"name": "스켈레톤", "enemy_type": "undead"})
    assert compute_damage_multiplier(e, ["물리", "불"]) == 1.5


def test_undead_physical_only_normal() -> None:
    """언데드 + 물리 only → 1.0x (약점 element 불일치)."""
    e = enemy_from_dict({"name": "스켈레톤", "enemy_type": "undead"})
    assert compute_damage_multiplier(e, ["물리"]) == 1.0


def test_cold_beast_lightning_15x() -> None:
    e = enemy_from_dict({"name": "예티", "enemy_type": "cold_beast"})
    assert compute_damage_multiplier(e, ["전격"]) == 1.5


def test_spirit_physical_immune_0x() -> None:
    """영체 + 물리 only → 0.0x 면역."""
    e = enemy_from_dict({"name": "원혼", "enemy_type": "spirit"})
    assert compute_damage_multiplier(e, ["물리"]) == 0.0


def test_spirit_nonphysical_not_immune() -> None:
    """영체 + 비물리 → 면역 X (1.0x)."""
    e = enemy_from_dict({"name": "원혼", "enemy_type": "spirit"})
    assert compute_damage_multiplier(e, ["신성력"]) == 1.0


# ── execute_player_attack end-to-end ────────────────────────────────────────


def test_player_attack_undead_fire_amplified() -> None:
    """player 불 공격 → 언데드 1.5x damage."""
    enemy = enemy_from_dict({
        "name": "스켈레톤", "enemy_type": "undead",
        "hp": 100, "max_hp": 100, "defense": 0,
    })
    # base = 20 - 0 = 20, ×1.5 = 30 (치명타 rand 고정 → 미발동)
    _, log = execute_player_attack(
        [enemy], 0, 20, "공격", ["물리", "불"], rand_func=lambda: 0.99,
    )
    assert log.weakness_hit is True
    assert log.damage_dealt == 30


def test_player_attack_spirit_physical_immune() -> None:
    """player 물리 공격 → 영체 면역 (damage 0)."""
    enemy = enemy_from_dict({
        "name": "원혼", "enemy_type": "spirit",
        "hp": 100, "max_hp": 100, "defense": 0,
    })
    _, log = execute_player_attack([enemy], 0, 20, "공격", ["물리"])
    assert log.immune is True
    assert log.damage_dealt == 0


def test_enemy_class_default_no_weakness() -> None:
    """Enemy 직접 생성 (dict 경유 X) — 자동 유도 없음 (기존 동작)."""
    e = Enemy(name="X", hp=10, max_hp=10, attack=5, defense=1,
              enemy_type=EnemyType.UNDEAD)
    assert e.weakness_types == []
