"""Tier 1.5 D2: HookManager 12 이벤트 시스템 테스트."""

from core.harness.hooks import (
    HookContext,
    HookEvent,
    HookManager,
    _builtin_external_pkg_check,
    _builtin_post_code_blocking,
    _builtin_verify_threshold,
)


class TestHookEvent:
    def test_all_12_events_defined(self) -> None:
        events = list(HookEvent)
        assert len(events) == 12

    def test_event_values(self) -> None:
        assert HookEvent.TASK_START == "task_start"
        assert HookEvent.POST_CODE == "post_code"
        assert HookEvent.TASK_FAIL == "task_fail"


class TestHookContext:
    def test_default_no_abort(self) -> None:
        ctx = HookContext(event=HookEvent.TASK_START)
        assert not ctx.abort
        assert ctx.abort_reason == ""

    def test_set_abort(self) -> None:
        ctx = HookContext(event=HookEvent.POST_CODE)
        ctx.set_abort("bad pattern")
        assert ctx.abort
        assert "bad pattern" in ctx.abort_reason

    def test_payload_default_empty(self) -> None:
        ctx = HookContext(event=HookEvent.PRE_PLAN)
        assert ctx.payload == {}


class TestBuiltinPostCodeBlocking:
    def test_critical_pattern_aborts(self) -> None:
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "+result.score = 95\n"
        )
        ctx = HookContext(event=HookEvent.POST_CODE, payload={"diff": diff})
        _builtin_post_code_blocking(ctx)
        assert ctx.abort

    def test_clean_diff_no_abort(self) -> None:
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "+result.score = llm_response.score\n"
        )
        ctx = HookContext(event=HookEvent.POST_CODE, payload={"diff": diff})
        _builtin_post_code_blocking(ctx)
        assert not ctx.abort

    def test_empty_diff_no_abort(self) -> None:
        ctx = HookContext(event=HookEvent.POST_CODE, payload={"diff": ""})
        _builtin_post_code_blocking(ctx)
        assert not ctx.abort


class TestBuiltinExternalPkgCheck:
    def test_unapproved_pkg_aborts(self) -> None:
        diff = (
            "diff --git a/pyproject.toml b/pyproject.toml\n"
            '+    "requests>=2.31",\n'
        )
        ctx = HookContext(event=HookEvent.POST_CODE, payload={"diff": diff})
        _builtin_external_pkg_check(ctx)
        assert ctx.abort

    def test_whitelisted_pkg_ok(self) -> None:
        diff = (
            "diff --git a/pyproject.toml b/pyproject.toml\n"
            '+    "anthropic>=0.40",\n'
        )
        ctx = HookContext(event=HookEvent.POST_CODE, payload={"diff": diff})
        _builtin_external_pkg_check(ctx)
        assert not ctx.abort

    def test_no_pyproject_no_abort(self) -> None:
        diff = "diff --git a/foo.py b/foo.py\n+x = 1\n"
        ctx = HookContext(event=HookEvent.POST_CODE, payload={"diff": diff})
        _builtin_external_pkg_check(ctx)
        assert not ctx.abort


class TestBuiltinVerifyThreshold:
    def test_below_threshold_aborts(self) -> None:
        ctx = HookContext(
            event=HookEvent.POST_VERIFY,
            payload={"score": 80, "threshold": 95},
        )
        _builtin_verify_threshold(ctx)
        assert ctx.abort

    def test_at_threshold_passes(self) -> None:
        ctx = HookContext(
            event=HookEvent.POST_VERIFY,
            payload={"score": 95, "threshold": 95},
        )
        _builtin_verify_threshold(ctx)
        assert not ctx.abort

    def test_no_score_no_abort(self) -> None:
        ctx = HookContext(event=HookEvent.POST_VERIFY, payload={})
        _builtin_verify_threshold(ctx)
        assert not ctx.abort


class TestHookManager:
    def test_builtin_hooks_registered(self) -> None:
        manager = HookManager()
        post_code_hooks = manager.hooks_for(HookEvent.POST_CODE)
        names = [h.name for h in post_code_hooks]
        assert "builtin_post_code_blocking" in names
        assert "builtin_external_pkg_check" in names

    def test_register_custom_hook(self) -> None:
        manager = HookManager()
        called: list[str] = []

        def my_hook(ctx: HookContext) -> None:
            called.append("triggered")

        manager.register(HookEvent.TASK_START, my_hook, name="test_hook")
        manager.trigger(HookEvent.TASK_START)
        assert "triggered" in called

    def test_trigger_abort_stops_chain(self) -> None:
        manager = HookManager()
        log: list[str] = []

        def hook_a(ctx: HookContext) -> None:
            ctx.set_abort("stop here")
            log.append("A")

        def hook_b(ctx: HookContext) -> None:
            log.append("B")

        manager.register(HookEvent.PRE_CODE, hook_a, priority=10)
        manager.register(HookEvent.PRE_CODE, hook_b, priority=20)
        ctx = manager.trigger(HookEvent.PRE_CODE)
        assert ctx.abort
        assert "A" in log
        assert "B" not in log

    def test_priority_order(self) -> None:
        manager = HookManager()
        order: list[int] = []

        manager.register(HookEvent.ON_RETRY, lambda c: order.append(30), priority=30)
        manager.register(HookEvent.ON_RETRY, lambda c: order.append(10), priority=10)
        manager.register(HookEvent.ON_RETRY, lambda c: order.append(20), priority=20)
        manager.trigger(HookEvent.ON_RETRY)
        assert order == [10, 20, 30]

    def test_trigger_returns_context(self) -> None:
        manager = HookManager()
        ctx = manager.trigger(HookEvent.TASK_COMPLETE, payload={"result": "ok"})
        assert isinstance(ctx, HookContext)
        assert ctx.event == HookEvent.TASK_COMPLETE
        assert ctx.payload["result"] == "ok"
