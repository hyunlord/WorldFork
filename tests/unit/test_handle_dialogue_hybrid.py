"""handle_dialogue hybrid 분기 검증 (I-E1) — mock 27B."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from service.canon.context import clear_entity_index, set_entity_index
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Character
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_dialogue


def _ctx(user_input: str, npc_name: str = "셰인") -> ActionContext:
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="1층 입구",
        user_input=user_input,
        encounters=[{"name": npc_name, "hostile": False}],
    )


def _facts_with_npc() -> CanonFacts:
    return CanonFacts(
        essences=[],
        characters=[
            Character(
                name="셰인",
                role="동료",
                race="인간",
                background="전직 기사 출신. 과거 왕국 근위대에서 복무했다.",
            ),
        ],
        locations=[],
        races=[],
        mechanisms=[],
    )


@pytest.fixture(autouse=True)
def _index() -> object:
    set_entity_index(EntityIndex(_facts_with_npc()))
    yield
    clear_entity_index()


def test_short_greeting_uses_template() -> None:
    """짧은 인사 → template narrative, 27B 미호출."""
    with patch("service.sim.action_handlers.asyncio.to_thread") as mock_thread:
        result = asyncio.run(
            handle_dialogue(_ctx("인사한다"))
        )
    mock_thread.assert_not_called()
    assert "짧은 인사가 오고 갔다" in result.narrative
    assert "셰인" in result.narrative


def test_template_includes_canon_role() -> None:
    """template path에서 canon role 포함."""
    result = asyncio.run(
        handle_dialogue(_ctx("안녕"))
    )
    assert "동료" in result.narrative


def test_deep_dialogue_calls_27b() -> None:
    """깊은 대화 keyword → asyncio.to_thread(compose_dialogue_narrative) 호출."""
    mock_narrative = (
        "셰인은 조용히 입을 열었다."
        " \"왕국의 균열은 생각보다 깊습니다.\" 그의 눈빛이 무거웠다."
    )
    with patch("service.sim.action_handlers.asyncio.to_thread") as mock_thread:
        mock_thread.return_value = mock_narrative
        result = asyncio.run(
            handle_dialogue(_ctx("던전 소식을 물어본다"))
        )
    mock_thread.assert_called_once()
    assert result.narrative == mock_narrative


def test_deep_dialogue_fallback_on_empty_27b() -> None:
    """27B 반환 빈 문자열 → fallback template."""
    with patch("service.sim.action_handlers.asyncio.to_thread") as mock_thread:
        mock_thread.return_value = ""
        result = asyncio.run(
            handle_dialogue(_ctx("최근 상황을 이야기해달라"))
        )
    assert "셰인" in result.narrative
    assert result.narrative != ""


def test_no_npc_returns_fail() -> None:
    """encounters 없음 → success=False."""
    ctx = ActionContext(
        current_hp=100, max_hp=100, inventory=[], location="1층 입구",
        user_input="인사한다", encounters=[],
    )
    result = asyncio.run(handle_dialogue(ctx))
    assert result.success is False
    assert result.fail_reason == "no_npc"


def test_affinity_increases() -> None:
    """dialogue 성공 → affinity +1."""
    result = asyncio.run(
        handle_dialogue(_ctx("인사한다"))
    )
    assert result.affinity_changes.get("셰인") == 1


def test_no_index_template_fallback() -> None:
    """entity_index=None → canon lookup 없이 template."""
    clear_entity_index()
    result = asyncio.run(
        handle_dialogue(_ctx("인사한다"))
    )
    assert "셰인" in result.narrative
    assert result.success is True
