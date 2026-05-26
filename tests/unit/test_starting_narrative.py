"""Phase E-5: 시나리오 시작 narrative 단위 테스트."""
from __future__ import annotations

from service.canon.races import Race
from service.canon.scenario import ScenarioMode, build_starting_narrative


def test_bjorn_narrative_has_shield() -> None:
    """BJORN narrative — ep_0003 정합 방패 포함."""
    msg = build_starting_narrative(ScenarioMode.BJORN, Race.BARBARIAN)
    assert "방패" in msg


def test_bjorn_narrative_has_dungeon() -> None:
    """BJORN narrative — 미궁 포함."""
    msg = build_starting_narrative(ScenarioMode.BJORN, Race.BARBARIAN)
    assert "미궁" in msg


def test_bjorn_narrative_first_person() -> None:
    """1인칭 정합 (audit B 정합)."""
    msg = build_starting_narrative(ScenarioMode.BJORN, Race.BARBARIAN)
    assert msg.startswith("나는")


def test_new_explorer_race_narratives() -> None:
    """NEW_EXPLORER 5종 narrative — 키워드 + 1인칭 정합."""
    expected = {
        Race.BARBARIAN: "도끼",
        Race.HUMAN: "검",
        Race.DWARF: "망치",
        Race.BEASTKIN: "발톱",
        Race.FAIRY: "단검",
    }
    for race, keyword in expected.items():
        msg = build_starting_narrative(ScenarioMode.NEW_EXPLORER, race)
        assert keyword in msg, f"{race.value}: '{keyword}' missing"
        assert "라스카니아" in msg, f"{race.value}: 위치 누락"
        assert msg.startswith("나는"), f"{race.value}: 1인칭 아님"


def test_all_narratives_nonempty() -> None:
    """모든 mode × race 조합 narrative 비어 있지 않음."""
    for mode in ScenarioMode:
        for race in Race:
            msg = build_starting_narrative(mode, race)
            assert msg, f"{mode.value}+{race.value}: empty narrative"
