"""Game routes (★ Tier 2 D7).

★ 게임 로직은 service/game/ 그대로 활용.
★ API는 얇은 wrapper.
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from core.llm.local_client import get_qwen35_9b_q3, get_qwen36_27b_q3
from core.verify.mechanical import MechanicalChecker
from service.api.models import (
    EndSessionRequest,
    EndSessionResponse,
    GameStateResponse,
    StartGameRequest,
    StartGameResponse,
    TurnRequest,
    TurnResponse,
)
from service.game.game_loop import GameLoop
from service.game.gm_agent import GMAgent
from service.game.init_from_plan import (
    init_game_state_from_plan,
    init_v2_characters_from_plan,
    init_world_state_from_plan,
)
from service.game.state import GameState
from service.game.turn_handler_v2 import advance_time
from service.pipeline.types import CharacterPlan, Plan, WorldSetting

router = APIRouter()


# In-memory 세션 (★ Phase 3 단순)
# Production: Redis / DB 등 고려
_sessions: dict[str, dict[str, Any]] = {}


def _make_default_plan() -> Plan:
    """기본 Plan (★ 단순 시작용).

    Tier 2 D7 단계: 단순 default Plan으로 시작.
    Tier 2 후속: 작품 검색 / Plan 생성 통합.
    """
    return Plan(
        work_name="신비한 모험",
        work_genre="판타지",
        main_character=CharacterPlan(
            name="용감한 모험가",
            role="주인공",
            description="호기심 많은 모험가",
        ),
        world=WorldSetting(
            setting_name="중세 판타지 세계",
            genre="판타지",
            tone="장엄하고 신비로운",
            rules=["마법 존재", "한국어로만"],
        ),
        opening_scene="당신은 모험 시작 지점에 도착했습니다.",
    )


@router.post("/start", response_model=StartGameResponse)
async def start_game(request: StartGameRequest) -> StartGameResponse:
    """게임 시작.

    ★ Tier 2 D7 단순 단계:
      - default Plan 사용 (request.work_name/url은 향후 통합)
      - 세션 생성
      - 초기 상태 반환
    """
    # 세션 ID 생성
    session_id = str(uuid.uuid4())

    # Plan + GameState
    plan = _make_default_plan()
    state = init_game_state_from_plan(plan)

    # ★ Tier 2 D12: state_v2 진짜 production track (★ turn_handler_v2 mutate 대상)
    v2_chars = init_v2_characters_from_plan(plan)
    v2_world = init_world_state_from_plan(plan)

    # 세션 저장 (★ in-memory)
    _sessions[session_id] = {
        "plan": plan,
        "state": state,
        "v2_chars": v2_chars,
        "v2_world": v2_world,
    }

    return StartGameResponse(
        session_id=session_id,
        plan={
            "work_name": plan.work_name,
            "world_setting": plan.world.setting_name,
            "opening_scene": plan.opening_scene,
        },
        initial_state={
            "turn": state.turn,
            "location": state.location,
        },
        message="Game started",
    )


@router.post("/turn", response_model=TurnResponse)
async def process_turn(request: TurnRequest) -> TurnResponse:
    """단일 턴 처리.

    ★ user_action → GMAgent → GameLoop → 응답.
    """
    if request.session_id not in _sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}",
        )

    session = _sessions[request.session_id]
    plan = session["plan"]
    state = session["state"]

    # GMAgent + GameLoop (★ service/game/ 그대로)
    try:
        # ★ Cross-Model: 9B Q3 (game) ≠ 27B Q3 (verify) — 본인 #18 정신
        game_llm = get_qwen35_9b_q3()
        verify_llm = get_qwen36_27b_q3()
        gm = GMAgent(
            game_llm=game_llm,
            verify_llm=verify_llm,
            mechanical_checker=MechanicalChecker(),
        )
        loop = GameLoop(gm)

        result = loop.process_action(plan, state, request.user_action)

        # ★ Tier 2 D12: turn_handler_v2 진짜 production mutate
        # 성공 턴 시 1시간 미궁 시간 진행 (★ 빛 자원 소진 + cooldown 회복)
        if result.verify_passed:
            advance_time(
                list(session["v2_chars"].values()),
                session["v2_world"],
                elapsed_hours=1.0,
            )

        # 잘림 검출 (★ Mechanical 결과 활용)
        truncated = any(
            "truncation" in f.lower() or "잘림" in f
            for f in result.mechanical_failures
        )

        return TurnResponse(
            response=result.response,
            turn_n=state.turn,
            mechanical_passed=result.mechanical_passed,
            truncated=truncated,
            total_score=result.total_score,
            verify_passed=result.verify_passed,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Turn processing failed: {e}",
        ) from e


@router.get("/state/{session_id}", response_model=GameStateResponse)
async def get_state(session_id: str) -> GameStateResponse:
    """현재 게임 상태."""
    if session_id not in _sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}",
        )

    state: GameState = _sessions[session_id]["state"]

    return GameStateResponse(
        session_id=session_id,
        turn=state.turn,
        location=state.location,
        history=[
            {
                "turn": h.turn,
                "user_action": h.user_action[:200],
                "gm_response": h.gm_response[:300],
            }
            for h in state.history[-5:]  # 최근 5턴
        ],
    )


@router.post("/end", response_model=EndSessionResponse)
async def end_session(request: EndSessionRequest) -> EndSessionResponse:
    """세션 종료 + 저장 (★ Tier 2 D10 사람 검증 UX).

    Fun rating + Findings를 받아 JSON 파일로 저장.
    """
    if request.session_id not in _sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}",
        )

    session = _sessions[request.session_id]
    state: GameState = session["state"]
    plan: Plan = session["plan"]

    # 저장 디렉토리
    sessions_dir = Path("docs/sessions")
    sessions_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    saved_path = sessions_dir / f"{request.session_id[:8]}_{timestamp}.json"

    # 직렬화
    data = {
        "session_id": request.session_id,
        "saved_at": datetime.now(UTC).isoformat(),
        "plan": {
            "work_name": plan.work_name,
            "world_setting": plan.world.setting_name,
            "opening_scene": plan.opening_scene,
        },
        "total_turns": state.turn,
        "history": [
            {
                "turn": h.turn,
                "user_action": h.user_action,
                "gm_response": h.gm_response,
                "cost_usd": h.cost_usd,
                "latency_ms": h.latency_ms,
            }
            for h in state.history
        ],
        "fun_rating": (
            {
                "score": request.fun_rating.score,
                "comment": request.fun_rating.comment,
            }
            if request.fun_rating
            else None
        ),
        "findings": [
            {
                "category": f.category,
                "description": f.description,
                "severity": f.severity,
            }
            for f in request.findings
        ],
        "comment": request.comment,
    }

    saved_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 세션 정리 (★ in-memory)
    del _sessions[request.session_id]

    return EndSessionResponse(
        session_id=request.session_id,
        saved_path=str(saved_path),
        total_turns=state.turn,
        summary={
            "fun_score": request.fun_rating.score if request.fun_rating else None,
            "findings_count": len(request.findings),
            "history_length": len(state.history),
        },
    )
