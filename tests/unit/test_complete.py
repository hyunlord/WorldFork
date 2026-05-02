"""W2 D5 작업 2: Complete / Save 테스트."""

import json
from pathlib import Path

import pytest

from service.game.init_from_plan import init_game_state_from_plan
from service.pipeline.complete import save_session, summarize_session
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


def _make_plan() -> Plan:
    mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
    return Plan(
        work_name="novice_dungeon_run",
        work_genre="판타지",
        main_character=mc,
        world=WorldSetting(setting_name="던전", genre="판타지", tone="진지", rules=["마법"]),
        opening_scene="던전 입구에 섰다.",
    )


class TestSummarizeSession:
    def test_keys_present(self) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        summary = summarize_session(plan, state, fun_rating=4, findings=[])
        assert "save_id" in summary
        assert summary["work_name"] == "novice_dungeon_run"
        assert summary["turns_completed"] == 0
        assert summary["fun_rating"] == 4
        assert summary["findings"] == []

    def test_history_included(self) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        state.add_turn("들어가기", "응답", 0.01, 100)
        summary = summarize_session(plan, state)
        assert len(summary["history"]) == 1
        assert summary["turns_completed"] == 1

    def test_fun_rating_none_ok(self) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        summary = summarize_session(plan, state)
        assert summary["fun_rating"] is None


class TestSaveSession:
    def test_file_created(self, tmp_path: Path) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        save_path = save_session(plan, state, fun_rating=3, save_dir=tmp_path)
        assert save_path.exists()

    def test_file_valid_json(self, tmp_path: Path) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        save_path = save_session(plan, state, save_dir=tmp_path)
        data = json.loads(save_path.read_text(encoding="utf-8"))
        assert "save_id" in data
        assert "history" in data

    def test_default_save_dir_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import service.pipeline.complete as c_module
        monkeypatch.setattr(c_module, "_DEFAULT_SAVE_DIR", tmp_path / "runs" / "playthrough")
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        save_path = save_session(plan, state)
        assert save_path.parent.exists()
