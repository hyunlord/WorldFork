"""1층 빛 자원 정의 — 작품 본질.

자료 출처:
- 11화: 정령 등불 (10h / 회복 2h / 요정 한정)
- 23화: 횃불 (한 뼘 마도구, 3일, 1만 스톤)
- 24/419/420화: 조명탄 (★ 50m 반경, 단발)
- 337/339화: 라이트 젬 (★ 자료 추가 검증 후 추가)
"""

from __future__ import annotations

from ..state_v2 import LightSource, LightSourceType

_TORCH = LightSource(
    name="횃불",
    light_type=LightSourceType.TORCH,
    duration_hours=72.0,  # ★ 23화: 3일
    cooldown_hours=None,  # ★ 마도구 (본 commit은 기본 명시만)
    radius_meters=10.0,  # ★ 1차 자료 가시거리 10m
    cost_stones=10000,  # ★ 23화: 1만 스톤
    is_consumable=False,
)

_SPIRIT_LANTERN = LightSource(
    name="정령 등불",
    light_type=LightSourceType.SPIRIT,
    duration_hours=10.0,  # ★ 11화: 10시간
    cooldown_hours=2.0,  # ★ 11화: 회복 2시간
    radius_meters=10.0,
    cost_stones=0,  # ★ 종족 능력 (요정 한정)
    is_consumable=False,
    requires_race="요정",  # ★ 정령술 종족 한정
)

_FLARE = LightSource(
    name="조명탄",
    light_type=LightSourceType.FLARE,
    duration_hours=None,  # 단발
    cooldown_hours=None,
    radius_meters=50.0,  # ★ 1차 자료: 50m
    cost_stones=0,  # ★ 자료 X (정직)
    is_consumable=True,
)


FLOOR1_LIGHT_SOURCES: tuple[LightSource, ...] = (
    _TORCH,
    _SPIRIT_LANTERN,
    _FLARE,
)
