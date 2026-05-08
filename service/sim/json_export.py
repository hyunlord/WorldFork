"""SimResult / SimAnalysis JSON 직렬화 (★ 4차 commit).

본인 본질 (★ 6번 결정 — structured output JSON):
- 시뮬 결과 저장
- 후속 분석 / 비교 본격
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .analyzer import SimAnalysis
from .types import SimResult


def sim_result_to_dict(result: SimResult) -> dict[str, Any]:
    """SimResult → JSON-serializable dict."""
    return {
        "sim_id": result.sim_id,
        "config_summary": result.config_summary,
        "total_turns": result.total_turns,
        "completed_turns": result.completed_turns,
        "end_reason": result.end_reason,
        "final_hp_by_actor": dict(result.final_hp_by_actor),
        "essences_absorbed_by_actor": dict(result.essences_absorbed_by_actor),
        "final_hours_in_dungeon": result.final_hours_in_dungeon,
        "total_player_llm_cost": result.total_player_llm_cost,
        "total_gm_llm_cost": result.total_gm_llm_cost,
        "total_latency_seconds": result.total_latency_seconds,
        "turn_logs": [
            {
                "turn_number": log.turn_number,
                "actor_name": log.actor_name,
                "action": {
                    "action_type": log.action.action_type.value,
                    "actor_name": log.action.actor_name,
                    "target": log.action.target,
                    "rationale": log.action.rationale,
                },
                "success": log.success,
                "message": log.message,
                "side_effects": list(log.side_effects),
                "hp_before": log.hp_before,
                "hp_after": log.hp_after,
                "essence_slots_used": log.essence_slots_used,
                "has_active_light": log.has_active_light,
                "hours_in_dungeon": log.hours_in_dungeon,
            }
            for log in result.turn_logs
        ],
    }


def sim_analysis_to_dict(analysis: SimAnalysis) -> dict[str, Any]:
    """SimAnalysis → JSON-serializable dict."""
    return {
        "sim_id": analysis.sim_id,
        "config_summary": analysis.config_summary,
        "end_reason": analysis.end_reason,
        "completed_turns": analysis.completed_turns,
        "total_turns": analysis.total_turns,
        "completion_rate": analysis.completion_rate,
        "final_hours_in_dungeon": analysis.final_hours_in_dungeon,
        "time_limit_reached": analysis.time_limit_reached,
        "diversity_score": analysis.diversity_score,
        "most_used_action": (
            analysis.most_used_action.value
            if analysis.most_used_action
            else None
        ),
        "action_frequencies": [
            {
                "action_type": f.action_type.value,
                "count": f.count,
                "percentage": f.percentage,
            }
            for f in analysis.action_frequencies
        ],
        "actors": [
            {
                "actor_name": a.actor_name,
                "final_hp": a.final_hp,
                "hp_changes": a.hp_changes,
                "essence_slots_used": a.essence_slots_used,
                "light_active_turns": a.light_active_turns,
                "actions_taken": a.actions_taken,
            }
            for a in analysis.actors
        ],
        "survived_to_end": analysis.survived_to_end,
        "floor_exit_attempted": analysis.floor_exit_attempted,
        "light_management_used": analysis.light_management_used,
        "total_latency_seconds": analysis.total_latency_seconds,
        "total_player_cost_usd": analysis.total_player_cost_usd,
    }


def save_sim_result_json(result: SimResult, path: Path) -> None:
    """SimResult JSON 파일 저장 (★ parent dir 자동 생성)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = sim_result_to_dict(result)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_sim_analysis_json(analysis: SimAnalysis, path: Path) -> None:
    """SimAnalysis JSON 파일 저장 (★ parent dir 자동 생성)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = sim_analysis_to_dict(analysis)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
