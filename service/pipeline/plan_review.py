"""Plan Review (★ 자료 2.2 Stage 4).

사용자가 생성된 Plan을 보고 승인/수정/취소 결정.
LLM 없음 — 단순 yes/no UX.

Decision 분류:
  approve   : 승인 (ok / yes / 네 / 좋아 / 시작 등)
  modify    : 수정 요청 (수정 / 바꿔 / 다르게 / change 등)
  cancel    : 취소 (취소 / 그만 / 나가기 / cancel / quit 등)
  clarify   : 판단 불가 (위 3개에 해당 안 됨)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from service.pipeline.types import Plan

ReviewDecision = Literal["approve", "modify", "cancel", "clarify"]

_APPROVE_KEYWORDS = {
    "ok", "yes", "네", "응", "좋아", "좋음", "시작", "ㅇㅋ", "ㅇ",
    "확인", "동의", "맞아", "맞음", "괜찮아", "괜찮음", "진행", "go",
    "start", "agree", "approved",
}
_MODIFY_KEYWORDS = {
    "수정", "바꿔", "바꾸", "다르게", "다시", "변경", "고쳐", "고치",
    "수정해", "바꿔줘", "change", "modify", "edit", "adjust", "update",
}
_CANCEL_KEYWORDS = {
    "취소", "그만", "나가기", "나가", "중단", "끝", "안 해", "안해",
    "cancel", "quit", "exit", "stop", "abort",
}


@dataclass
class PlanReviewResult:
    """Plan Review 결과 (자료 2.2 Stage 4)."""

    decision: ReviewDecision
    modification_request: str = ""
    raw_input: str = ""
    skipped: bool = False


@dataclass
class PlanReviewSession:
    """Plan Review 세션 (사용자 인터랙션 상태)."""

    plan: Plan
    result: PlanReviewResult | None = None
    display_lines: list[str] = field(default_factory=list)


def format_plan_for_user(plan: Plan) -> str:
    """Plan 내용을 사용자 친화적 텍스트로 변환."""
    chars = [plan.main_character]
    chars.extend(plan.supporting_characters)
    char_lines = "\n".join(
        f"  - {c.name} ({c.role}): {c.description}" for c in chars
    )

    choices_text = ""
    if plan.initial_choices:
        choices_text = "\n초기 선택지:\n" + "\n".join(
            f"  {i + 1}. {c}" for i, c in enumerate(plan.initial_choices)
        )

    return (
        f"=== 게임 플랜 ===\n"
        f"작품: {plan.work_name}\n"
        f"장르: {plan.work_genre}\n\n"
        f"세계관:\n"
        f"  {plan.world.setting_name} — {plan.world.tone}\n"
        f"  룰: {', '.join(plan.world.rules) if plan.world.rules else '없음'}\n\n"
        f"캐릭터:\n{char_lines}\n\n"
        f"오프닝:\n  {plan.opening_scene}"
        f"{choices_text}\n"
    )


def classify_user_decision(user_input: str) -> ReviewDecision:
    """사용자 입력 → ReviewDecision (rule-based, 0 LLM 토큰)."""
    normalized = user_input.strip().lower()

    # 취소 우선 (안전)
    for kw in _CANCEL_KEYWORDS:
        if kw in normalized:
            return "cancel"

    # 수정
    for kw in _MODIFY_KEYWORDS:
        if kw in normalized:
            return "modify"

    # 승인
    for kw in _APPROVE_KEYWORDS:
        if kw == normalized or normalized.startswith(kw + " ") or normalized.endswith(" " + kw):
            return "approve"
    # 짧은 승인 (1-2 글자)
    if normalized in {"ㅇ", "ㅇㅋ", "ok", "y"}:
        return "approve"

    return "clarify"


def review_plan(plan: Plan, user_input: str) -> PlanReviewResult:
    """Plan Review 실행 (Stage 4).

    user_input: 사용자가 Plan 화면을 보고 입력한 텍스트
    """
    decision = classify_user_decision(user_input)
    modification_request = user_input if decision == "modify" else ""

    return PlanReviewResult(
        decision=decision,
        modification_request=modification_request,
        raw_input=user_input,
    )
