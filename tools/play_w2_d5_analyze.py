#!/usr/bin/env python
"""W2 D5 결과 분석 + Eval Seed 변환 도구.

사용법:
  python tools/play_w2_d5_analyze.py runs/playthrough/<save_id>.json

흐름:
  1. save_path JSON 로드
  2. findings → eval seeds 변환 (★ W2 D3 seed_converter 활용)
  3. evals/auto_added/{category}.jsonl 에 추가
  4. 분석 보고서 출력

★ Tier 1 졸업 #4 입증:
  "본인이 작품명 → 플랜 → 게임 30턴 풀 플레이"
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.ai_playtester.seed_converter import (
    EVALS_AUTO_ADDED_DIR,
    EXPECTED_BEHAVIORS_BY_CATEGORY,
    _map_category,
)

_MAX_AUTO_SEEDS_PER_SESSION = 5

_FINDING_CRITERIA: dict[str, str] = {
    "korean_quality": "응답이 자연스러운 한국어이며 공문서체가 아닐 것",
    "encoding": "인코딩 깨짐이 없을 것",
    "ai_breakout": "AI 또는 IP 정보가 노출되지 않을 것",
    "world_consistency": "세계관 룰을 위반하지 않을 것",
    "ux": "선택지/페이싱/명확성이 적절할 것",
    "persona_consistency": "캐릭터 말투/성격이 일관될 것",
    "general": "응답이 적절한 길이이며 잘리지 않을 것",
}


def _load_session(save_path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(save_path.read_text(encoding="utf-8"))
    return data


def _build_seed(
    finding: dict[str, Any],
    work_name: str,
    history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    cat_raw = finding.get("category", "general")
    cat = _map_category(cat_raw)
    turn = finding.get("turn", 0)
    description = finding.get("description", "")
    severity = finding.get("severity", "minor")

    # 해당 턴의 user_action 찾기 (없으면 시드 거부)
    turn_entry: dict[str, Any] | None = None
    for h in history:
        if h.get("turn") == turn:
            turn_entry = h
            break

    if turn_entry is None:
        if not history:
            # history 없는 경우 기본 프롬프트 사용
            user_input = description
        else:
            return None

    else:
        user_input = turn_entry.get("user_action", description)

    expected = EXPECTED_BEHAVIORS_BY_CATEGORY.get(
        cat, EXPECTED_BEHAVIORS_BY_CATEGORY["general"]
    ).copy()
    if severity == "critical":
        expected["critical_avoidance"] = True

    criteria = _FINDING_CRITERIA.get(cat, _FINDING_CRITERIA["general"])
    seed_id = f"w2d5_{cat}_{str(uuid.uuid4())[:6]}"

    return {
        "id": seed_id,
        "category": cat,
        "version": "v1",
        "prompt": {
            "system": f"[{work_name}] GM 응답 생성",
            "user": user_input,
        },
        "expected_behavior": expected,
        "criteria": criteria,
        "context": {
            "source": "w2_d5_playthrough",
            "original_category": cat_raw,
            "turn": turn,
            "description": description,
            "severity": severity,
        },
        "metadata": {
            "added_at": datetime.now(UTC).isoformat(),
            "origin": "personal_playthrough",
        },
    }


def _append_seeds(seeds: list[dict[str, Any]]) -> dict[str, int]:
    """seeds → evals/auto_added/{cat}.jsonl 추가. {cat: count} 반환."""
    added: dict[str, int] = {}
    EVALS_AUTO_ADDED_DIR.mkdir(parents=True, exist_ok=True)

    for seed in seeds:
        cat = seed["category"]
        fpath = EVALS_AUTO_ADDED_DIR / f"{cat}.jsonl"
        with fpath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(seed, ensure_ascii=False) + "\n")
        added[cat] = added.get(cat, 0) + 1

    return added


def analyze(save_path: Path) -> None:
    print("\n" + "=" * 60)
    print("  W2 D5 결과 분석")
    print("=" * 60 + "\n")

    session = _load_session(save_path)

    work_name: str = session.get("work_name", "unknown")
    turns: int = session.get("turns_completed", 0)
    fun_rating: Any = session.get("fun_rating")
    findings: list[dict[str, Any]] = session.get("findings", [])
    total_cost: float = session.get("total_cost_usd", 0.0)
    history: list[dict[str, Any]] = session.get("history", [])

    print(f"  작품: {work_name}")
    print(f"  완료 턴: {turns}")
    print(f"  Fun rating: {fun_rating}/5")
    print(f"  총 비용: ${total_cost:.4f}")
    print(f"  발견 이슈: {len(findings)}건")
    print()

    # Tier 1 졸업 #4 체크
    tier1_grad = turns >= 1 or len(findings) > 0
    print(f"  ★ Tier 1 졸업 #4 (작품명→플랜→게임): {'✅' if tier1_grad else '⏳'}")
    print()

    if not findings:
        print("  발견 이슈 없음 — Seed 변환 스킵.\n")
        return

    # Seed 변환
    print(f"  발견 이슈 → Eval Seed 변환 (최대 {_MAX_AUTO_SEEDS_PER_SESSION}건)")
    seeds: list[dict[str, Any]] = []
    for finding in findings[:_MAX_AUTO_SEEDS_PER_SESSION]:
        seed = _build_seed(finding, work_name, history)
        if seed is not None:
            seeds.append(seed)
            print(f"    + [{seed['category']}] {finding['description'][:50]}")
        else:
            print(f"    - 스킵 (turn {finding.get('turn')} 기록 없음)")

    if seeds:
        added = _append_seeds(seeds)
        print(f"\n  저장 완료: {dict(added)}")
        for cat, count in added.items():
            fpath = EVALS_AUTO_ADDED_DIR / f"{cat}.jsonl"
            print(f"    {fpath} (+{count})")
    else:
        print("  (변환 가능 시드 없음)")

    print()

    # 보고서 요약
    print("─" * 60)
    fun_str = ["", "답답함", "약간 흥미", "그럭저럭", "재밌음", "매우 재밌음"]
    rating_label = (
        fun_str[fun_rating] if isinstance(fun_rating, int) and 1 <= fun_rating <= 5 else "?"
    )
    print(f"  ★ 한 줄 요약: Fun {fun_rating}/5 ({rating_label}), {turns}턴, 이슈 {len(findings)}건")
    print("─" * 60 + "\n")


def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: python tools/play_w2_d5_analyze.py <save_path.json>")
        print("예시:   python tools/play_w2_d5_analyze.py runs/playthrough/<save>.json")
        sys.exit(1)

    save_path = Path(sys.argv[1])
    if not save_path.exists():
        print(f"파일 없음: {save_path}")
        sys.exit(1)

    analyze(save_path)


if __name__ == "__main__":
    main()
