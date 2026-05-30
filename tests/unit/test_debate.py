"""Debate Mode 단위 테스트 — Drafter/Challenger/Quality 3-stage."""

from __future__ import annotations

import inspect

from core.verify.debate import (
    PASS_CUTOFF,
    ChallengerReview,
    DebateJudge,
    DebateResult,
    DebateVerdict,
    run_challenger,
    run_quality,
)

# ── dataclass / 구조 ────────────────────────────────────────────────────────


def test_challenger_review_dataclass() -> None:
    c = ChallengerReview(concerns=["우려"], missing_checks=["누락"], summary="s")
    assert c.concerns == ["우려"]
    assert c.missing_checks == ["누락"]


def test_debate_result_models_3stage() -> None:
    r = DebateResult(
        verdict=DebateVerdict.PASS,
        score=23,
        challenger=ChallengerReview(),
        models_used={
            "drafter": "codex/gpt-5.5",
            "challenger": "qwen-27b",
            "quality": "qwen-9b",
        },
    )
    assert len(r.models_used) == 3
    # ★ Drafter(openai) ≠ Challenger(qwen) family
    assert "codex" in r.models_used["drafter"]
    assert "qwen" in r.models_used["challenger"]
    assert "qwen" in r.models_used["quality"]


# ── Challenger 코드 격리 (★ design 핵심) ────────────────────────────────────


def test_challenger_code_isolation_signature() -> None:
    """run_challenger는 git_diff 파라미터 없음 (★ 코드 격리)."""
    params = list(inspect.signature(run_challenger).parameters.keys())
    assert "git_diff" not in params
    assert "commit_intent" in params
    assert "change_summary" in params


# ── Challenger / Quality (mock client) ──────────────────────────────────────


class _FakeJSONResp:
    def __init__(self, parsed: dict) -> None:
        self.parsed = parsed
        self.text = ""


class _FakeClient:
    """generate_json 만 mock — payload 검증 + 고정 응답."""

    def __init__(self, parsed: dict) -> None:
        self._parsed = parsed
        self.last_user = ""

    def generate_json(self, prompt, schema=None, **kwargs):  # noqa: ANN001
        self.last_user = prompt.user
        return _FakeJSONResp(self._parsed)


def test_run_challenger_parses_and_isolates_code() -> None:
    client = _FakeClient({
        "concerns": ["edge case 누락 가능"],
        "missing_checks": ["회귀 테스트"],
        "summary": "추가 검증 권장",
    })
    result = run_challenger(
        commit_intent="feat: X 함수 추가",
        change_summary="X 함수 + 기본 테스트",
        client=client,
    )
    assert result.concerns == ["edge case 누락 가능"]
    assert result.missing_checks == ["회귀 테스트"]
    # ★ Challenger 프롬프트에 git diff가 없음 — 의도/요약만
    assert "diff --git" not in client.last_user
    assert "X 함수 추가" in client.last_user


def test_run_quality_returns_verdict_score() -> None:
    client = _FakeClient({"verdict": "pass", "score": 22, "summary": "양호"})
    verdict, score, summary = run_quality(
        drafter_score=23,
        drafter_summary="ok",
        challenger=ChallengerReview(),
        client=client,
    )
    assert verdict == DebateVerdict.PASS
    assert score == 22


def test_run_quality_does_not_leak_drafter_score() -> None:
    """★ 정보 격리 — Quality 프롬프트에 drafter 점수 숫자 미전달 (debate가 검출한 결함).

    점수 anchor 누설 시 Quality LLM이 무비판 추종 → 검증 무력화.
    """
    client = _FakeClient({"verdict": "pass", "score": 20, "summary": "ok"})
    run_quality(
        drafter_score=23,
        drafter_summary="양호한 변경, 테스트 충분",
        challenger=ChallengerReview(concerns=["우려"]),
        client=client,
    )
    # 옛 누설 형식 'score: 23/25' / '23/25' 부재
    assert "23/25" not in client.last_user
    assert "score: 23" not in client.last_user
    # 질적 요약은 전달됨 (종합에 필요)
    assert "양호한 변경" in client.last_user


# ── DebateJudge orchestration ───────────────────────────────────────────────


def test_judge_pass_keeps_drafter_score() -> None:
    """quality=pass면 drafter score 유지 (9B noise 감점 방지)."""
    challenger_c = _FakeClient({"concerns": [], "missing_checks": [], "summary": "없음"})
    quality_c = _FakeClient({"verdict": "pass", "score": 15, "summary": "ok"})
    judge = DebateJudge(challenger_client=challenger_c, quality_client=quality_c)
    result = judge.judge(drafter_score=24, drafter_summary="clean", commit_intent="feat: x")
    assert result.verdict == DebateVerdict.PASS
    assert result.score == 24  # ★ quality score(15)로 깎이지 않음


def test_judge_fail_lowers_score() -> None:
    """quality=fail이면 min(drafter, quality)로 하향 + fail."""
    challenger_c = _FakeClient({
        "concerns": ["중대 누락"], "missing_checks": ["보안 검증"], "summary": "위험",
    })
    quality_c = _FakeClient({"verdict": "fail", "score": 8, "summary": "중대 문제"})
    judge = DebateJudge(challenger_client=challenger_c, quality_client=quality_c)
    result = judge.judge(drafter_score=23, drafter_summary="x", commit_intent="feat: y")
    assert result.verdict == DebateVerdict.FAIL
    assert result.score == 8


def test_judge_never_inflates_above_drafter() -> None:
    """quality=warn이고 quality_score > drafter여도 drafter 상한 (상향 X)."""
    challenger_c = _FakeClient({"concerns": ["경미"], "missing_checks": [], "summary": "s"})
    quality_c = _FakeClient({"verdict": "warn", "score": 24, "summary": "ok"})
    judge = DebateJudge(challenger_client=challenger_c, quality_client=quality_c)
    result = judge.judge(drafter_score=20, drafter_summary="x", commit_intent="z")
    assert result.score == 20  # ★ drafter 상한 — quality 24 > 20여도 상향 X


def test_judge_warn_is_advisory_keeps_drafter() -> None:
    """quality=warn (코드 격리 challenger 의혹) → drafter score 유지 + pass.

    ★ 코드 못 본 challenger의 미확정 의혹이 코드 본 drafter를 뒤집지 못함.
    warn-noise로 clean commit이 차단되지 않도록 — concerns는 advisory 로그.
    """
    challenger_c = _FakeClient({
        "concerns": ["X 정말 구현됐나?", "fallback 모호"],
        "missing_checks": ["회귀 테스트"],
        "summary": "검증 불가 의혹",
    })
    quality_c = _FakeClient({"verdict": "warn", "score": 18, "summary": "불확실"})
    judge = DebateJudge(challenger_client=challenger_c, quality_client=quality_c)
    result = judge.judge(drafter_score=23, drafter_summary="양호", commit_intent="feat: x")
    assert result.score == 23  # ★ drafter 유지 (warn으로 감점 X)
    assert result.verdict == DebateVerdict.PASS  # ★ advisory — 차단 X
    assert result.challenger.concerns  # concerns는 보존 (로그)


def test_judge_challenger_failure_fallback_to_drafter() -> None:
    """Challenger LLM 실패 → drafter 결과 fallback (gate 보호)."""
    class _BoomClient:
        def generate_json(self, *a, **k):  # noqa: ANN002, ANN003
            raise RuntimeError("27B down")

    judge = DebateJudge(challenger_client=_BoomClient(), quality_client=_FakeClient({}))
    result = judge.judge(drafter_score=22, drafter_summary="x", commit_intent="y")
    assert result.score == 22
    assert result.verdict == DebateVerdict.PASS  # 22 >= cutoff 18
    assert result.error is not None and "challenger" in result.error


def test_judge_quality_failure_fallback() -> None:
    """Quality LLM 실패 → drafter 결과 fallback."""
    challenger_c = _FakeClient({"concerns": [], "missing_checks": [], "summary": "s"})

    class _BoomQuality:
        def generate_json(self, *a, **k):  # noqa: ANN002, ANN003
            raise RuntimeError("9B down")

    judge = DebateJudge(challenger_client=challenger_c, quality_client=_BoomQuality())
    result = judge.judge(drafter_score=10, drafter_summary="x", commit_intent="y")
    assert result.score == 10
    assert result.verdict == DebateVerdict.FAIL  # 10 < cutoff 18
    assert result.error is not None and "quality" in result.error


def test_pass_cutoff_constant() -> None:
    assert PASS_CUTOFF == 18
