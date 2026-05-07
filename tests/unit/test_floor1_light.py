"""1층 빛 자원 진짜 정의 테스트.

본인 본질 (2026-05-07):
- 횃불: 3일 / 1만 스톤 (★ 23화)
- 정령 등불: 10h / 회복 2h / 요정 한정 (★ 11화)
- 조명탄: 단발 / 50m (★ 1차 자료)
"""

from __future__ import annotations

from service.game.floors.floor1 import get_floor1_definition
from service.game.floors.floor1_light import FLOOR1_LIGHT_SOURCES
from service.game.state_v2 import LightSource, LightSourceType


def _find_light(light_type: LightSourceType) -> LightSource | None:
    return next(
        (ls for ls in FLOOR1_LIGHT_SOURCES if ls.light_type == light_type),
        None,
    )


def test_floor1_has_3_light_sources() -> None:
    """1층 빛 자원 3종 (횃불/정령/조명탄)."""
    assert len(FLOOR1_LIGHT_SOURCES) == 3
    types = {ls.light_type for ls in FLOOR1_LIGHT_SOURCES}
    assert LightSourceType.TORCH in types
    assert LightSourceType.SPIRIT in types
    assert LightSourceType.FLARE in types


def test_torch_72_hours_10000_stones() -> None:
    """횃불: 3일(72h) / 1만 스톤 (★ 23화)."""
    torch = _find_light(LightSourceType.TORCH)
    assert torch is not None
    assert torch.duration_hours == 72.0
    assert torch.cost_stones == 10000
    assert not torch.is_consumable


def test_spirit_10h_2h_cooldown_faerie() -> None:
    """정령 등불: 10h 지속 / 회복 2h / 요정 한정 (★ 11화)."""
    spirit = _find_light(LightSourceType.SPIRIT)
    assert spirit is not None
    assert spirit.duration_hours == 10.0
    assert spirit.cooldown_hours == 2.0
    assert spirit.requires_race == "요정"


def test_flare_single_use_50m() -> None:
    """조명탄: 단발 / 50m 반경 (★ 1차 자료)."""
    flare = _find_light(LightSourceType.FLARE)
    assert flare is not None
    assert flare.duration_hours is None
    assert flare.radius_meters == 50.0
    assert flare.is_consumable


def test_floor1_definition_includes_light_sources() -> None:
    f1 = get_floor1_definition()
    assert len(f1.light_sources) == 3
