"""1층 본격 디자인 end-to-end 통합 테스트.

본인 본질 (★ Stage 6, 2026-05-08):
직전 5 commit 진짜 1층 풀 통합 검증:
- Plan → init_from_plan → build_game_context → ctx → _gm_system_prompt
- 모든 v2 섹션 진짜 출력 검증
- 1층 풀 자료 (★ 6 sub_area + 7 monster + 4 rift + 3 light + bounty)
- 진행 룰 (★ Stage 6 보강)
"""

from __future__ import annotations

import pytest

from service.game.gm_agent import _gm_system_prompt
from service.game.init_from_plan import build_game_context, init_game_state_from_plan
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


@pytest.fixture
def floor1_plan() -> Plan:
    """1층 미궁 시작 시 Plan."""
    return Plan(
        work_name="barbarian_v2",
        work_genre="판타지",
        main_character=CharacterPlan(
            name="비요른",
            role="바바리안 부족장",
            description="주인공",
        ),
        supporting_characters=[
            CharacterPlan(
                name="에르웬",
                role="요정 정령사",
                description="동료",
            ),
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


def test_e2e_floor1_full_context(floor1_plan: Plan) -> None:
    """Plan → state → build_game_context → 모든 v2 섹션 진짜 부여."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)

    # ─── 모든 v2 섹션 진짜 ───
    assert "v2_characters" in ctx
    assert "v2_world_state" in ctx
    assert "v2_initial_location" in ctx
    assert "v2_floor_definition" in ctx

    # 캐릭터 종족별 base
    chars = ctx["v2_characters"]
    assert "비요른" in chars
    assert chars["비요른"]["race"] == "바바리안"
    assert chars["비요른"]["height"] == 210  # ★ 바바리안 base
    assert chars["비요른"]["hp"] == 150

    # WorldState 어둠 본질
    ws = ctx["v2_world_state"]
    assert ws["is_dark_zone"]

    # Location 1층 어둠 + 가시거리 10m
    loc = ctx["v2_initial_location"]
    assert loc["realm"] == "미궁"
    assert loc["floor"] == 1
    assert loc["visibility_meters"] == 10
    assert not loc["has_light"]

    # Floor1 풀 정의
    fd = ctx["v2_floor_definition"]
    assert fd["name"] == "수정동굴"
    assert len(fd["sub_areas"]) == 6
    assert len(fd["monsters"]) == 7
    assert len(fd["rifts"]) == 4
    assert len(fd["light_sources"]) == 3
    assert fd["bounty_config"] is not None


def test_e2e_floor1_prompt_full_output(floor1_plan: Plan) -> None:
    """1층 시작 prompt 풀 출력 (★ Layer 4 모든 섹션)."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)
    prompt = _gm_system_prompt(ctx)

    # ─── 캐릭터 ───
    assert "비요른" in prompt
    assert "바바리안" in prompt
    assert "에르웬" in prompt
    assert "요정" in prompt

    # ─── WorldState ───
    assert "라운드" in prompt
    assert "어둠" in prompt

    # ─── Location ───
    assert "미궁" in prompt
    assert "10m" in prompt or "10.0m" in prompt or "가시거리" in prompt

    # ─── Floor1 풀 정의 ───
    assert "수정동굴" in prompt
    assert "168" in prompt

    # Sub Areas
    assert "비석 공동" in prompt
    assert "포탈 근처" in prompt

    # Monsters
    assert "고블린" in prompt
    assert "노움" in prompt

    # Rifts
    assert "핏빛성채" in prompt
    assert "캠브로미어" in prompt or "변종" in prompt

    # Light Sources
    assert "횃불" in prompt
    assert "정령 등불" in prompt

    # PvP
    assert "수정 연합" in prompt
    assert "300" in prompt

    # ─── Stage 6 진행 룰 ───
    assert "1층 진행 룰" in prompt
    assert "168시간" in prompt or "7일" in prompt
    assert "챕터" in prompt
    assert "정수 흡수" in prompt
    assert "30분" in prompt
    assert "자연 소멸" in prompt
    assert "9:1" in prompt
    assert "화살 회수" in prompt


def test_e2e_floor1_no_placeholder_text(floor1_plan: Plan) -> None:
    """1층 prompt에 placeholder/TODO 텍스트 X (★ YAGNI 검증)."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)
    prompt = _gm_system_prompt(ctx)

    forbidden = ("TODO", "FIXME", "PLACEHOLDER", "추가 검증 필요")
    for f in forbidden:
        assert f not in prompt, f"prompt에 '{f}' 발견 — placeholder 차단"


def test_e2e_floor1_prompt_size_reasonable(floor1_plan: Plan) -> None:
    """1층 prompt 크기 적정 (★ 27B context 보호)."""
    state = init_game_state_from_plan(floor1_plan)
    ctx = build_game_context(floor1_plan, state)
    prompt = _gm_system_prompt(ctx)

    assert len(prompt) >= 2000, f"prompt 너무 짧음: {len(prompt)}자"
    assert len(prompt) < 25000, f"prompt 너무 큼: {len(prompt)}자"
