"""build_gm_canon — GM Canon Contract 주입 검증 (고증 RAG 배선).

끊겨 있던 Canon Contract(빈 문자열)를 맥락 정합 canon으로 채우는 헬퍼. 전역
EntityIndex에서 위치/적/키워드 정합 fact만 압축 주입하고 persona/무기 앵커를 덧댄다.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Character, Essence, Location, Mechanism, Race
from service.sim.gm_narrator import build_gm_canon


def _make_facts() -> CanonFacts:
    return CanonFacts(
        essences=[
            Essence(name="고블린 정수", grade=9, source_monster="고블린"),
        ],
        characters=[
            # 원작 주인공 류 — 부분일치 노이즈가 되면 안 된다(비요른과 모순).
            Character(name="한수", aliases=[], role="주인공", race="인간"),
        ],
        locations=[
            Location(
                name="1층: 수정동굴",
                location_type="dungeon",
                description=(
                    "수정이 광원. 동서남북 네 포탈 — "
                    "동 칼날늑대/서 노움/남 구울/북 고블린."
                ),
            ),
            # 1글자 location — '방'⊂'방향' 부분일치 노이즈 후보.
            Location(name="방", location_type="facility", description="에르웬의 방"),
        ],
        races=[
            Race(name="고블린", description="1층 북쪽 출몰 몬스터."),
        ],
        mechanisms=[Mechanism(name="정수 흡수", category="magic", description="흡수")],
    )


@pytest.fixture()
def _index() -> Iterator[None]:
    set_entity_index(EntityIndex(_make_facts()))
    yield
    clear_entity_index()


def test_persona_and_weapon_anchor(_index: None) -> None:
    canon = build_gm_canon("주변을 살핀다", "1층: 수정동굴", "특이사항 없음", [], "전투 도끼")
    assert "비요른" in canon and "흑곰족" in canon
    assert "전투 도끼" in canon  # 무기 앵커 — 무기 드리프트 예방


def test_location_fact_injected(_index: None) -> None:
    canon = build_gm_canon("들어선다", "1층: 수정동굴", "", [], "")
    # 위치 고증(방향별 몬스터)이 주입돼 baseline 모호함을 보강한다.
    assert "칼날늑대" in canon and "포탈" in canon


def test_hostile_fact_injected(_index: None) -> None:
    canon = build_gm_canon("고블린이 노려본다", "1층: 수정동굴", "고블린", ["고블린"], "")
    assert "고블린" in canon


def test_character_noise_excluded(_index: None) -> None:
    # 원작 인간 주인공 '한수'는 비요른 persona와 모순 — 키워드 정합서 배제돼야.
    canon = build_gm_canon("한수의 기억이 스친다", "1층: 수정동굴", "", [], "")
    assert "라프도니아" not in canon
    assert "인간" not in canon  # 한수 character 요약이 새지 않음


def test_short_name_substring_noise_excluded(_index: None) -> None:
    # '방' (1글자 location)이 '방향'에 부분일치해 새면 안 된다.
    canon = build_gm_canon("어느 방향으로 갈까", "1층: 수정동굴", "", [], "")
    assert "에르웬" not in canon


def test_empty_index_returns_persona_only() -> None:
    clear_entity_index()
    canon = build_gm_canon("x", "어딘가", "y", [], "도끼")
    assert "비요른" in canon and "도끼" in canon
    assert "\n- " not in canon  # 고증 라인 없음(인덱스 미적재)
