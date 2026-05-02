"""Complete / Save (★ 자료 2.2 Stage 8).

게임 종료 시 GameState + Plan + 평가 저장.
W3에서 SQL로 확장 예정 (지금은 JSON only).

저장 경로: runs/playthrough/{save_id}.json
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from service.game.state import GameState
from service.pipeline.types import Plan

_DEFAULT_SAVE_DIR = Path("runs/playthrough")


def summarize_session(
    plan: Plan,
    state: GameState,
    fun_rating: int | None = None,
    findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """세션 요약 dict 생성 (저장 전 단계)."""
    return {
        "save_id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(UTC).isoformat(),
        "work_name": plan.work_name,
        "scenario_id": state.scenario_id,
        "turns_completed": state.turn,
        "total_cost_usd": round(state.total_cost_usd(), 6),
        "avg_latency_ms": round(state.avg_latency_ms(), 1),
        "fun_rating": fun_rating,
        "findings": findings or [],
        "plan": plan.to_dict(),
        "history": [asdict(t) for t in state.history],
    }


def save_session(
    plan: Plan,
    state: GameState,
    fun_rating: int | None = None,
    findings: list[dict[str, Any]] | None = None,
    save_dir: Path | None = None,
) -> Path:
    """세션 저장 → JSON 파일 경로 반환.

    Args:
        plan: 게임 플랜
        state: 게임 진행 상태
        fun_rating: 사용자 평가 (1-5, None 허용)
        findings: 발견 이슈 목록
        save_dir: 저장 디렉토리 (기본 runs/playthrough/)

    Returns:
        저장된 파일 Path
    """
    target_dir = save_dir or _DEFAULT_SAVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    summary = summarize_session(plan, state, fun_rating, findings)
    save_id = summary["save_id"]
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{save_id}.json"
    save_path = target_dir / filename

    save_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return save_path
