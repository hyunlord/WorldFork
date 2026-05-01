"""Layer 2 Pipeline 데이터 모델 (★ 자료 HARNESS_LAYER2 2.2).

8단계 파이프라인:
  Interview → Plan → Verify → Review → Agent → Game → Save
"""

from dataclasses import dataclass, field
from typing import Any, Literal

# ============================================================
# Stage 1: Interview Agent
# ============================================================


@dataclass
class InterviewResult:
    """Interview Agent 결과 (자료 2.2 Stage 1).

    Attributes:
        skip: 명확한 입력이면 True (질문 X, 다음 단계로)
        parsed_input: 명확하면 사용자 입력
        questions: 모호하면 질문 3-5개
        wait_for_user: 사용자 답변 대기 중인지
    """

    skip: bool = False
    parsed_input: str = ""
    questions: list[str] = field(default_factory=list)
    wait_for_user: bool = False

    def __post_init__(self) -> None:
        if not self.skip and not self.questions:
            self.questions = ["입력이 모호합니다. 구체적으로 알려주세요."]


# ============================================================
# Stage 2: Plan (Planning Agent)
# ============================================================


@dataclass
class CharacterPlan:
    """플랜 안의 캐릭터.

    IP Masking 적용된 이름 (원작 이름 X).
    """

    name: str
    role: str
    description: str
    canonical_name: str = ""


@dataclass
class WorldSetting:
    """세계관 정보 (마스킹 적용)."""

    setting_name: str
    genre: str
    tone: str
    rules: list[str] = field(default_factory=list)
    canonical_name: str = ""


@dataclass
class Plan:
    """게임 플랜 (자료 2.2 Stage 2).

    PLAN_SCHEMA 기반 (자료):
      - work_name (마스킹)
      - characters[]
      - world
      - genre
      - tone
      - opening_scene
    """

    work_name: str
    work_genre: str
    main_character: CharacterPlan
    supporting_characters: list[CharacterPlan] = field(default_factory=list)
    world: WorldSetting = field(
        default_factory=lambda: WorldSetting(setting_name="", genre="", tone="")
    )
    opening_scene: str = ""
    initial_choices: list[str] = field(default_factory=list)
    user_preferences: dict[str, Any] = field(default_factory=dict)
    ip_masking_applied: bool = False
    sources_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        result: dict[str, Any] = asdict(self)
        return result


@dataclass
class PlanResult:
    """Planning Agent 결과 (자료 2.2 Stage 2)."""

    plan: Plan
    cost_usd: float = 0.0
    sources_summary: str = ""
    ip_masking_applied: bool = True
    error: str | None = None


# ============================================================
# Stage 3: Plan Verify
# ============================================================


@dataclass
class PlanVerifyResult:
    """Plan 검증 결과 (자료 2.2 Stage 3)."""

    passed: bool
    score: float
    failures: list[str] = field(default_factory=list)
    ip_leakage_score: float = 100.0
    consistency_score: float = 100.0


# ============================================================
# Pipeline 전체 상태
# ============================================================


@dataclass
class PipelineState:
    """Pipeline 8단계 진행 상태."""

    stage: Literal[
        "interview", "planning", "verify", "review",
        "agent_select", "verify_select", "game_loop", "complete",
    ] = "interview"

    interview_result: InterviewResult | None = None
    plan: Plan | None = None
    plan_verify_result: PlanVerifyResult | None = None

    user_input_raw: str = ""
    work_name_input: str = ""

    cumulative_cost_usd: float = 0.0
