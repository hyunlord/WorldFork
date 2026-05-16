"""Phase 9.17-b role-system — Role enum + Class→Role mapping.

검증 본질 (★ 44화 본문 정합):
- ClassType.SCOUT 추가 (★ 44화 '탐색꾼')
- Role enum 5개 (★ TANK / DPS / SCOUT / SUPPORT / HEALER)
- CLASS_TO_ROLE mapping:
  * warrior → TANK (★ 비요른)
  * mage → DPS (★ 28화 '최강')
  * priest → HEALER (★ 5화 '중층')
  * paladin → SUPPORT (★ 본문 X)
  * scout → SCOUT (★ 44화)
- get_role_for_class fallback DPS
- gm_agent prompt 본격 역할 분포 + 3+ alive 부재 경고

본문 정합:
- 44화: 탱커 / 탐색꾼 / 부재 치명적
- 28화: 마법사 = 최강 (DPS)
- 5화: 신관 = 중층 (HEALER)

추측 (★ docstring):
- paladin → SUPPORT
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    ClassType,
    Role,
)
from service.game.turn_handler_v2 import (
    CLASS_TO_ROLE,
    get_role_for_class,
)

# ─── 1. ClassType.SCOUT ───


def test_classtype_scout_value() -> None:
    """44화 정합 — '탐색꾼' enum value."""
    assert ClassType.SCOUT.value == "scout"


def test_classtype_count_5() -> None:
    """warrior/mage/priest/paladin/scout = 5."""
    assert len(list(ClassType)) == 5


# ─── 2. Role enum ───


def test_role_tank() -> None:
    assert Role.TANK.value == "tank"


def test_role_dps() -> None:
    assert Role.DPS.value == "dps"


def test_role_scout() -> None:
    assert Role.SCOUT.value == "scout"


def test_role_support() -> None:
    assert Role.SUPPORT.value == "support"


def test_role_healer() -> None:
    assert Role.HEALER.value == "healer"


def test_role_count_5() -> None:
    assert len(list(Role)) == 5


# ─── 3. CLASS_TO_ROLE mapping ───


def test_warrior_to_tank_44hwa() -> None:
    """44화 정합 — 비요른 바바리안 = 탱커."""
    assert CLASS_TO_ROLE[ClassType.WARRIOR.value] == Role.TANK.value


def test_mage_to_dps_28hwa() -> None:
    """28화 정합 — 마법사 = '최강의 직업' (DPS)."""
    assert CLASS_TO_ROLE[ClassType.MAGE.value] == Role.DPS.value


def test_priest_to_healer_5hwa() -> None:
    """5화 정합 — 신관 = 중층 (HEALER)."""
    assert CLASS_TO_ROLE[ClassType.PRIEST.value] == Role.HEALER.value


def test_paladin_to_support_guess() -> None:
    """본문 X — 추측 (★ docstring)."""
    assert CLASS_TO_ROLE[ClassType.PALADIN.value] == Role.SUPPORT.value


def test_scout_to_scout_44hwa() -> None:
    """44화 정합 — 탐색꾼."""
    assert CLASS_TO_ROLE[ClassType.SCOUT.value] == Role.SCOUT.value


def test_all_classes_mapped() -> None:
    for ct in ClassType:
        assert ct.value in CLASS_TO_ROLE


# ─── 4. get_role_for_class ───


def test_get_role_warrior() -> None:
    assert get_role_for_class("warrior") == "tank"


def test_get_role_mage() -> None:
    assert get_role_for_class("mage") == "dps"


def test_get_role_unknown_default_dps() -> None:
    assert get_role_for_class("unknown") == "dps"


def test_get_role_empty_default_dps() -> None:
    assert get_role_for_class("") == "dps"


# ─── 5. gm_agent prompt — 역할 분포 + 부재 경고 ───


def _ctx_with_party(
    party: list[tuple[str, str, int]],
) -> dict[str, Any]:
    """party = [(name, class_type, hp)]."""
    chars: dict[str, dict[str, Any]] = {}
    names: list[str] = []
    for name, cls, hp in party:
        chars[name] = {
            "race": "바바리안",
            "hp": hp,
            "hp_max": 100,
            "level": 1,
            "physical": 12,
            "strength": 14,
            "grade": 1,
            "class_type": cls,
        }
        names.append(name)
    return {
        "work_name": "1층",
        "work_genre": "판타지",
        "world_setting": "라프도니아",
        "world_tone": "차분",
        "world_rules": ["1층 어둠"],
        "main_character_name": names[0] if names else "",
        "main_character_role": "주인공",
        "supporting_characters": [],
        "current_location": "1층",
        "current_turn": 0,
        "v2_characters": chars,
        "v2_world_state": {
            "party_members": names,
            "max_party_members": 5,
        },
    }


def test_prompt_shows_role_distribution() -> None:
    prompt = _gm_system_prompt(
        _ctx_with_party(
            [
                ("비요른", "warrior", 100),
                ("아루아", "mage", 100),
                ("엘리사", "priest", 100),
            ]
        )
    )
    assert "역할 분포" in prompt
    assert "tank 1" in prompt
    assert "dps 1" in prompt
    assert "healer 1" in prompt


def test_prompt_warns_missing_critical_3_mages() -> None:
    """3+ alive 모두 mage → 탱커/힐러/탐색꾼 부재 경고."""
    prompt = _gm_system_prompt(
        _ctx_with_party(
            [
                ("M1", "mage", 100),
                ("M2", "mage", 100),
                ("M3", "mage", 100),
            ]
        )
    )
    assert "역할 부재" in prompt
    assert "탱커" in prompt
    assert "힐러" in prompt
    assert "탐색꾼" in prompt
    assert "44화" in prompt


def test_prompt_no_missing_warning_solo() -> None:
    """1인 (9.17-a 정합) → 역할 부재 경고 본격 X."""
    prompt = _gm_system_prompt(
        _ctx_with_party([("비요른", "warrior", 100)])
    )
    assert "역할 부재" not in prompt


def test_prompt_no_missing_warning_two_persons() -> None:
    """2인 → 역할 부재 경고 본격 X (★ 9.17-a 중립 정합)."""
    prompt = _gm_system_prompt(
        _ctx_with_party(
            [
                ("비요른", "warrior", 100),
                ("에르웬", "mage", 100),
            ]
        )
    )
    assert "역할 부재" not in prompt


def test_prompt_full_team_no_missing_warning() -> None:
    """tank + healer + scout 모두 본격 → 경고 X."""
    prompt = _gm_system_prompt(
        _ctx_with_party(
            [
                ("Tank", "warrior", 100),
                ("Heal", "priest", 100),
                ("Sc", "scout", 100),
            ]
        )
    )
    assert "역할 부재" not in prompt


def test_prompt_partial_missing_only_some() -> None:
    """tank/healer 본격, scout 본격 X → '탐색꾼'만 경고."""
    prompt = _gm_system_prompt(
        _ctx_with_party(
            [
                ("Tank", "warrior", 100),
                ("Heal", "priest", 100),
                ("M3", "mage", 100),
            ]
        )
    )
    assert "역할 부재" in prompt
    assert "탐색꾼" in prompt
    assert "탱커" not in prompt.split("역할 부재")[1].split("\n")[0]
    assert "힐러" not in prompt.split("역할 부재")[1].split("\n")[0]


def test_prompt_dead_member_excluded() -> None:
    """죽은 priest 본격 alive count 본격 X → healer 부재 경고."""
    prompt = _gm_system_prompt(
        _ctx_with_party(
            [
                ("Tank", "warrior", 100),
                ("Dead", "priest", 0),
                ("Mage", "mage", 100),
                ("Sc", "scout", 100),
            ]
        )
    )
    # alive 3: tank/dps/scout — healer 부재
    assert "역할 부재" in prompt
    assert "힐러" in prompt
