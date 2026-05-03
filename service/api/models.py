"""API 요청/응답 모델 (★ Tier 2 D7).

★ Pydantic 모델로 type 안전.
★ 게임 로직은 service/game/에서 그대로.
"""

from typing import Any

from pydantic import BaseModel, Field


class StartGameRequest(BaseModel):
    """게임 시작 요청."""

    work_url: str | None = Field(
        default=None, description="작품 URL (선택)"
    )
    work_name: str | None = Field(
        default=None, description="작품 이름 (work_url 없을 시)"
    )


class StartGameResponse(BaseModel):
    """게임 시작 응답."""

    session_id: str = Field(description="세션 ID")
    plan: dict[str, Any] = Field(description="생성된 Plan")
    initial_state: dict[str, Any] = Field(description="초기 상태")
    message: str = Field(default="Game started")


class TurnRequest(BaseModel):
    """단일 턴 요청."""

    session_id: str = Field(description="세션 ID")
    user_action: str = Field(description="사용자 액션", min_length=1)


class TurnResponse(BaseModel):
    """단일 턴 응답."""

    response: str = Field(description="GM 응답")
    turn_n: int = Field(description="현재 턴")

    # 검증 결과
    mechanical_passed: bool = Field(description="Mechanical 검증 통과")
    truncated: bool = Field(description="잘림 여부")
    total_score: float = Field(description="통합 점수 0-100")
    verify_passed: bool = Field(description="진짜 통과")


class GameStateResponse(BaseModel):
    """게임 상태."""

    session_id: str
    turn: int
    location: str
    history: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    """에러 응답."""

    error: str
    detail: str | None = None
