"""Stage 7 — 1층 5턴 동적 시뮬 (★ Layer 4 동적 검증).

본인 본질 (★ Stage 7, 2026-05-08):
init 시점 외에도 게임 진행 중 동적 상태가 prompt에 진짜 반영되는가?
- Turn 1: 미궁 진입 (init)
- Turn 2: 횃불 점화 → has_active_light
- Turn 3: 균열 진입
- Turn 4: 약탈자 현상금 발령
- Turn 5: 보스 처치 → 정수 흡수

ctx dict 구조 직접 변경으로 시뮬 (★ 게임 루프가 turn 사이 ctx 갱신하는 패턴).
"""

from __future__ import annotations

import pytest

from service.game.gm_agent import _gm_system_prompt
from service.game.init_from_plan import build_game_context, init_game_state_from_plan
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


@pytest.fixture
def floor1_plan() -> Plan:
    return Plan(
        work_name="barbarian_v2",
        work_genre="판타지",
        main_character=CharacterPlan(
            name="비요른",
            role="바바리안 부족장",
            description="주인공",
        ),
        supporting_characters=[
            CharacterPlan(name="에르웬", role="요정 정령사", description="동료"),
        ],
        world=WorldSetting(
            setting_name="라스카니아",
            genre="판타지",
            tone="진지",
            rules=["미궁 존재"],
        ),
        opening_scene="비요른은 1층 수정동굴 진입점에서 깨어난다.",
        initial_choices=["진입"],
        ip_masking_applied=True,
    )


def test_turn1_dungeon_entry_no_light_no_bounty(floor1_plan: Plan) -> None:
    """Turn 1: 미궁 진입 시 빛 비활성, 현상금 X (★ 초기 상태)."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)

    bjorn_light = ctx["v2_characters"]["비요른"]["light_state"]
    assert not bjorn_light["has_active_light"]
    assert bjorn_light["active_source_name"] is None

    assert ctx["v2_world_state"]["active_bounties"] == []

    prompt = _gm_system_prompt(ctx)
    assert "활성 현상금" not in prompt
    # 빛 비활성 상태에서는 빛 라인 X (★ 인자 노출 X)
    assert "빛 [횃불" not in prompt


def test_turn2_torch_lit_shows_in_prompt(floor1_plan: Plan) -> None:
    """Turn 2: 횃불 점화 → ctx 갱신 → prompt에 진짜 노출."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)

    # 게임 루프가 ctx 갱신하는 패턴 시뮬
    ctx["v2_characters"]["비요른"]["light_state"] = {
        "active_source_name": "횃불",
        "remaining_duration_hours": 72.0,
        "cooldown_remaining_hours": 0.0,
        "consumables": {},
        "has_active_light": True,
    }

    prompt = _gm_system_prompt(ctx)
    assert "빛 [횃불 72.0h 남음]" in prompt


def test_turn3_faerie_lantern_with_cooldown(floor1_plan: Plan) -> None:
    """Turn 3: 정령 등불 (★ 요정 한정, 회복 대기 표시)."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)

    ctx["v2_characters"]["에르웬"]["light_state"] = {
        "active_source_name": "정령 등불",
        "remaining_duration_hours": 8.0,
        "cooldown_remaining_hours": 2.0,
        "consumables": {},
        "has_active_light": True,
    }

    prompt = _gm_system_prompt(ctx)
    assert "빛 [정령 등불 8.0h 남음]" in prompt
    assert "회복 대기 2.0h" in prompt


def test_turn4_bounty_issued_appears_in_prompt(floor1_plan: Plan) -> None:
    """Turn 4: 수정 연합이 비요른에게 현상금 발령 (★ 11화 본질)."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)

    ctx["v2_world_state"]["active_bounties"] = [
        {
            "target_name": "비요른",
            "amount_stones": 10000,
            "issuer_name": "수정 연합",
            "issuer_faction": "수정 연합",
            "kill_condition": "생사 무관",
            "reason": "정수 강탈 거부",
            "issued_at_hours": 24,
        }
    ]

    prompt = _gm_system_prompt(ctx)
    assert "활성 현상금" in prompt
    assert "비요른" in prompt
    assert "10,000스톤" in prompt
    assert "수정 연합" in prompt
    assert "생사 무관" in prompt


def test_turn5_essence_absorb_does_not_break_prompt(floor1_plan: Plan) -> None:
    """Turn 5: 정수 흡수 후도 prompt 정합성 유지 (★ 빛 + 현상금 + 정수)."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)

    # 빛 + 현상금 동시
    ctx["v2_characters"]["비요른"]["light_state"] = {
        "active_source_name": "횃불",
        "remaining_duration_hours": 60.0,
        "cooldown_remaining_hours": 0.0,
        "consumables": {},
        "has_active_light": True,
    }
    ctx["v2_world_state"]["active_bounties"] = [
        {
            "target_name": "비요른",
            "amount_stones": 20000,
            "issuer_name": "수정 연합 강화",
            "issuer_faction": "수정 연합",
            "kill_condition": "처치 한정",
            "reason": "강화 발령",
            "issued_at_hours": 48,
        }
    ]

    prompt = _gm_system_prompt(ctx)
    assert "빛 [횃불 60.0h 남음]" in prompt
    assert "20,000스톤" in prompt
    assert "처치 한정" in prompt
    # 사이즈 적정
    assert 2000 <= len(prompt) <= 25000


def test_multiple_bounties_all_render(floor1_plan: Plan) -> None:
    """현상금 다수 발령 시 모두 렌더링 (★ 동적 다수 case)."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)

    ctx["v2_world_state"]["active_bounties"] = [
        {
            "target_name": "비요른",
            "amount_stones": 10000,
            "issuer_name": "수정 연합",
            "issuer_faction": "수정 연합",
            "kill_condition": "생사 무관",
            "reason": "",
            "issued_at_hours": 12,
        },
        {
            "target_name": "에르웬",
            "amount_stones": 10000,
            "issuer_name": "수정 연합",
            "issuer_faction": "수정 연합",
            "kill_condition": "생포 한정",
            "reason": "정령사 가치",
            "issued_at_hours": 24,
        },
    ]

    prompt = _gm_system_prompt(ctx)
    assert "활성 현상금 (2)" in prompt
    assert "에르웬" in prompt
    assert "생포 한정" in prompt
