"""Hook 이벤트 시스템 — Tier 1.5 D2 (★ 자료 HARNESS_LAYER1_DEV 5장).

12개 이벤트, priority merge (built-in < global < project),
abort 지원, LLM 호출 0회 (Mechanical only).
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class HookEvent(StrEnum):
    """12개 표준 Hook 이벤트."""

    TASK_START = "task_start"
    PRE_PLAN = "pre_plan"
    POST_PLAN = "post_plan"
    PLAN_REVIEW = "plan_review"
    PRE_CODE = "pre_code"
    POST_CODE = "post_code"        # 빌드 게이트 (anti-pattern + build check)
    PRE_VERIFY = "pre_verify"
    POST_VERIFY = "post_verify"
    ON_RETRY = "on_retry"
    ON_REPLAN = "on_replan"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"


@dataclass
class HookContext:
    """Hook 실행 컨텍스트."""

    event: HookEvent
    payload: dict[str, Any] = field(default_factory=dict)
    abort: bool = False
    abort_reason: str = ""

    def set_abort(self, reason: str) -> None:
        self.abort = True
        self.abort_reason = reason


HookFn = Callable[[HookContext], None]


@dataclass
class HookDefinition:
    """Hook 정의."""

    event: HookEvent
    name: str
    fn: HookFn
    priority: int = 50  # 낮을수록 먼저 실행; built-in=10, global=50, project=90


# ============================================================
# Built-in Hooks
# ============================================================

def _builtin_post_code_blocking(ctx: HookContext) -> None:
    """POST_CODE: anti-pattern 검출 → abort."""
    from core.verify.anti_pattern_check import check_anti_patterns

    diff = ctx.payload.get("diff", "")
    if not diff:
        return

    matches = check_anti_patterns(diff)
    critical = [m for m in matches if m.anti_pattern.severity == "critical"]
    if critical:
        ids = ", ".join(m.anti_pattern.id for m in critical)
        ctx.set_abort(f"Critical anti-pattern detected: {ids}")


def _builtin_external_pkg_check(ctx: HookContext) -> None:
    """POST_CODE: pyproject.toml 외부 패키지 추가 감지."""
    diff = ctx.payload.get("diff", "")
    if not diff or "pyproject.toml" not in diff:
        return

    pattern = re.compile(
        r"^\+\s*['\"](?!anthropic|httpx|pydantic|pyyaml|"
        r"python-dotenv|jupyterlab|huggingface-hub|"
        r"pytest|pytest-asyncio|pytest-cov|pytest-mock|"
        r"hypothesis|ruff|mypy|types-PyYAML|"
        r"openai|google-generativeai|sqlalchemy|"
        r"llama-cpp-python|streamlit)"
        r"[a-zA-Z][a-zA-Z0-9_.-]*(?:>=|<=|==|~=|!=|>|<|\[)",
        re.MULTILINE,
    )
    if pattern.search(diff):
        ctx.set_abort("Unapproved external package addition detected in pyproject.toml")


def _builtin_verify_threshold(ctx: HookContext) -> None:
    """POST_VERIFY: 점수 임계값 미달 시 abort."""
    score = ctx.payload.get("score")
    threshold = ctx.payload.get("threshold", 95)
    if score is not None and score < threshold:
        ctx.set_abort(f"Verify score {score} < threshold {threshold}")


_BUILTIN_HOOKS: list[HookDefinition] = [
    HookDefinition(
        event=HookEvent.POST_CODE,
        name="builtin_post_code_blocking",
        fn=_builtin_post_code_blocking,
        priority=10,
    ),
    HookDefinition(
        event=HookEvent.POST_CODE,
        name="builtin_external_pkg_check",
        fn=_builtin_external_pkg_check,
        priority=10,
    ),
    HookDefinition(
        event=HookEvent.POST_VERIFY,
        name="builtin_verify_threshold",
        fn=_builtin_verify_threshold,
        priority=10,
    ),
]


# ============================================================
# HookManager
# ============================================================

_GLOBAL_HOOKS_DIR = Path.home() / ".autodev"
_PROJECT_HOOKS_FILE = Path(".autodev") / "hooks.json"


def _load_json_hooks(path: Path, priority: int) -> list[HookDefinition]:
    """JSON hooks 파일 → HookDefinition 리스트 (shell 커맨드 실행형)."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    hooks: list[HookDefinition] = []
    for event_str, entries in data.get("hooks", {}).items():
        try:
            event = HookEvent(event_str)
        except ValueError:
            continue

        if isinstance(entries, list):
            for entry in entries:
                cmd = entry.get("cmd") if isinstance(entry, dict) else None
                raw_name = entry.get("name") if isinstance(entry, dict) else None
                name = raw_name or f"{event_str}_cmd"
                if cmd:
                    hooks.append(
                        HookDefinition(
                            event=event,
                            name=name,
                            fn=_make_shell_fn(cmd),
                            priority=priority,
                        )
                    )
    return hooks


def _make_shell_fn(cmd: str) -> HookFn:
    def shell_fn(ctx: HookContext) -> None:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            ctx.set_abort(f"Shell hook failed ({cmd!r}): {result.stderr[:200]}")

    return shell_fn


class HookManager:
    """Hook 등록 + 실행 관리자.

    priority merge: built-in(10) < global(50) < project(90)
    같은 priority → 등록 순서 유지.
    """

    def __init__(self) -> None:
        self._hooks: list[HookDefinition] = []
        self._load_defaults()

    def _load_defaults(self) -> None:
        # 1. built-in
        for h in _BUILTIN_HOOKS:
            self._hooks.append(h)

        # 2. global (~/.autodev/hooks.json)
        global_path = _GLOBAL_HOOKS_DIR / "hooks.json"
        for h in _load_json_hooks(global_path, priority=50):
            self._hooks.append(h)

        # 3. project (.autodev/hooks.json)
        for h in _load_json_hooks(_PROJECT_HOOKS_FILE, priority=90):
            self._hooks.append(h)

    def register(
        self,
        event: HookEvent,
        fn: HookFn,
        name: str = "",
        priority: int = 50,
    ) -> None:
        """런타임 Hook 등록."""
        self._hooks.append(
            HookDefinition(
                event=event,
                name=name or fn.__name__,
                fn=fn,
                priority=priority,
            )
        )

    def trigger(self, event: HookEvent, payload: dict[str, Any] | None = None) -> HookContext:
        """이벤트 발생 → 해당 Hook 순서대로 실행.

        abort 발생 시 이후 Hook 건너뜀.
        """
        ctx = HookContext(event=event, payload=payload or {})
        relevant = sorted(
            (h for h in self._hooks if h.event == event),
            key=lambda h: h.priority,
        )
        for hook in relevant:
            if ctx.abort:
                break
            hook.fn(ctx)
        return ctx

    def hooks_for(self, event: HookEvent) -> list[HookDefinition]:
        """이벤트에 등록된 Hook 목록 (priority 정렬)."""
        return sorted(
            (h for h in self._hooks if h.event == event),
            key=lambda h: h.priority,
        )
