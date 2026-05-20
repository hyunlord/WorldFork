"""Phase D step 5 — freeform_handler entity context inject (mock-based)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from service.api.schemas.freeform_action import ExtractedEntities, StateDelta
from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Character, Essence, Location, Mechanism, Race
from service.sim.freeform_handler import _build_canon_context, _collect_entity_refs, freeform_action


def _simple_facts() -> CanonFacts:
    return CanonFacts(
        essences=[
            Essence(
                name="화염 정수",
                grade=2,
                skills_granted=["화염구"],
                absorption_mechanism="흡수 시 화력 증가",
            ),
        ],
        characters=[
            Character(
                name="투르윈",
                aliases=["주인공"],
                role="주인공",
                race="인간",
                grade=None,
                background="이계인",
            ),
        ],
        locations=[
            Location(name="2층 입구", location_type="dungeon", description="던전 2층 시작 지점"),
        ],
        races=[Race(name="인간", description="일반 종족")],
        mechanisms=[
            Mechanism(name="등급 상승", category="progression", description="등급 1→9 성장"),
        ],
    )


@pytest.fixture(autouse=True)
def _entity_index(tmp_path: object) -> object:  # type: ignore[override]
    set_entity_index(EntityIndex(_simple_facts()))
    yield
    clear_entity_index()


# ── _build_canon_context ──────────────────────────────────────────────────────


def test_build_canon_context_empty() -> None:
    assert _build_canon_context([]) == ""


def test_build_canon_context_with_refs() -> None:
    from service.canon.entity_index import EntityRef

    refs = [EntityRef("character", "투르윈", "캐릭터 투르윈 · 주인공")]
    ctx = _build_canon_context(refs)
    assert "본문 정합 정보:" in ctx
    assert "투르윈" in ctx


# ── _collect_entity_refs ──────────────────────────────────────────────────────


def test_collect_entity_refs_by_extracted() -> None:
    entities = ExtractedEntities(actor="투르윈", location=None, item=None)
    refs = _collect_entity_refs("아무 텍스트", entities)
    names = [r.name for r in refs]
    assert "투르윈" in names


def test_collect_entity_refs_by_keyword() -> None:
    refs = _collect_entity_refs("화염 정수를 흡수한다", None)
    names = [r.name for r in refs]
    assert "화염 정수" in names


def test_collect_entity_refs_max_five() -> None:
    # 텍스트에 여러 entity 포함 — 최대 5개
    refs = _collect_entity_refs("투르윈 화염 정수 2층 입구 인간 등급 상승", None)
    assert len(refs) <= 5


def test_collect_entity_refs_dedup() -> None:
    # extracted actor와 keyword에서 동일 entity → 중복 제거
    entities = ExtractedEntities(actor="투르윈", location=None, item=None)
    refs = _collect_entity_refs("투르윈이 이동한다", entities)
    names = [r.name for r in refs]
    assert names.count("투르윈") == 1


def test_collect_entity_refs_no_index() -> None:
    clear_entity_index()
    refs = _collect_entity_refs("투르윈", None)
    assert refs == []
    # restore for autouse cleanup
    set_entity_index(EntityIndex(_simple_facts()))


# ── freeform_action integration ───────────────────────────────────────────────


def _mock_generate_json(narrative: str = "투르윈이 전진한다.") -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.parsed = {
        "narrative": narrative,
        "state_delta": {
            "hp_change": 0,
            "inventory_add": [],
            "inventory_remove": [],
            "location": None,
            "time_advance": 1,
            "affinity_changes": {},
        },
    }
    return mock_resp


def test_freeform_action_injects_entity_context() -> None:
    """system prompt에 canon_context가 포함되는지 확인."""
    captured_prompts: list[object] = []

    def _fake_generate_json(prompt: object, **kwargs: object) -> MagicMock:
        captured_prompts.append(prompt)
        return _mock_generate_json()

    mock_client = MagicMock()
    mock_client.generate_json.side_effect = _fake_generate_json

    with patch("service.sim.freeform_handler.get_qwen36_27b_q3", return_value=mock_client):
        entities = ExtractedEntities(actor="투르윈", location=None, item=None)
        narrative, delta = freeform_action(
            "투르윈이 2층 입구로 이동",
            rationale=None,
            extracted_entities=entities,
        )

    assert len(captured_prompts) == 1
    prompt = captured_prompts[0]
    assert hasattr(prompt, "system")
    assert "투르윈" in prompt.system  # type: ignore[union-attr]
    assert isinstance(narrative, str)
    assert isinstance(delta, StateDelta)


def test_freeform_action_no_entities_no_context() -> None:
    """entity 없으면 system에 canon_context 블록 없음."""
    captured_prompts: list[object] = []

    def _fake_generate_json(prompt: object, **kwargs: object) -> MagicMock:
        captured_prompts.append(prompt)
        return _mock_generate_json()

    mock_client = MagicMock()
    mock_client.generate_json.side_effect = _fake_generate_json

    with patch("service.sim.freeform_handler.get_qwen36_27b_q3", return_value=mock_client):
        narrative, delta = freeform_action(
            "완전히 새로운 행동",
            rationale=None,
            extracted_entities=None,
        )

    prompt = captured_prompts[0]
    assert hasattr(prompt, "system")
    assert "본문 정합 정보:" not in prompt.system  # type: ignore[union-attr]
