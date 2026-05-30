"""Debate Mode — Drafter(codex) → Challenger(27B) → Quality(9B) 3-stage.

design (HARNESS_CORE 672-914): single review → 3-stage 토론으로 검증 신뢰도 향상.

- Drafter (codex, openai): git diff 직접 리뷰 — Layer1ReviewAgent codex 단계가 담당.
- Challenger (27B, qwen, 8081): ★ 코드 격리 — commit 의도 + 변경 요약만 받아 독립 반박.
- Quality (9B, qwen, 8083): Drafter score + Challenger 우려 종합 → 최종 verdict.

Cross-Model: Drafter(openai) ≠ Challenger(qwen). 코드 author=claude → 3 stage 모두 claude 아님.
gemini(google) 미사용 — 환경 부재.

robustness:
- final_score는 drafter_score를 상향 못 함 (토론은 confirm/하향만 —
  challenger가 코드를 못 보므로 inflate 금지).
- quality verdict=pass면 drafter_score 유지 (clean commit은 9B noise로 감점 X).
- 27B/9B 호출 실패 시 drafter 결과로 fallback (gate fragility 증가 X).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.llm.client import LLMClient, LLMError, Prompt

MAX_DEBATE_SCORE = 25
PASS_CUTOFF = 18  # Layer1 cutoff 정합


class DebateVerdict(StrEnum):
    """debate 최종 verdict."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ChallengerReview:
    """Challenger(27B) 반박 — 코드 격리 (git diff 미열람)."""

    concerns: list[str] = field(default_factory=list)
    missing_checks: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class DebateResult:
    """debate 최종 결과 (★ score ×2 = Verify Agent 50점)."""

    verdict: DebateVerdict
    score: int
    challenger: ChallengerReview
    quality_summary: str = ""
    models_used: dict[str, str] = field(default_factory=dict)
    error: str | None = None


# ── Challenger (27B) — 코드 격리 ────────────────────────────────────────────

_CHALLENGER_SYSTEM = (
    "코드 변경 검증 회의론자. 당신은 실제 코드 diff를 보지 못한다 — "
    "commit 의도와 변경 요약만 본다.\n"
    "역할: 의도가 그 변경만으로 정말 충족되는지 의심하라.\n"
    "- 변경만으로 의도 충족? 누락 가능성?\n"
    "- 검증 누락 (edge case / 회귀 / 부수효과)?\n"
    "- 위험 신호 (과도 / 미흡 / 범위 일탈)?\n"
    "근거 없는 트집은 금지. 실질 우려만. JSON only."
)

_CHALLENGER_SCHEMA: dict[str, Any] = {
    "required": ["concerns", "missing_checks", "summary"],
    "properties": {
        "concerns": {
            "type": "array",
            "items": {"type": "string", "maxLength": 200},
            "maxItems": 5,
        },
        "missing_checks": {
            "type": "array",
            "items": {"type": "string", "maxLength": 200},
            "maxItems": 5,
        },
        "summary": {"type": "string", "maxLength": 300},
    },
}


def run_challenger(
    commit_intent: str,
    change_summary: str,
    client: LLMClient | None = None,
) -> ChallengerReview:
    """Challenger(27B) — 코드 격리 반박.

    ★ git_diff 파라미터 없음 — commit 의도 + 변경 요약만 (false positive 방지).
    """
    if client is None:
        from core.llm.local_client import get_qwen36_27b_q3

        client = get_qwen36_27b_q3()

    user = (
        f"# commit 의도\n{commit_intent[:1500]}\n\n"
        f"# 변경 요약 (Drafter)\n{change_summary[:1500]}\n\n"
        "위 의도가 이 변경만으로 충족되는가? 누락/위험을 지적하라. JSON only."
    )
    prompt = Prompt(system=_CHALLENGER_SYSTEM, user=user)
    resp = client.generate_json(
        prompt, schema=_CHALLENGER_SCHEMA, max_tokens=500, temperature=0.1
    )
    data = resp.parsed
    return ChallengerReview(
        concerns=[str(c) for c in data.get("concerns", []) if isinstance(c, str)],
        missing_checks=[
            str(m) for m in data.get("missing_checks", []) if isinstance(m, str)
        ],
        summary=str(data.get("summary", "")),
    )


# ── Quality (9B) — 종합 ─────────────────────────────────────────────────────

_QUALITY_SYSTEM = (
    "코드 리뷰 종합 판정자. Drafter(코드 직접 평가)와 Challenger(코드 못 본 의심)를 종합한다.\n"
    "규칙:\n"
    "- Challenger 우려가 실질적이고 타당할 때만 score를 낮춘다.\n"
    "- 우려가 막연/무근거면 Drafter 평가를 신뢰하라.\n"
    "- verdict: pass(문제 없음) / warn(경미) / fail(중대 누락·위험).\n"
    "score는 0-25. JSON only."
)

_QUALITY_SCHEMA: dict[str, Any] = {
    "required": ["verdict", "score", "summary"],
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "warn", "fail"]},
        "score": {"type": "integer", "minimum": 0, "maximum": 25},
        "summary": {"type": "string", "maxLength": 300},
    },
}


def run_quality(
    drafter_score: int,
    drafter_summary: str,
    challenger: ChallengerReview,
    client: LLMClient | None = None,
) -> tuple[DebateVerdict, int, str]:
    """Quality(9B) — Drafter + Challenger 종합.

    return: (verdict, quality_score, summary)
    """
    if client is None:
        from core.llm.local_client import get_qwen35_9b_q3

        client = get_qwen35_9b_q3()

    # ★ 정보 격리: drafter score 숫자를 LLM에 전달하지 않음 (anchor 누설 차단).
    #   요약(질적 텍스트)만 전달 — 점수 종합은 code의 judge()에서만 수행.
    concerns = "; ".join(challenger.concerns) or "(없음)"
    missing = "; ".join(challenger.missing_checks) or "(없음)"
    user = (
        f"# Drafter (코드 직접 평가) 요약\n{drafter_summary[:800]}\n\n"
        f"# Challenger (코드 못 봄, 의도 의심)\n"
        f"우려: {concerns}\n누락 지적: {missing}\n요약: {challenger.summary[:400]}\n\n"
        "Challenger 우려가 실질적이고 타당한지 판정하라 (verdict + score). JSON only."
    )
    prompt = Prompt(system=_QUALITY_SYSTEM, user=user)
    resp = client.generate_json(
        prompt, schema=_QUALITY_SCHEMA, max_tokens=400, temperature=0.1
    )
    data = resp.parsed
    verdict_raw = str(data.get("verdict", "warn"))
    verdict = (
        DebateVerdict(verdict_raw)
        if verdict_raw in ("pass", "warn", "fail")
        else DebateVerdict.WARN
    )
    score = int(data.get("score", drafter_score))
    return verdict, score, str(data.get("summary", ""))


# ── orchestration ───────────────────────────────────────────────────────────


class DebateJudge:
    """3-stage debate — Drafter(외부 주입) + Challenger(27B) + Quality(9B).

    Drafter는 Layer1ReviewAgent codex 단계가 담당 → 점수/요약만 받는다 (중복 호출 X).
    """

    def __init__(
        self,
        challenger_client: LLMClient | None = None,
        quality_client: LLMClient | None = None,
    ) -> None:
        self._challenger_client = challenger_client
        self._quality_client = quality_client

    def judge(
        self,
        drafter_score: int,
        drafter_summary: str,
        commit_intent: str,
    ) -> DebateResult:
        """Challenger → Quality 종합. 실패 시 drafter 결과로 fallback."""
        models = {
            "drafter": "codex/gpt-5.5",
            "challenger": "qwen-27b",
            "quality": "qwen-9b",
        }

        # 1. Challenger (27B) — 코드 격리
        try:
            challenger = run_challenger(
                commit_intent=commit_intent,
                change_summary=drafter_summary,
                client=self._challenger_client,
            )
        except (LLMError, Exception) as e:  # noqa: BLE001 — gate 보호: 어떤 실패도 fallback
            return DebateResult(
                verdict=_score_to_verdict(drafter_score),
                score=drafter_score,
                challenger=ChallengerReview(),
                quality_summary="",
                models_used=models,
                error=f"challenger failed: {e}",
            )

        # 2. Quality (9B) — 종합
        try:
            q_verdict, q_score, q_summary = run_quality(
                drafter_score=drafter_score,
                drafter_summary=drafter_summary,
                challenger=challenger,
                client=self._quality_client,
            )
        except (LLMError, Exception) as e:  # noqa: BLE001 — gate 보호
            return DebateResult(
                verdict=_score_to_verdict(drafter_score),
                score=drafter_score,
                challenger=challenger,
                quality_summary="",
                models_used=models,
                error=f"quality failed: {e}",
            )

        # 3. 종합 — 코드를 본 Drafter(codex, 최강)가 authoritative.
        #    Challenger(27B)는 코드 격리 → 의혹은 "미확정 가설"(advisory).
        #    약한 Quality(9B)의 warn-noise가 코드 본 drafter를 뒤집지 못하게:
        #    - FAIL (Quality 확정 결함): min(drafter, quality)로 하향 + 차단
        #    - PASS / WARN: drafter score 유지 (concerns는 advisory 로그)
        #    토론은 drafter score를 상향 못 함 (challenger 코드 못 보므로 inflate 금지).
        if q_verdict == DebateVerdict.FAIL:
            final_score = min(drafter_score, q_score)
            final_verdict = DebateVerdict.FAIL
        else:
            final_score = drafter_score
            final_verdict = (
                DebateVerdict.PASS
                if drafter_score >= PASS_CUTOFF
                else DebateVerdict.FAIL
            )

        return DebateResult(
            verdict=final_verdict,
            score=final_score,
            challenger=challenger,
            quality_summary=q_summary,
            models_used=models,
        )


def _score_to_verdict(score: int) -> DebateVerdict:
    """score → verdict (cutoff 18) — fallback 시 사용."""
    return DebateVerdict.PASS if score >= PASS_CUTOFF else DebateVerdict.FAIL
