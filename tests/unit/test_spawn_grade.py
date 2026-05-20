"""Phase D step 6c — estimate_location_grade / spawn_count / extract_race_habitat."""

from __future__ import annotations

from service.canon.spawn import (
    estimate_location_grade,
    extract_race_habitat,
    spawn_count_for_grade,
)

# ─── estimate_location_grade ───


def test_grade_high_keyword_deep() -> None:
    assert estimate_location_grade("심층 구역") == 7


def test_grade_high_keyword_floor9() -> None:
    assert estimate_location_grade("던전 9층") == 7


def test_grade_high_keyword_rift() -> None:
    assert estimate_location_grade("심층 균열 내부") == 7


def test_grade_mid_keyword_floor5() -> None:
    assert estimate_location_grade("5층 복도") == 4


def test_grade_mid_keyword_inner() -> None:
    assert estimate_location_grade("탑 내부") == 4


def test_grade_low_keyword_entrance() -> None:
    assert estimate_location_grade("던전 입구") == 1


def test_grade_low_keyword_floor1() -> None:
    assert estimate_location_grade("1층 A구역") == 1


def test_grade_default_no_keyword() -> None:
    assert estimate_location_grade("알 수 없는 장소") == 3


def test_grade_uses_description() -> None:
    assert estimate_location_grade("미지의 구역", "심층 아래쪽") == 7


def test_grade_description_none() -> None:
    assert estimate_location_grade("미지의 구역", None) == 3


# ─── spawn_count_for_grade ───


def test_spawn_count_high_grade() -> None:
    lo, hi = spawn_count_for_grade(7)
    assert lo == 2 and hi == 4


def test_spawn_count_mid_grade() -> None:
    lo, hi = spawn_count_for_grade(4)
    assert lo == 1 and hi == 2


def test_spawn_count_low_grade() -> None:
    lo, hi = spawn_count_for_grade(1)
    assert lo == 1 and hi == 1


def test_spawn_count_boundary_grade_9() -> None:
    lo, hi = spawn_count_for_grade(9)
    assert lo == 2 and hi == 4


# ─── extract_race_habitat ───


def test_habitat_dungeon_keyword() -> None:
    result = extract_race_habitat("지하 동굴에 서식한다")
    assert "dungeon" in result


def test_habitat_wilderness_keyword() -> None:
    result = extract_race_habitat("숲과 산악 지대에 무리 지어 생활한다")
    assert "wilderness" in result


def test_habitat_rift_keyword() -> None:
    result = extract_race_habitat("균열을 통해 출현하는 존재")
    assert "rift" in result


def test_habitat_multiple() -> None:
    result = extract_race_habitat("산악 지대와 지하 동굴 양쪽에 서식")
    assert "dungeon" in result
    assert "wilderness" in result


def test_habitat_empty_description() -> None:
    assert extract_race_habitat("") == []


def test_habitat_none_description() -> None:
    assert extract_race_habitat(None) == []


def test_habitat_no_match() -> None:
    result = extract_race_habitat("마을 광장에서 활동한다")
    assert result == []
