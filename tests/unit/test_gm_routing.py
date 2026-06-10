"""서빙 3단계 — 하이브리드 9B/27B GM 라우팅 결정 (결정적 단위 테스트)."""

from __future__ import annotations

import pytest

from service.sim.gm_narrator import gm_model_label, is_pivotal_gm
from service.sim.types import PlayerActionType


def test_pivotal_phase_declaration_27b() -> None:
    # 성년식 첫인상(선언) = pivotal → 27B
    assert is_pivotal_gm(PlayerActionType.DIALOGUE, "declaration", False) is True


def test_pivotal_phase_weapon_choice_27b() -> None:
    assert is_pivotal_gm(PlayerActionType.DIALOGUE, "weapon_choice", False) is True


def test_combat_action_27b() -> None:
    # 전투 action = pivotal → 27B (중대 순간)
    assert is_pivotal_gm(PlayerActionType.ATTACK, "dungeon", False) is True
    assert is_pivotal_gm(PlayerActionType.FLEE, "dungeon", False) is True


def test_hostile_present_27b() -> None:
    # 적대 조우 중이면 어떤 행동이든 27B (애매하면 27B)
    assert is_pivotal_gm(PlayerActionType.EXPLORE, "dungeon", True) is True


def test_simple_dungeon_action_9b() -> None:
    # 순수 비전투 단순 행동(탐색/이동/대화) → 9B (빠름)
    assert is_pivotal_gm(PlayerActionType.EXPLORE, "dungeon", False) is False
    assert is_pivotal_gm(PlayerActionType.MOVE, "dungeon", False) is False
    assert is_pivotal_gm(PlayerActionType.DIALOGUE, "departure", False) is False


def test_dungeon_entry_9b() -> None:
    # 던전 진입(입성 전환)은 단순 서사 → 9B
    assert is_pivotal_gm(PlayerActionType.ENTER_DUNGEON, "departure", False) is False


def test_model_label(monkeypatch: pytest.MonkeyPatch) -> None:
    # 기본: pivotal → Gemma 4(품질·~15 t/s), 단순 → 원본 9B(빠른 tier)
    monkeypatch.delenv("GEMMA_GM", raising=False)
    assert gm_model_label(True) == "gemma"
    assert gm_model_label(False) == "9b"
    # GEMMA_GM=0 폴백: pivotal → 27B
    monkeypatch.setenv("GEMMA_GM", "0")
    assert gm_model_label(True) == "27b"
    assert gm_model_label(False) == "9b"
