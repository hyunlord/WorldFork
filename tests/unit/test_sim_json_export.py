"""SimResult / SimAnalysis JSON 직렬화 테스트 (★ 4차 commit)."""

from __future__ import annotations

import json
from pathlib import Path

from service.sim.analyzer import analyze_sim_result
from service.sim.json_export import (
    save_sim_analysis_json,
    save_sim_result_json,
    sim_analysis_to_dict,
    sim_result_to_dict,
)
from service.sim.types import (
    PlayerAction,
    PlayerActionType,
    SimResult,
    TurnLog,
)


def _mk_result() -> SimResult:
    return SimResult(
        sim_id="t",
        config_summary="test",
        total_turns=2,
        completed_turns=2,
        end_reason="max_turns",
        turn_logs=[
            TurnLog(
                turn_number=1,
                actor_name="비요른",
                action=PlayerAction(
                    action_type=PlayerActionType.ACTIVATE_LIGHT,
                    actor_name="비요른",
                    target="횃불",
                    rationale="어둠 본질",
                ),
                success=True,
                message="횃불 활성",
                side_effects=["가시거리 10m"],
                hp_before=150,
                hp_after=150,
                has_active_light=True,
                hours_in_dungeon=0,
            ),
        ],
        final_hp_by_actor={"비요른": 150},
        essences_absorbed_by_actor={"비요른": 0},
        final_hours_in_dungeon=2,
    )


def test_sim_result_to_dict_basic() -> None:
    r = _mk_result()
    d = sim_result_to_dict(r)

    assert d["sim_id"] == "t"
    assert d["completed_turns"] == 2
    assert d["end_reason"] == "max_turns"
    assert d["final_hp_by_actor"]["비요른"] == 150
    assert len(d["turn_logs"]) == 1

    log = d["turn_logs"][0]
    assert log["actor_name"] == "비요른"
    assert log["action"]["action_type"] == "activate_light"
    assert log["action"]["target"] == "횃불"
    assert log["has_active_light"]


def test_sim_result_json_roundtrip() -> None:
    """JSON → dict → JSON 본격."""
    r = _mk_result()
    d = sim_result_to_dict(r)

    json_text = json.dumps(d, ensure_ascii=False)
    parsed = json.loads(json_text)

    assert parsed["sim_id"] == "t"
    assert parsed["turn_logs"][0]["action"]["action_type"] == "activate_light"


def test_save_sim_result_json(tmp_path: Path) -> None:
    r = _mk_result()
    path = tmp_path / "result.json"
    save_sim_result_json(r, path)

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["sim_id"] == "t"


def test_sim_analysis_to_dict() -> None:
    r = _mk_result()
    a = analyze_sim_result(r)
    d = sim_analysis_to_dict(a)

    assert d["sim_id"] == "t"
    assert "completion_rate" in d
    assert "action_frequencies" in d
    assert "actors" in d
    assert d["light_management_used"]


def test_save_sim_analysis_json(tmp_path: Path) -> None:
    r = _mk_result()
    a = analyze_sim_result(r)
    path = tmp_path / "analysis.json"
    save_sim_analysis_json(a, path)

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["sim_id"] == "t"
    assert data["light_management_used"]


def test_save_creates_parent_dir(tmp_path: Path) -> None:
    """parent dir 자동 생성."""
    r = _mk_result()
    path = tmp_path / "nested" / "deep" / "result.json"
    save_sim_result_json(r, path)

    assert path.exists()
