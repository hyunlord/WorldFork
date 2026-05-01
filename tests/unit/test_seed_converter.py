"""Tier 1 W1 D4-D6: FindingToEvalSeed + SeedManager 단위 테스트.

★ W1 D6: 자료 5.2 정확 구현 반영
    - playthrough[turn_n] 추출 fixture
    - turn_context fallback 테스트
    - None 시드 거부 테스트
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tools.ai_playtester.runner import PlaytesterFinding, PlaytesterSessionResult
from tools.ai_playtester.seed_converter import (
    EvalSeed,
    FindingToEvalSeed,
    SeedManager,
)


def _make_finding(
    severity: str = "major",
    category: str = "tone_mismatch",
    description: str = "공문서체 응답",
    turn_n: int = 1,
    turn_context: dict[str, Any] | None = None,
) -> PlaytesterFinding:
    return PlaytesterFinding(
        severity=severity,
        category=category,
        turn_n=turn_n,
        description=description,
        turn_context=turn_context or {},
    )


def _make_turn_log(
    turn_n: int = 1,
    role: str = "game_response",
    user_input: str = "다음으로 가자",
    game_response: str = "당신은 던전에 들어갑니다.",
) -> dict[str, Any]:
    """★ W1 D6: TurnLog dict (자료 5.2 target_turn 모양)."""
    return {
        "turn_n": turn_n,
        "role": role,
        "system_prompt": "당신은 한국어 텍스트 어드벤처 GM입니다.",
        "user_input": user_input,
        "game_response": game_response,
        "latency_ms": 100,
        "context": {"language": "ko", "character_response": True},
    }


def _make_session(
    persona_id: str = "casual_korean_player",
    playthrough_log: list[dict[str, Any]] | None = None,
) -> PlaytesterSessionResult:
    """기본 fixture: turn 0 (intro) + turn 1 (game_response) 포함."""
    if playthrough_log is None:
        playthrough_log = [
            _make_turn_log(turn_n=0, role="game_intro",
                           user_input="시작", game_response="게임 인트로..."),
            _make_turn_log(turn_n=1),
        ]
    return PlaytesterSessionResult(
        persona_id=persona_id,
        work_name="novice_dungeon_run",
        completed=False,
        n_turns_played=2,
        elapsed_seconds=42.0,
        fun_rating=1,
        would_replay=False,
        abandoned=True,
        abandon_reason="intro 잘림",
        abandon_turn=2,
        findings=[],
        playthrough_log=playthrough_log,
    )


def _make_seed(category: str = "korean_quality", idx: int = 0) -> EvalSeed:
    return EvalSeed(
        id=f"test_{idx}",
        category=category,
        version="auto_added",
        prompt={"system": "", "user": ""},
        expected_behavior={},
        criteria=category,
        context={},
        metadata={"discovered_at": datetime.now().isoformat()},
    )


class TestFindingToEvalSeed:
    def test_tone_mismatch_maps_to_korean_quality(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding("major", "tone_mismatch"), _make_session()
        )
        assert seed is not None
        assert seed.category == "korean_quality"

    def test_verbose_maps_to_korean_quality(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding("major", "verbose"), _make_session()
        )
        assert seed is not None
        assert seed.category == "korean_quality"

    def test_ip_leak_maps_to_ip_leakage(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding("critical", "ip_leak"), _make_session()
        )
        assert seed is not None
        assert seed.category == "ip_leakage"

    def test_broken_ux_maps_to_ux(self) -> None:
        """W1 D7: broken_ux는 general → ux 로 이동."""
        seed = FindingToEvalSeed().convert(
            _make_finding("critical", "broken_ux"), _make_session()
        )
        assert seed is not None
        assert seed.category == "ux"

    def test_unknown_category_maps_to_general(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding("minor", "unknown_xyz"), _make_session()
        )
        assert seed is not None
        assert seed.category == "general"

    def test_version_is_auto_added(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding(), _make_session())
        assert seed is not None
        assert seed.version == "auto_added"

    def test_metadata_persona_recorded(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(), _make_session("speed_runner")
        )
        assert seed is not None
        assert seed.metadata["persona"] == "speed_runner"

    def test_metadata_severity_recorded(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding("critical"), _make_session())
        assert seed is not None
        assert seed.metadata["severity"] == "critical"

    def test_id_contains_persona(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(), _make_session("casual_korean_player")
        )
        assert seed is not None
        assert "casual_korean_player" in seed.id

    def test_to_jsonl_roundtrip(self) -> None:
        import json
        seed = FindingToEvalSeed().convert(_make_finding(), _make_session())
        assert seed is not None
        line = seed.to_jsonl()
        data = json.loads(line)
        assert data["version"] == "auto_added"
        assert data["category"] == "korean_quality"


class TestW1D6SeedExtraction:
    """★ W1 D6: 자료 5.2 — playthrough[turn_n] 추출 정확성."""

    def test_target_turn_extracted_from_playthrough(self) -> None:
        """playthrough_log의 turn_n=1 entry → seed.prompt."""
        seed = FindingToEvalSeed().convert(
            _make_finding(turn_n=1), _make_session()
        )
        assert seed is not None
        # ★ 자료 5.2: prompt = target_turn 의 system + user
        assert "텍스트 어드벤처" in seed.prompt["system"]
        assert seed.prompt["user"] == "다음으로 가자"

    def test_no_target_turn_returns_none(self) -> None:
        """playthrough에 turn_n 매칭 없고 turn_context도 비면 None."""
        # finding은 turn_n=99 인데 playthrough엔 turn 0,1만 있음
        seed = FindingToEvalSeed().convert(
            _make_finding(turn_n=99), _make_session()
        )
        assert seed is None

    def test_turn_context_fallback(self) -> None:
        """playthrough 매칭 없어도 turn_context 있으면 변환 성공."""
        finding = _make_finding(
            turn_n=99,
            turn_context={
                "system_prompt": "fallback system",
                "user_input": "fallback user",
                "language": "ko",
                "character_response": True,
            },
        )
        seed = FindingToEvalSeed().convert(finding, _make_session())
        assert seed is not None
        assert seed.prompt["system"] == "fallback system"
        assert seed.prompt["user"] == "fallback user"

    def test_expected_behavior_persona_consistency_categories(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(category="persona_break"), _make_session()
        )
        assert seed is not None
        eb = seed.expected_behavior
        assert eb["in_character"] is True
        assert eb["no_ai_mentions"] is True
        assert eb["speech_style_consistent"] is True

    def test_expected_behavior_korean_quality_categories(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(category="verbose"), _make_session()
        )
        assert seed is not None
        eb = seed.expected_behavior
        assert eb["natural_korean"] is True
        assert eb["no_excessive_honorifics"] is True
        assert eb["no_korean_english_mix"] is True

    def test_expected_behavior_ip_leakage_categories(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(category="ip_leak"), _make_session()
        )
        assert seed is not None
        eb = seed.expected_behavior
        assert eb["no_proper_names"] is True
        assert eb["uses_renamed_only"] is True

    def test_expected_behavior_ai_breakout_deflect(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(category="ai_breakout"), _make_session()
        )
        assert seed is not None
        assert seed.expected_behavior["deflect_meta_question"] is True

    def test_critical_severity_adds_critical_avoidance(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(severity="critical"), _make_session()
        )
        assert seed is not None
        assert seed.expected_behavior.get("critical_avoidance") is True

    def test_minor_severity_no_critical_avoidance(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(severity="minor"), _make_session()
        )
        assert seed is not None
        assert "critical_avoidance" not in seed.expected_behavior

    def test_metadata_finding_turn_n_recorded(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(turn_n=7),
            _make_session(playthrough_log=[_make_turn_log(turn_n=7)]),
        )
        assert seed is not None
        assert seed.metadata["finding_turn_n"] == 7


class TestSeedManager:
    def test_add_within_limits(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=20, max_per_category=5)
            seeds: list[EvalSeed | None] = [
                _make_seed("korean_quality", i) for i in range(3)
            ]
            result = mgr.add_seeds(seeds)
            assert len(result.added) == 3
            assert len(result.rejected) == 0
            assert result.daily_count_after == 3

    def test_max_per_category_enforced(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=20, max_per_category=2)
            seeds: list[EvalSeed | None] = [
                _make_seed("korean_quality", i) for i in range(5)
            ]
            result = mgr.add_seeds(seeds)
            assert len(result.added) == 2
            assert len(result.rejected) == 3

    def test_max_per_day_enforced(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=3, max_per_category=10)
            seeds: list[EvalSeed | None] = [
                _make_seed("general", i) for i in range(5)
            ]
            result = mgr.add_seeds(seeds)
            assert len(result.added) == 3
            assert len(result.rejected) == 2

    def test_mixed_categories_respected(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=20, max_per_category=2)
            kq_seeds: list[EvalSeed | None] = [
                _make_seed("korean_quality", i) for i in range(3)
            ]
            ge_seeds: list[EvalSeed | None] = [
                _make_seed("general", i + 10) for i in range(3)
            ]
            seeds: list[EvalSeed | None] = kq_seeds + ge_seeds
            result = mgr.add_seeds(seeds)
            added_cats = {s.category for s in result.added}
            assert "korean_quality" in added_cats
            assert "general" in added_cats
            kq = sum(1 for s in result.added if s.category == "korean_quality")
            ge = sum(1 for s in result.added if s.category == "general")
            assert kq <= 2
            assert ge <= 2

    def test_jsonl_file_created(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=20, max_per_category=5)
            mgr.add_seeds([_make_seed("ip_leakage")])
            assert (tmp_path / "ip_leakage.jsonl").exists()

    def test_none_seeds_rejected(self, tmp_path: Path) -> None:
        """★ W1 D6: None 시드 자동 거부 + 카운트."""
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=20, max_per_category=5)
            seeds: list[EvalSeed | None] = [
                _make_seed("general", 0),
                None,
                _make_seed("general", 1),
                None,
                None,
            ]
            result = mgr.add_seeds(seeds)
            assert len(result.added) == 2
            assert result.none_rejected == 3
