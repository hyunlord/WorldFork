#!/usr/bin/env python
"""W2 D5 본인 풀 플레이 도구 (★ 인사이트 #14 적용).

사용법:
  python tools/play_w2_d5.py

흐름:
  1. 작품명 입력 (또는 기본값 novice_dungeon_run)
  2. Mock Plan 생성 → 화면 출력
  3. Plan Review (yes/no)
  4. Agent Selection (qwen35-9b-q3)
  5. Game Loop (최대 30턴, ★ 진짜 LLM 호출)
  6. 평가 (fun_rating + findings)
  7. 결과 저장 → runs/playthrough/

★ Phase 2: Claude Code는 여기서 멈춤. 본인이 직접 실행.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm.local_client import get_qwen35_9b_q3
from service.game.game_loop import GameLoop
from service.game.gm_agent import GMAgent
from service.game.init_from_plan import init_game_state_from_plan
from service.pipeline.complete import save_session
from service.pipeline.plan_review import classify_user_decision, format_plan_for_user
from service.pipeline.planning import MockPlanningAgent
from service.pipeline.types import Plan

MAX_TURNS = 30
_HR = "─" * 60


def _print_banner() -> None:
    print("\n" + "=" * 60)
    print("  WorldFork — W2 D5 본인 풀 플레이")
    print("  ★ 인사이트 #14: 게임 성숙 후 본인 검토")
    print("=" * 60 + "\n")


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n(중단됨)")
        sys.exit(0)


def _step_interview() -> str:
    print(_HR)
    print("★ Step 1 — 작품명 입력")
    print("  예시: novice_dungeon_run")
    print("  (빈 칸 Enter → 기본값 사용)\n")
    raw = _ask("작품명: ")
    work_name = raw if raw else "novice_dungeon_run"
    print(f"  → {work_name}\n")
    return work_name


def _step_planning(work_name: str) -> Plan:
    print(_HR)
    print("★ Step 2 — Plan 생성 (Mock)")
    agent = MockPlanningAgent()
    result = agent.run(
        work_name=work_name,
        user_preferences={"entry_point": "주인공"},
    )
    if result.error:
        print(f"  [경고] Plan 오류: {result.error}")
        print("  → 기본 Plan으로 진행합니다.")
    print("  Plan 생성 완료.\n")
    return result.plan


def _step_plan_review(plan: Plan) -> bool:
    """Plan 리뷰. True = 승인, False = 취소."""
    print(_HR)
    print("★ Step 3 — Plan Review\n")
    print(format_plan_for_user(plan))

    for _attempt in range(3):
        raw = _ask("이 플랜으로 진행하시겠습니까? (ok/수정/취소): ")
        decision = classify_user_decision(raw)

        if decision == "approve":
            print("  → 승인. 게임을 시작합니다!\n")
            return True
        elif decision == "cancel":
            print("  → 취소.\n")
            return False
        elif decision == "modify":
            print("  [안내] W2 D5는 Mock Plan 사용 중 — 수정은 W3에서 지원 예정.")
            print("         그냥 ok를 입력하거나, 취소하세요.")
        else:
            print("  [안내] ok / 취소 중 하나를 입력해주세요.")

    print("  (3회 입력 실패 → 취소)\n")
    return False


def _step_game_loop(plan: Plan) -> tuple[int, list[dict[str, Any]], float]:
    """Game Loop 실행. (turns, findings_collected, cost_usd)를 반환."""
    print(_HR)
    print("★ Step 4 — Game Loop (최대 30턴)\n")
    print("  서버: qwen35-9b-q3 (port 8083)")
    print("  모델 연결 중...")

    llm = get_qwen35_9b_q3()
    gm = GMAgent(llm)
    loop = GameLoop(gm)
    state = init_game_state_from_plan(plan)

    print(f"\n{'=' * 60}")
    print("  오프닝 장면")
    print(f"{'=' * 60}")
    print(f"\n{plan.opening_scene}\n")

    if plan.initial_choices:
        print("초기 선택지:")
        for i, c in enumerate(plan.initial_choices, 1):
            print(f"  {i}. {c}")
    print()

    issues: list[dict[str, Any]] = []
    total_cost = 0.0

    while state.turn < MAX_TURNS:
        turn_num = state.turn + 1
        raw = _ask(f"[턴 {turn_num:02d}] 행동 입력 (abandon으로 종료): ")

        if raw.lower() in {"abandon", "quit", "exit", "종료", "나가기"}:
            print(f"\n  → 게임 중단 (turn {state.turn})\n")
            break

        print("\n  [처리 중...] ", end="", flush=True)
        t0 = time.perf_counter()
        result = loop.process_action(plan, state, raw)
        elapsed = time.perf_counter() - t0
        total_cost += result.cost_usd

        print(f"{elapsed:.1f}초 / ${result.cost_usd:.4f}\n")
        print(f"{'─' * 40}")
        print(result.response)
        print(f"{'─' * 40}\n")

        if result.fallback_used:
            print("  [시스템] Fallback 응답이 사용되었습니다.")
            issues.append({
                "category": "general",
                "description": f"Turn {state.turn}: Fallback used — {result.error}",
                "turn": state.turn,
                "severity": "major",
            })

        if result.mechanical_failures:
            for failure in result.mechanical_failures:
                print(f"  [Mechanical] {failure}")
                issues.append({
                    "category": "general",
                    "description": f"Turn {state.turn}: Mechanical — {failure}",
                    "turn": state.turn,
                    "severity": "minor",
                })

        # 종료 조건 체크
        if "[ENDING]" in result.response.upper():
            print("\n  ★ 엔딩 감지! 게임 완료.\n")
            break

    print(f"\n  총 턴: {state.turn}  총 비용: ${total_cost:.4f}\n")
    return state.turn, issues, total_cost


def _step_evaluation(
    turns: int, auto_issues: list[dict[str, Any]]
) -> tuple[int, list[dict[str, Any]]]:
    """평가 단계. (fun_rating, all_findings) 반환."""
    print(_HR)
    print("★ Step 5 — 평가\n")
    print(f"  완료 턴: {turns}")
    print()

    # Fun rating
    for _attempt in range(5):
        raw = _ask("Fun rating (1-5): ")
        if raw.isdigit() and 1 <= int(raw) <= 5:
            fun_rating = int(raw)
            break
        print("  1-5 사이 숫자를 입력해주세요.")
    else:
        fun_rating = 3
        print("  (기본값 3 사용)")

    print()
    print("  Fun rating 기준:")
    print("    1: 답답함  2: 약간 흥미  3: 그럭저럭  4: 재밌음  5: 매우 재밌음")
    print(f"  → 입력: {fun_rating}/5\n")

    # 추가 발견 이슈
    findings = list(auto_issues)
    print("  추가 발견 이슈 입력 (빈 칸 Enter → 완료)\n")
    cats = "korean_quality / encoding / ai_breakout / world_consistency / ux / persona_consistency"
    print(f"  카테고리: {cats} / general")
    while True:
        desc = _ask("  이슈 설명 (없으면 Enter): ")
        if not desc:
            break
        cat = _ask("  카테고리: ") or "general"
        sev = _ask("  심각도 (critical/major/minor): ") or "minor"
        findings.append({
            "category": cat,
            "description": desc,
            "turn": turns,
            "severity": sev,
        })
        print(f"  → 추가됨 ({len(findings)}건)\n")

    return fun_rating, findings


def _step_save(
    plan: Plan,
    turns: int,
    fun_rating: int,
    findings: list[dict[str, Any]],
) -> None:
    from service.game.init_from_plan import init_game_state_from_plan as _init
    print(_HR)
    print("★ Step 6 — 저장\n")

    # 게임 state 재구성 (history 없는 요약용)
    state = _init(plan)
    state.turn = turns

    save_path = save_session(
        plan=plan,
        state=state,
        fun_rating=fun_rating,
        findings=findings,
    )
    print(f"  저장 완료: {save_path}\n")
    print(f"  ★ 분석: python tools/play_w2_d5_analyze.py {save_path}\n")


def main() -> None:
    _print_banner()

    # Step 1: Interview (작품명)
    work_name = _step_interview()

    # Step 2: Planning
    plan = _step_planning(work_name)

    # Step 3: Plan Review
    approved = _step_plan_review(plan)
    if not approved:
        print("게임을 종료합니다.")
        sys.exit(0)

    # Step 4: Game Loop
    turns, auto_issues, _cost = _step_game_loop(plan)

    # Step 5: 평가
    fun_rating, findings = _step_evaluation(turns, auto_issues)

    # Step 6: 저장
    _step_save(plan, turns, fun_rating, findings)

    # 결과 요약
    print("=" * 60)
    print("  W2 D5 플레이 완료!")
    print(f"  턴: {turns} / Fun: {fun_rating}/5 / 이슈: {len(findings)}건")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
