"""삼신교 본격 신 / 교단 정의 (★ Phase 9.5 temple-heal).

본문 정합:
- 268화: 토베라 교단 정사제 라이린 에르시나 + 바바리안 거절 규율
- 55화: 레아틀라스 — 탐험의 신, 선 성향
- 72화: 카루이 — 사제 엘리사

본문 X 본격 placeholder (★ docstring 정합):
- 토베라 / 카루이 본격 성향
- 레아틀라스 사제 이름

production caller (★ Phase 9.5):
- service/game/cities/rapdonia.py: 3 temple sub_areas
- service/game/turn_handler_v2.py: execute_heal_at_temple
- service/game/gm_agent.py: _format_city_context temple hint
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TempleDeity:
    """삼신교 본격 신 / 교단 본격 본격.

    is_canonical / canonical_priest_name:
    - True / 본격 본격 이름 = 본문 직접 등장 (★ 268화 라이린 / 72화 엘리사)
    - "" = 본문 X — placeholder (★ 후속 본문 발견 시 보강)
    """

    deity_id: str
    deity_name: str
    temple_name: str
    sub_area_id: str
    nature: str = ""  # ★ "선" 등 본격 본격 본격
    refuses_races: tuple[str, ...] = ()  # ★ 268화 바바리안 거절 본격
    canonical_priest_name: str = ""
    priest_rank: str = "사제"  # ★ 사제 / 정사제 / 대신관
    # ★ Phase 9.13 — rapdonia.py NPCDef.id 정합 (★ HEAL 할인 affinity lookup)
    priest_npc_id: str = ""


TOBERAH = TempleDeity(
    deity_id="toberah",
    deity_name="토베라",
    temple_name="토베라 신전",
    sub_area_id="toberah_temple",
    nature="",  # ★ 본문 X — placeholder
    refuses_races=("바바리안",),  # ★ 268화 본문 정합
    canonical_priest_name="라이린 에르시나",  # ★ 268화
    priest_rank="정사제",
    priest_npc_id="rairin_ersina",  # ★ rapdonia.py NPCDef
)


REATLAS = TempleDeity(
    deity_id="reatlas",
    deity_name="레아틀라스",
    temple_name="레아틀라스 신전",
    sub_area_id="reatlas_temple",
    nature="선",  # ★ 55화: '선 성향'
    refuses_races=(),
    canonical_priest_name="",  # ★ 본문 X — placeholder
    priest_rank="사제",
    priest_npc_id="reatlas_priest",  # ★ rapdonia.py NPCDef (placeholder)
)


KARUYI = TempleDeity(
    deity_id="karuyi",
    deity_name="카루이",
    temple_name="카루이 신전",
    sub_area_id="karuyi_temple",
    nature="",  # ★ 본문 X — placeholder
    refuses_races=(),
    canonical_priest_name="엘리사",  # ★ 72화
    priest_rank="사제",
    priest_npc_id="elisa",  # ★ rapdonia.py NPCDef
)


def get_deity_by_sub_area(sub_area_id: str) -> TempleDeity | None:
    """sub_area_id 본격 TempleDeity (★ None X — 3 inline check)."""
    if sub_area_id == TOBERAH.sub_area_id:
        return TOBERAH
    if sub_area_id == REATLAS.sub_area_id:
        return REATLAS
    if sub_area_id == KARUYI.sub_area_id:
        return KARUYI
    return None
