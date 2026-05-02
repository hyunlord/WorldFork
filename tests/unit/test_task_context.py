"""Tier 1.5 D3 작업 4: TaskContext 테스트."""

from core.harness.task_context import TaskContext, TaskStatus


class TestTaskContext:
    def test_default_init(self) -> None:
        task = TaskContext(description="test")
        assert task.task_id.startswith("task_")
        assert task.status == TaskStatus.INITIALIZED
        assert task.coding_attempts_count == 0
        assert task.verify_attempts_count == 0

    def test_log_code_attempt(self) -> None:
        task = TaskContext()
        task.log_code_attempt(True, {"file": "x.py"})
        assert task.coding_attempts_count == 1
        assert task.code_attempts[0]["succeeded"] is True
        assert task.code_attempts[0]["attempt_n"] == 1

    def test_log_verify_attempt(self) -> None:
        task = TaskContext()
        task.log_verify_attempt(95, "pass")
        assert task.verify_attempts_count == 1
        assert task.verify_attempts[0]["score"] == 95
        assert task.verify_attempts[0]["verdict"] == "pass"

    def test_mark_completed_success(self) -> None:
        task = TaskContext()
        task.mark_completed(success=True)
        assert task.status == TaskStatus.COMPLETED
        assert task.success
        assert task.completed_at is not None

    def test_mark_completed_failure(self) -> None:
        task = TaskContext()
        task.mark_completed(success=False)
        assert task.status == TaskStatus.FAILED
        assert not task.success

    def test_to_dict_roundtrip(self) -> None:
        task = TaskContext(description="x")
        task.log_code_attempt(True)
        task.log_verify_attempt(80, "warn")
        d = task.to_dict()
        assert d["description"] == "x"
        assert len(d["code_attempts"]) == 1
        assert len(d["verify_attempts"]) == 1
        assert "elapsed_sec" in d
        assert d["status"] == "initialized"

    def test_elapsed_sec_positive(self) -> None:
        task = TaskContext()
        assert task.elapsed_sec >= 0.0

    def test_multiple_code_attempts_numbered(self) -> None:
        task = TaskContext()
        task.log_code_attempt(True)
        task.log_code_attempt(False)
        task.log_code_attempt(True)
        assert task.coding_attempts_count == 3
        assert task.code_attempts[2]["attempt_n"] == 3
