"""GM prompt size 측정 — 9B Q3 context (~8192 token) 한도 진단.

본격 측정 (★ 외부 패키지 0건 — 한국어 1 token ≈ 1.8 chars approx).

사용:
    python -m tools.measure_gm_prompt           # rift 외부
    python -m tools.measure_gm_prompt --in-rift # rift 내부 (보스방)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.game.init_from_plan import _floor_definition_dict_for

_BASE_CTX: dict[str, Any] = {
    "work_name": "겜바바",
    "work_genre": "판타지",
    "world_setting": "라스카니아 — 미궁의 도시",
    "world_tone": "진지",
    "world_rules": ["미궁", "정수", "균열"],
    "main_character_name": "비요른",
    "main_character_role": "주인공 바바리안",
    "supporting_characters": [
        {"name": "투르윈", "role": "검사"},
        {"name": "셰인", "role": "궁수"},
    ],
    "current_location": "1층 — 수정동굴",
    "current_turn": 0,
}


def _ctx_outside_rift() -> dict[str, Any]:
    """1층 평소 ctx (★ rift 외부)."""
    return {
        **_BASE_CTX,
        "v2_world_state": {
            "current_round": 1,
            "hours_in_dungeon": 12,
            "is_dimension_collapse": False,
            "active_rifts": ["bloody_castle"],
            "is_dark_zone": True,
            "party_members": ["비요른", "투르윈", "셰인"],
            "party_share_ratios": {"비요른": 0.6, "투르윈": 0.2, "셰인": 0.2},
        },
        "v2_initial_location": {
            "realm": "1층",
            "floor": 1,
            "sub_area": "수정동굴 중심부",
            "rift_id": None,
            "visibility_meters": 10,
            "has_light": False,
        },
        "v2_floor_definition": _floor_definition_dict_for(1),
    }


def _ctx_inside_rift_boss() -> dict[str, Any]:
    """rift 내부 — 핏빛성채 보스방."""
    base = _ctx_outside_rift()
    base["v2_initial_location"] = {
        "realm": "균열",
        "floor": 1,
        "sub_area": None,
        "rift_id": "bloody_castle",
        "rift_sub_area": "bc_demon_chamber",
        "rift_is_variant": True,
        "visibility_meters": 5,
        "has_light": True,
    }
    return base


def measure(prompt: str) -> dict[str, Any]:
    chars = len(prompt)
    bytes_len = len(prompt.encode("utf-8"))
    # Gemma KR 1 token ≈ 1.8 chars (★ approximate)
    approx_tokens = int(chars / 1.8)
    return {
        "chars": chars,
        "bytes": bytes_len,
        "approx_tokens": approx_tokens,
        "ctx_8192_usage_pct": round(approx_tokens / 8192 * 100, 1),
        "ctx_4096_usage_pct": round(approx_tokens / 4096 * 100, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-rift", action="store_true")
    parser.add_argument("--show", action="store_true", help="prompt 출력")
    args = parser.parse_args()

    ctx = _ctx_inside_rift_boss() if args.in_rift else _ctx_outside_rift()
    prompt = _gm_system_prompt(ctx)
    result = measure(prompt)

    label = "rift 내부 (핏빛성채 보스방)" if args.in_rift else "rift 외부"
    print(f"=== GM prompt 측정: {label} ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    print(f"prompt 본격 = {result['chars']} chars / {result['bytes']} bytes")
    print(
        f"9B Q3 (~8192 token) 사용율: {result['ctx_8192_usage_pct']}%  "
        f"(★ 70%+ 시 위험)"
    )
    if result["ctx_8192_usage_pct"] > 70:
        print("⚠ 위험 — 다이어트 본격")

    if args.show:
        print("\n=== prompt 본문 ===\n")
        print(prompt)

    return 0


if __name__ == "__main__":
    sys.exit(main())
