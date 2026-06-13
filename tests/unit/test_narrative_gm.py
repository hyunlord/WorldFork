"""AI GM 오프닝 슬라이스 Phase 1 — 캐논 앵커 + 구조화 GM 단위 테스트.

캐논 앵커(비트 순서·변환명·카이라 5축), GM 구조화 파싱(narration/choices/state_delta),
gm_beat가 client.generate_json을 schema로 호출하는지(freeform 아님). LLM은 mock.
"""

from unittest.mock import MagicMock

from service.sim.narrative_gm import (
    GMStateDelta,
    extract_narration,
    gm_beat,
    parse_beat_result,
    parse_beat_text,
)
from service.sim.opening_canon import (
    COMING_OF_AGE_WEAPONS,
    KAIRA_DISPOSITION,
    KAIRA_NAME,
    PLAYER_NAME,
    Beat,
    anchor_for,
    build_anchor_prompt,
    next_beat,
    parse_beat,
)


class TestOpeningCanon:
    def test_beat_order(self) -> None:
        assert next_beat(Beat.COMING_OF_AGE) is Beat.DUNGEON_ENTRY
        assert next_beat(Beat.DUNGEON_ENTRY) is Beat.FIRST_ENCOUNTER
        assert next_beat(Beat.FIRST_ENCOUNTER) is Beat.AFTERMATH
        assert next_beat(Beat.AFTERMATH) is None  # 마지막

    def test_parse_beat(self) -> None:
        assert parse_beat("dungeon_entry") is Beat.DUNGEON_ENTRY
        assert parse_beat("없는비트") is None

    def test_kaira_disposition_world_bible(self) -> None:
        # WORLD_BIBLE §11: 충성80/저돌75/지혜35/변덕25/유대65.
        d = KAIRA_DISPOSITION
        assert (d.loyalty, d.aggression, d.wisdom, d.whimsy, d.bond) == (80, 75, 35, 25, 65)

    def test_anchor_uses_transformed_names(self) -> None:
        # ★ 코드=변환명 — 앵커 문자열에 원작명(비요른/아이나르)이 없어야 한다(git IP 차단).
        p = build_anchor_prompt(Beat.FIRST_ENCOUNTER, weapon="양손도끼")
        assert PLAYER_NAME in p and KAIRA_NAME in p
        assert "비요른" not in p and "아이나르" not in p
        assert "양손도끼" in p

    def test_weapon_choices_present(self) -> None:
        ids = {w.id for w in COMING_OF_AGE_WEAPONS}
        assert {"axe", "hammer", "greatsword"} <= ids

    def test_anchor_has_goal(self) -> None:
        assert anchor_for(Beat.COMING_OF_AGE).goal


class TestParseBeatResult:
    def test_full_parse(self) -> None:
        r = parse_beat_result(
            {
                "narration": "나는 도끼를 골랐다.",
                "choices": [
                    {"id": "a", "label": "돌격"},
                    {"id": "b", "label": "관망"},
                ],
                "state_delta": {
                    "flags": {"성인식": "완료"},
                    "hp_change": -5,
                    "relationship_delta": {"카이라": 3},
                    "inventory_add": ["양손도끼"],
                    "scene_transition": "dungeon_entry",
                },
                "speaker": "투르윈",
            }
        )
        assert r.narration == "나는 도끼를 골랐다."
        assert len(r.choices) == 2 and r.choices[0].id == "a"
        assert r.state_delta.flags == {"성인식": "완료"}
        assert r.state_delta.hp_change == -5
        assert r.state_delta.relationship_delta == {"카이라": 3}
        assert r.state_delta.inventory_add == ["양손도끼"]
        assert r.state_delta.scene_transition == "dungeon_entry"
        assert r.speaker == "투르윈"

    def test_missing_delta_safe_defaults(self) -> None:
        r = parse_beat_result(
            {"narration": "장면.", "choices": [{"id": "x", "label": "ㄱ"}]}
        )
        assert isinstance(r.state_delta, GMStateDelta)
        assert r.state_delta.hp_change == 0
        assert r.state_delta.scene_transition is None
        assert r.speaker is None

    def test_bad_choices_filtered(self) -> None:
        r = parse_beat_result(
            {
                "narration": "n",
                "choices": [{"id": "a", "label": "ok"}, {"id": "", "label": ""}, "junk"],
                "state_delta": {},
            }
        )
        assert len(r.choices) == 1  # 빈/이상 선택지 제거


class TestParseBeatText:
    """스트리밍 종료 후 누적 텍스트 파싱(astream은 schema 가드 없음 → 관대 추출)."""

    def test_extracts_json_from_noisy_text(self) -> None:
        noisy = '어쩌고 {"narration": "장면.", "choices": [{"id":"a","label":"ㄱ"},' \
            '{"id":"b","label":"ㄴ"}], "state_delta": {"flags": {"k": "v"}}} 뒤꼬리'
        r = parse_beat_text(noisy)
        assert r.narration == "장면."
        assert len(r.choices) == 2
        assert r.state_delta.flags == {"k": "v"}

    def test_no_json_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            parse_beat_text("JSON이 전혀 없는 텍스트")


class TestExtractNarration:
    """스트리밍 점진 표시 — 누적 JSON에서 narration을 현재까지 디코드."""

    def test_partial_stream(self) -> None:
        # 아직 닫히지 않은 narration도 현재까지 반환(흐르는 표시).
        assert extract_narration('{"narration": "나는 도끼를') == "나는 도끼를"

    def test_closed_string(self) -> None:
        full = '{"narration": "도끼를 들었다.", "choices": []}'
        assert extract_narration(full) == "도끼를 들었다."

    def test_escapes_decoded(self) -> None:
        assert extract_narration('{"narration": "줄1\\n줄2 \\"인용\\""') == '줄1\n줄2 "인용"'

    def test_no_narration_key(self) -> None:
        assert extract_narration('{"choices": []}') is None


class TestGmBeatCall:
    def test_calls_generate_json_with_schema(self) -> None:
        client = MagicMock()
        client.generate_json.return_value = MagicMock(
            parsed={
                "narration": "부족장이 나를 불렀다.",
                "choices": [{"id": "axe", "label": "양손도끼"}, {"id": "sword", "label": "대검"}],
                "state_delta": {"flags": {"성인식": "진행"}},
            }
        )
        result = gm_beat(
            Beat.COMING_OF_AGE,
            hp=120,
            max_hp=120,
            weapon="",
            stones=0,
            flags={},
            history="",
            action="(성인식)",
            client=client,
        )
        # schema 기반 구조화 호출(freeform 아님)
        _, kwargs = client.generate_json.call_args
        assert "schema" in kwargs and kwargs["schema"]["required"]
        assert result.choices[0].label == "양손도끼"
        assert result.state_delta.flags == {"성인식": "진행"}
