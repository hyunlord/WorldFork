"""TaskContext — 작업 단위 추적 (★ 본인 자료 AutoDev 정합).

흐름:
  Initialized → Planning → Coding → Verifying → Completed/Failed
  Retrying / Replanning 중간 상태 가능.

12 이벤트와 통합:
  TaskStart 시 TaskContext 생성
  각 단계 hook 호출
  TaskComplete / TaskFail 시 종료
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TaskStatus(StrEnum):
    """작업 상태 (9종)."""

    INITIALIZED = "initialized"
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    CODING = "coding"
    VERIFYING = "verifying"
    RETRYING = "retrying"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskContext:
    """작업 단위 추적 (★ 본인 자료 AutoDev 정신).

    매 작업마다 생성되어 12 이벤트 흐름 통합.
    """

    task_id: str = field(default_factory=lambda: f"task_{uuid4().hex[:8]}")
    description: str = ""
    status: TaskStatus = TaskStatus.INITIALIZED
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    # 흐름 추적
    plan: dict[str, Any] | None = None
    code_attempts: list[dict[str, Any]] = field(default_factory=list)
    verify_attempts: list[dict[str, Any]] = field(default_factory=list)
    replan_count: int = 0

    # Layer
    layer: str = "1"  # "1" or "2"

    # 결과
    success: bool = False
    error: str | None = None

    @property
    def elapsed_sec(self) -> float:
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def coding_attempts_count(self) -> int:
        return len(self.code_attempts)

    @property
    def verify_attempts_count(self) -> int:
        return len(self.verify_attempts)

    def log_code_attempt(
        self,
        succeeded: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code_attempts.append({
            "attempt_n": len(self.code_attempts) + 1,
            "succeeded": succeeded,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        })

    def log_verify_attempt(
        self,
        score: int,
        verdict: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.verify_attempts.append({
            "attempt_n": len(self.verify_attempts) + 1,
            "score": score,
            "verdict": verdict,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        })

    def mark_completed(self, success: bool = True) -> None:
        self.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.success = success

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화 호환."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "plan": self.plan,
            "code_attempts": self.code_attempts,
            "verify_attempts": self.verify_attempts,
            "replan_count": self.replan_count,
            "layer": self.layer,
            "success": self.success,
            "error": self.error,
            "elapsed_sec": self.elapsed_sec,
        }
