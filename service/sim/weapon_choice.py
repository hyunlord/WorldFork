"""성인식 무기 선택 — 게임 내 선택 처리 (ep_0002 고증, 게임 엔진 3단계).

무기 선택을 character 생성(미리 선택)에서 성인식 weapon_choice 단계로 이동.
부족장이 '골라라' → 플레이어가 무기를 고르면 장착 + element 정합(35a0ef6).

create_session과 무기 장착 로직을 공유하기 위한 헬퍼 모듈(순환 import 회피).
"""

from __future__ import annotations

from typing import Any

from service.canon.items import build_weapon_equipment
from service.canon.scenario import COMING_OF_AGE_WEAPONS, find_coming_of_age_weapon
from service.sim.equipment import equipment_to_dict

# 긴 이름 우선 — '양손 도끼'가 '양손 대검'보다 먼저 매칭되도록.
_WEAPON_NAMES = tuple(
    sorted((w.name for w in COMING_OF_AGE_WEAPONS), key=len, reverse=True)
)


def make_weapon_equipment(weapon_name: str) -> dict[str, Any]:
    """무기명 → equipment dict (attack_bonus + element 포함).

    create_session과 성인식 무기 선택이 동일 장착 로직을 쓴다(35a0ef6 정합).
    """
    sw = find_coming_of_age_weapon(weapon_name)
    return equipment_to_dict(
        build_weapon_equipment(
            weapon_name,
            sw.attack_bonus if sw is not None else 0,
            sw.description if sw is not None else "",
        )
    )


def match_weapon_in_text(text: str) -> str | None:
    """플레이어 입력에서 성인식 무기명을 추출(없으면 None).

    '양손 도끼를 고른다' → '양손 도끼'. 긴 이름 우선으로 부분 겹침 방지.
    """
    for name in _WEAPON_NAMES:
        if name in text:
            return name
    return None
