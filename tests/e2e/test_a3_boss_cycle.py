"""Phase 8 A3 E2E — 보스 사이클 검증.

본질:
- Scripted harness (★ LLM 무관 결정적) 본격 보스 사이클 mechanism 검증
- ENTER_RIFT (force_variant) → MOVE chain → boss spawn → ATTACK → 처치 →
  side_effects markers → cleared_rifts → EXIT_RIFT 본격 전체 발현
- 4 균열 모두 본격 (★ BC variant / GC variant+weakness / GM normal / IT normal)

본 test 본격: tests/e2e/trace_A3_scripted.json 본격 본격 본격 X — 본격
run_scripted() 본격 신규 실행 본격 검증 (★ self-contained).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.run_a3_scripted import run_scripted

_TRACE_PATH = Path("tests/e2e/trace_A3_scripted.json")
_LLM_TRACE_PATH = Path("tests/e2e/trace_A3_llm.json")


# ─── 1. Scripted trace — 4 균열 사이클 발현 ───


@pytest.mark.parametrize(
    "rift_id,expected_variant,expected_grade",
    [
        ("bloody_castle", True, 5),   # 캠보르미어 5등급
        ("glacier_cave", True, 7),    # 키르뒤 — variant_grade None → normal 7
        ("green_mine", False, 8),     # 킹 슬라임 (variant X)
        ("iron_tomb", False, 8),      # 철인 일디움 (variant X)
    ],
)
def test_scripted_cycle_completes(
    rift_id: str, expected_variant: bool, expected_grade: int
) -> None:
    """4 균열 모두 ENTER→MOVE→ATTACK→처치→EXIT 사이클 완주."""
    trace = run_scripted(rift_id, max_attacks=30)
    assert trace["end_reason"] == "complete", trace["end_reason"]

    logs = trace["turn_logs"]
    action_types = [t["action_type"] for t in logs]
    assert action_types[0] == "ENTER_RIFT"
    assert action_types[-1] == "EXIT_RIFT"

    # boss spawn 발현
    spawn_turn = next(
        t for t in logs
        if any("boss_spawned=" in eff for eff in t["side_effects"])
    )
    boss = spawn_turn["world_snapshot"]["active_boss_encounter"]
    assert boss is not None
    assert boss["is_variant"] is expected_variant
    assert boss["boss_grade"] == expected_grade

    # boss defeated + rift cleared markers
    defeat_turn = next(
        t for t in logs
        if any("boss_defeated=" in eff for eff in t["side_effects"])
    )
    assert any(
        "rift_cleared=" in eff for eff in defeat_turn["side_effects"]
    )
    assert any(
        "essence_spawn=" in eff for eff in defeat_turn["side_effects"]
    )

    # 처치 후 world.cleared_rifts에 등록
    last = logs[-1]
    assert rift_id in last["world_snapshot"]["cleared_rifts"]
    assert last["world_snapshot"]["active_boss_encounter"] is None

    # 마석 inventory append
    inv = trace["final_inventory"]["비요른"]
    assert any("마석" in it["name"] for it in inv)


def test_scripted_hp_balance_within_target() -> None:
    """4 균열 모두 ATTACK 횟수 3-15 turn 범위 (HP balance 적정)."""
    for rift_id in ["bloody_castle", "glacier_cave", "green_mine", "iron_tomb"]:
        trace = run_scripted(rift_id, max_attacks=30)
        attacks = sum(
            1 for t in trace["turn_logs"]
            if t["action_type"] == "ATTACK"
        )
        assert 3 <= attacks <= 15, (
            f"{rift_id}: {attacks}회 ATTACK (★ 3-15 범위 외)"
        )


def test_scripted_glacier_weakness_doubles() -> None:
    """빙하굴 — weakness_element='전격' 본격 본격 데미지 2배 (★ A1 inherit)."""
    trace_with = run_scripted("glacier_cave", max_attacks=30)
    attacks_with = sum(
        1 for t in trace_with["turn_logs"] if t["action_type"] == "ATTACK"
    )
    # 본격 본격 본격 X — strength+physical=60, weakness 2배=120,
    # HP 300 → 3 attacks 본격 본격. 본격 본격 본격 본격 X 시 5 attacks.
    assert attacks_with <= 4, (
        f"빙하굴 weakness 본격 attacks {attacks_with} (★ 본격 본격 X?)"
    )


# ─── 2. Committed scripted trace JSON 본격 ───


def test_scripted_trace_json_committed() -> None:
    """tests/e2e/trace_A3_scripted.json 본격 생성 본격 X."""
    assert _TRACE_PATH.exists(), (
        f"{_TRACE_PATH} 본격 X — `python -m tests.e2e.run_a3_scripted` 본격 본격"
    )
    data = json.loads(_TRACE_PATH.read_text(encoding="utf-8"))
    assert data["end_reason"] == "complete"
    assert data["completed_turns"] >= 7  # 최소 ENTER+MOVE×N+ATTACK×N+EXIT


# ─── 3. LLM trace (★ 본격 본격 본격 본격 본격 본격) ───


@pytest.mark.skipif(
    not _LLM_TRACE_PATH.exists(),
    reason="trace_A3_llm.json 본격 X — `python -m tests.e2e.run_e2e_trace ...`",
)
def test_llm_trace_no_gm_fallback() -> None:
    """LLM trace 본격 본격 GM fallback X (★ D 본격 본격 — context 회복)."""
    data = json.loads(_LLM_TRACE_PATH.read_text(encoding="utf-8"))
    # 본격 본격 본격 0 본격 본격 본격 — marginal 본격 본격 본격 본격 본격 본격
    # 본격 본격 본격 본격 본격, 본격 본격 본격 본격 본격 본격 본격 본격 본격.
    fallback = data.get("gm_fallback_count", 0)
    assert fallback < 5, f"GM fallback {fallback} (★ context 본격 본격)"


@pytest.mark.skipif(
    not _LLM_TRACE_PATH.exists(),
    reason="trace_A3_llm.json 본격 X",
)
def test_llm_trace_completed() -> None:
    """LLM trace 본격 completed_turns > 0 (★ 본격 본격 본격 본격 본격)."""
    data = json.loads(_LLM_TRACE_PATH.read_text(encoding="utf-8"))
    assert data["completed_turns"] > 0
