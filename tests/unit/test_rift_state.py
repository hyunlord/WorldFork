"""audit-3 commit 1 — rift state 추적 단위 테스트."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from service.persistence.sqlite_store import SessionRow
from service.sim.action_context import ActionContext, ActionResult
from service.sim.session_manager import SessionState, _from_row, _to_row

# ── SessionState default fields ────────────────────────────────────────────


class TestSessionStateRiftDefaults(unittest.TestCase):
    def _make_state(self) -> SessionState:
        import time
        now = time.time()
        return SessionState(
            session_id="s1",
            current_hp=100,
            max_hp=100,
            inventory=[],
            location="1층 입구",
            encounters=[],
            turn_count=0,
            created_at=now,
            last_active=now,
        )

    def test_default_rift_id_is_none(self) -> None:
        s = self._make_state()
        self.assertIsNone(s.rift_id)

    def test_default_rift_sub_area_is_none(self) -> None:
        s = self._make_state()
        self.assertIsNone(s.rift_sub_area)

    def test_default_rift_is_variant_is_false(self) -> None:
        s = self._make_state()
        self.assertFalse(s.rift_is_variant)


# ── SessionRow round-trip ───────────────────────────────────────────────────


class TestSessionRowRiftRoundTrip(unittest.TestCase):
    def _make_row(self, **kwargs: object) -> SessionRow:
        return SessionRow(
            session_id="r1",
            created_at=0.0,
            last_active=0.0,
            current_hp=100,
            max_hp=100,
            inventory=[],
            location="1층 입구",
            turn_count=0,
            **kwargs,  # type: ignore[arg-type]
        )

    def test_rift_fields_serialise_via_to_row(self) -> None:
        import time
        now = time.time()
        state = SessionState(
            session_id="s2",
            current_hp=80,
            max_hp=100,
            inventory=[],
            location="핏빛성채 (균열 내부)",
            encounters=[],
            turn_count=3,
            created_at=now,
            last_active=now,
            rift_id="bloody_castle",
            rift_sub_area="bc_ch1",
            rift_is_variant=True,
        )
        row = _to_row(state)
        self.assertEqual(row.rift_id, "bloody_castle")
        self.assertEqual(row.rift_sub_area, "bc_ch1")
        self.assertTrue(row.rift_is_variant)

    def test_rift_fields_deserialise_via_from_row(self) -> None:
        row = self._make_row(
            rift_id="glacier_cave",
            rift_sub_area="gc_ch2",
            rift_is_variant=False,
        )
        state = _from_row(row)
        self.assertEqual(state.rift_id, "glacier_cave")
        self.assertEqual(state.rift_sub_area, "gc_ch2")
        self.assertFalse(state.rift_is_variant)

    def test_rift_fields_default_to_none_false(self) -> None:
        row = self._make_row()
        state = _from_row(row)
        self.assertIsNone(state.rift_id)
        self.assertIsNone(state.rift_sub_area)
        self.assertFalse(state.rift_is_variant)


# ── ActionResult rift_transition ───────────────────────────────────────────


class TestActionResultRiftTransition(unittest.TestCase):
    def test_default_rift_transition_is_none(self) -> None:
        r = ActionResult(narrative="test")
        self.assertIsNone(r.rift_transition)

    def test_enter_transition_payload(self) -> None:
        r = ActionResult(
            narrative="균열 진입",
            rift_transition={
                "action": "enter",
                "rift_id": "bloody_castle",
                "rift_sub_area": "bc_ch1",
                "is_variant": False,
            },
        )
        assert r.rift_transition is not None
        self.assertEqual(r.rift_transition["action"], "enter")
        self.assertEqual(r.rift_transition["rift_id"], "bloody_castle")

    def test_exit_transition_payload(self) -> None:
        r = ActionResult(
            narrative="균열 탈출",
            rift_transition={"action": "exit"},
        )
        assert r.rift_transition is not None
        self.assertEqual(r.rift_transition["action"], "exit")


# ── apply_result rift_transition 처리 ──────────────────────────────────────


class TestApplyResultRiftTransition(unittest.TestCase):
    def _make_manager(self) -> object:
        from service.sim.session_manager import SessionManager
        store = MagicMock()
        store.save_session = MagicMock()
        store.save_turn = MagicMock()
        store.load_session = MagicMock(return_value=None)
        return SessionManager(store)

    def _make_state(self) -> SessionState:
        import time
        now = time.time()
        return SessionState(
            session_id="s3",
            current_hp=100,
            max_hp=100,
            inventory=[],
            location="1층 핏빛성채",
            encounters=[],
            turn_count=0,
            created_at=now,
            last_active=now,
        )

    def test_enter_sets_rift_fields(self) -> None:
        mgr: object = self._make_manager()
        state = self._make_state()

        from service.sim.session_manager import SessionManager
        assert isinstance(mgr, SessionManager)
        mgr._cache["s3"] = state  # type: ignore[attr-defined]

        result = ActionResult(
            narrative="진입",
            rift_transition={
                "action": "enter",
                "rift_id": "bloody_castle",
                "rift_sub_area": "bc_ch1",
                "is_variant": True,
            },
        )

        with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
            updated = asyncio.run(
                mgr.apply_result("s3", result, "핏빛성채 진입", "intent")  # type: ignore[attr-defined]
            )

        self.assertEqual(updated.rift_id, "bloody_castle")
        self.assertEqual(updated.rift_sub_area, "bc_ch1")
        self.assertTrue(updated.rift_is_variant)

    def test_exit_clears_rift_fields(self) -> None:
        mgr: object = self._make_manager()
        import time
        now = time.time()
        state = SessionState(
            session_id="s4",
            current_hp=100,
            max_hp=100,
            inventory=[],
            location="핏빛성채 (균열 내부)",
            encounters=[],
            turn_count=1,
            created_at=now,
            last_active=now,
            rift_id="bloody_castle",
            rift_sub_area="bc_ch5",
            rift_is_variant=False,
        )

        from service.sim.session_manager import SessionManager
        assert isinstance(mgr, SessionManager)
        mgr._cache["s4"] = state  # type: ignore[attr-defined]

        result = ActionResult(
            narrative="탈출",
            rift_transition={"action": "exit"},
        )

        with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
            updated = asyncio.run(
                mgr.apply_result("s4", result, "균열 탈출", "intent")  # type: ignore[attr-defined]
            )

        self.assertIsNone(updated.rift_id)
        self.assertIsNone(updated.rift_sub_area)
        self.assertFalse(updated.rift_is_variant)

    def test_move_to_chamber_updates_sub_area(self) -> None:
        mgr: object = self._make_manager()
        import time
        now = time.time()
        state = SessionState(
            session_id="s5",
            current_hp=100,
            max_hp=100,
            inventory=[],
            location="핏빛성채 (균열 내부)",
            encounters=[],
            turn_count=1,
            created_at=now,
            last_active=now,
            rift_id="bloody_castle",
            rift_sub_area="bc_ch1",
            rift_is_variant=False,
        )

        from service.sim.session_manager import SessionManager
        assert isinstance(mgr, SessionManager)
        mgr._cache["s5"] = state  # type: ignore[attr-defined]

        result = ActionResult(
            narrative="챔버 이동",
            rift_transition={
                "action": "move_to_chamber",
                "rift_sub_area": "bc_ch2",
            },
        )

        with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
            updated = asyncio.run(
                mgr.apply_result("s5", result, "도개교로 이동", "intent")  # type: ignore[attr-defined]
            )

        self.assertEqual(updated.rift_id, "bloody_castle")
        self.assertEqual(updated.rift_sub_area, "bc_ch2")
        self.assertFalse(updated.rift_is_variant)


# ── handle_enter_rift transition emit ──────────────────────────────────────


class TestHandleEnterRiftTransition(unittest.TestCase):
    def _make_ctx(self, location: str = "핏빛성채") -> ActionContext:
        return ActionContext(
            current_hp=100,
            max_hp=100,
            inventory=[],
            location=location,
            floor_number=1,
        )

    def test_emits_rift_transition_on_enter(self) -> None:
        from service.sim.action_handlers import handle_enter_rift
        ctx = self._make_ctx("핏빛성채")
        result = asyncio.run(handle_enter_rift(ctx))
        self.assertIsNotNone(result.rift_transition)
        assert result.rift_transition is not None
        self.assertEqual(result.rift_transition["action"], "enter")
        self.assertEqual(result.rift_transition["rift_id"], "bloody_castle")
        self.assertEqual(result.rift_transition["rift_sub_area"], "bc_ch1")

    def test_rift_id_none_for_unknown_location(self) -> None:
        from service.sim.action_handlers import handle_enter_rift
        ctx = self._make_ctx("알 수 없는 균열")
        result = asyncio.run(handle_enter_rift(ctx))
        assert result.rift_transition is not None
        self.assertIsNone(result.rift_transition["rift_id"])

    def test_handle_exit_rift_emits_exit_transition(self) -> None:
        from service.sim.action_handlers import handle_exit_rift
        ctx = self._make_ctx("핏빛성채 (균열 내부)")
        result = asyncio.run(handle_exit_rift(ctx))
        assert result.rift_transition is not None
        self.assertEqual(result.rift_transition["action"], "exit")


if __name__ == "__main__":
    unittest.main()
