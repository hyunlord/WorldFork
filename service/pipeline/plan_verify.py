"""Plan Verify (★ 자료 2.2 Stage 3).

자료 검증 항목:
  1. IP leakage (저작권 누출)
  2. World consistency (세계관 일관성)
  3. User preference match (사용자 의도 충실)
  4. Plan quality (실행 가능성)

원칙:
  - Mock 우선 (★ 본인 인사이트 #14)
  - DebateJudge 본격 X (Tier 2+ 메모)
  - W2 D3: rule-based + Mock LLM
"""

from typing import Any, Protocol

from core.llm.client import LLMResponse, Prompt

from .ip_masking import detect_ip_keywords
from .types import Plan, PlanVerifyResult


class VerifyLLMClient(Protocol):
    @property
    def model_name(self) -> str: ...
    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse: ...


VERIFY_CRITERIA = {
    "ip_leakage": "Plan에 작품 IP 누출이 없는가?",
    "world_consistency": "세계관이 일관성 있는가?",
    "user_preference": "사용자 선호 반영됐는가?",
    "plan_quality": "Plan이 실행 가능한가?",
}


def check_ip_leakage(plan: Plan) -> tuple[float, list[str]]:
    """IP 누출 검증 (rule-based, ★ critical)."""
    issues: list[str] = []
    score = 100.0

    fields_to_check = [
        ("work_name", plan.work_name),
        ("main_character.name", plan.main_character.name),
        ("main_character.description", plan.main_character.description),
        ("world.setting_name", plan.world.setting_name),
        ("opening_scene", plan.opening_scene),
    ]
    for sc in plan.supporting_characters:
        fields_to_check.append((f"supporting.{sc.name}", sc.name))
        fields_to_check.append((f"supporting.{sc.name}.description", sc.description))

    for field, text in fields_to_check:
        detected = detect_ip_keywords(text)
        if detected:
            score -= 30
            issues.append(f"{field}: keywords {detected}")

    return max(0.0, score), issues


def check_world_consistency(plan: Plan) -> tuple[float, list[str]]:
    """세계관 일관성 rule-based."""
    issues: list[str] = []
    score = 100.0

    if not plan.world.setting_name:
        score -= 20
        issues.append("world.setting_name empty")
    if not plan.world.genre:
        score -= 15
        issues.append("world.genre empty")
    if len(plan.world.rules) == 0:
        score -= 15
        issues.append("world.rules empty")

    if plan.world.genre and plan.world.rules:
        joined_rules = " ".join(plan.world.rules)
        if "판타지" in plan.world.genre and not any(
            kw in joined_rules for kw in ["마법", "괴물", "정령", "엘프", "드래곤"]
        ):
            score -= 10
            issues.append("판타지 장르 but 마법/괴물 없음 (소프트 위반)")

    return max(0.0, score), issues


def check_user_preference_match(
    plan: Plan,
    user_preferences: dict[str, str],
) -> tuple[float, list[str]]:
    """User preference 반영 검증."""
    issues: list[str] = []
    score = 100.0

    entry_point = user_preferences.get("entry_point", "")
    if entry_point:
        role = plan.main_character.role
        if entry_point == "주인공" and "주인공" not in role:
            score -= 30
            issues.append(f"entry_point=주인공 but role={role}")

    play_style = user_preferences.get("play_style", "")
    if play_style and not plan.opening_scene:
        score -= 10
        issues.append("opening_scene empty (play_style 반영 어려움)")

    return max(0.0, score), issues


def check_plan_quality(plan: Plan) -> tuple[float, list[str]]:
    """Plan quality (실행 가능성)."""
    issues: list[str] = []
    score = 100.0

    if not plan.opening_scene:
        score -= 30
        issues.append("opening_scene empty")
    elif len(plan.opening_scene) < 20:
        score -= 15
        issues.append("opening_scene too short")

    if len(plan.initial_choices) < 2:
        score -= 25
        issues.append(f"initial_choices < 2 ({len(plan.initial_choices)})")

    if not plan.main_character.description:
        score -= 15
        issues.append("main_character.description empty")

    return max(0.0, score), issues


class MockPlanVerifyAgent:
    """Mock Verify (★ Tier 1-2 본격 LLM 호출 X).

    Rule-based 점수 + force_pass 옵션.
    """

    def __init__(self, force_pass: bool = True) -> None:
        self._force_pass = force_pass

    def verify(
        self,
        plan: Plan,
        user_preferences: dict[str, str] | None = None,
    ) -> PlanVerifyResult:
        prefs = user_preferences or {}

        ip_score, ip_issues = check_ip_leakage(plan)
        world_score, world_issues = check_world_consistency(plan)
        pref_score, pref_issues = check_user_preference_match(plan, prefs)
        quality_score, quality_issues = check_plan_quality(plan)

        all_issues = ip_issues + world_issues + pref_issues + quality_issues

        total_score = (
            ip_score * 0.4
            + world_score * 0.2
            + pref_score * 0.2
            + quality_score * 0.2
        )

        passed = self._force_pass or total_score >= 80

        return PlanVerifyResult(
            passed=passed,
            score=total_score,
            failures=all_issues,
            ip_leakage_score=ip_score,
            consistency_score=world_score,
        )


class PlanVerifyAgent:
    """Plan Verify 본체 (★ 자료 2.2 Stage 3).

    Rule-based + 선택적 LLM 보조.
    DebateJudge 본격 X (Tier 2+).
    """

    def __init__(self, llm_client: VerifyLLMClient | None = None) -> None:
        self._llm = llm_client

    def verify(
        self,
        plan: Plan,
        user_preferences: dict[str, str] | None = None,
    ) -> PlanVerifyResult:
        prefs = user_preferences or {}

        ip_score, ip_issues = check_ip_leakage(plan)
        world_score, world_issues = check_world_consistency(plan)
        pref_score, pref_issues = check_user_preference_match(plan, prefs)
        quality_score, quality_issues = check_plan_quality(plan)

        all_issues = ip_issues + world_issues + pref_issues + quality_issues
        total_score = (
            ip_score * 0.4
            + world_score * 0.2
            + pref_score * 0.2
            + quality_score * 0.2
        )

        if self._llm is not None and total_score >= 60:
            try:
                llm_score = self._llm_quality_check(plan)
                total_score = total_score * 0.7 + llm_score * 0.3
            except Exception:
                pass

        # IP는 더 엄격 (70+ 강제)
        passed = total_score >= 80 and ip_score >= 70

        return PlanVerifyResult(
            passed=passed,
            score=total_score,
            failures=all_issues,
            ip_leakage_score=ip_score,
            consistency_score=world_score,
        )

    def _llm_quality_check(self, plan: Plan) -> float:
        if self._llm is None:
            return 80.0

        prompt_text = (
            f"다음 게임 플랜의 quality (실행 가능성, 재미)를 0-100으로 평가:\n"
            f"작품: {plan.work_name}\n"
            f"주인공: {plan.main_character.name} ({plan.main_character.description})\n"
            f"opening: {plan.opening_scene[:200]}\n"
            f"choices: {', '.join(plan.initial_choices)}\n\n"
            f"점수만 숫자로 출력 (예: 75)."
        )
        prompt = Prompt(system="숫자만 출력", user=prompt_text)
        response = self._llm.generate(prompt, max_tokens=10)

        try:
            text = response.text.strip()
            score = float("".join(c for c in text if c.isdigit() or c == "."))
            return min(100.0, max(0.0, score))
        except (ValueError, TypeError):
            return 70.0
