"""Phase 8 D — GM prompt 다이어트 검증.

본질:
- 9B Q3 context 한도 회피 (★ A1 trace skip 회복)
- 현재 rift만 챕터 detail, 나머지는 1-line summary
- rift 외부면 모든 rift 챕터 detail X
"""

from __future__ import annotations

from service.game.gm_agent import _gm_system_prompt
from tools.measure_gm_prompt import (
    _ctx_inside_rift_boss,
    _ctx_outside_rift,
    measure,
)

# ─── 다이어트: 현재 rift만 챕터 detail ───


def test_outside_rift_no_chapter_details() -> None:
    """rift 외부: 챕터 detail 본격 prompt 출력 X."""
    prompt = _gm_system_prompt(_ctx_outside_rift())

    # 균열 이름은 출력 (활성 균열 등)
    assert "핏빛성채" in prompt
    assert "빙하굴" in prompt or "녹색 탄광" in prompt or "강철의 묘" in prompt

    # 챕터 detail 본격 출력 X — "챕터 (4)" 또는 "챕터 (5)" 없음
    assert "챕터 (" not in prompt, "rift 외부 시 챕터 detail 출력 X"

    # 챕터 sub_area 이름 (★ 빙하굴 "동굴 입구") 본격 X
    assert "동굴 입구" not in prompt
    assert "외곽 검문소" not in prompt


def test_inside_rift_only_current_chapter() -> None:
    """rift 내부: 현재 rift 챕터만 detail, 다른 rift는 1-line summary."""
    prompt = _gm_system_prompt(_ctx_inside_rift_boss())

    # 현재 rift (핏빛성채) 챕터 detail 본격 출력 O
    assert "외곽 검문소" in prompt, "현재 rift 챕터 출력 본격"
    assert "영주성 악마 숭배실" in prompt

    # 다른 rift (빙하굴, 녹색 탄광, 강철의 묘) 챕터 본격 X
    assert "동굴 입구" not in prompt, "빙하굴 챕터 본격 X"
    assert "입구 갱도" not in prompt, "녹색 탄광 챕터 본격 X"


def test_bosses_always_visible() -> None:
    """수호자 정보는 항상 출력 (★ 다이어트 X 항목 — 본문 본격)."""
    for ctx_fn in (_ctx_outside_rift, _ctx_inside_rift_boss):
        prompt = _gm_system_prompt(ctx_fn())
        # 4 rifts 일반 수호자 모두 출력
        assert "저주받은 기사 블라터" in prompt
        assert "폭군 타룬바스" in prompt
        assert "킹 슬라임" in prompt
        assert "철인 일디움" in prompt

        # 본격 변종 수호자 일부도 출력
        assert "캠보르미어" in prompt


def test_entry_and_reward_always_visible() -> None:
    """진입 방식 + 보상 정수 색은 항상 출력 (★ 본격 정보)."""
    prompt = _gm_system_prompt(_ctx_outside_rift())
    assert "8등급 마석 공물" in prompt
    assert "보상 정수 색" in prompt


# ─── prompt size threshold ───


def test_prompt_size_outside_rift_under_3500_tokens() -> None:
    """rift 외부 prompt size < 3500 tokens (★ 9B Q3 4096 ctx 80% margin)."""
    prompt = _gm_system_prompt(_ctx_outside_rift())
    result = measure(prompt)
    # approx (chars/1.8) — 실제 Qwen tokenizer 약 chars/1.5
    # 직전 baseline = 2955 approx (실제 3509), 다이어트 후 = 2230 approx (실제 2624)
    assert result["approx_tokens"] < 3500, (
        f"prompt 본격 다이어트 회귀: {result['approx_tokens']} tokens > 3500 "
        "(★ 9B Q3 ctx 한도 위험)"
    )


def test_prompt_size_inside_rift_under_3500_tokens() -> None:
    """rift 내부 (보스방) prompt size < 3500 tokens."""
    prompt = _gm_system_prompt(_ctx_inside_rift_boss())
    result = measure(prompt)
    assert result["approx_tokens"] < 3500, (
        f"prompt 본격 다이어트 회귀: {result['approx_tokens']} tokens > 3500"
    )


def test_diet_reduction_from_baseline() -> None:
    """다이어트 효과 검증: rift 외부 본격 4500 chars 이하 (★ 직전 baseline 5320)."""
    prompt = _gm_system_prompt(_ctx_outside_rift())
    chars = len(prompt)
    assert chars < 4500, (
        f"다이어트 효과 회귀: {chars} chars >= 4500 "
        "(★ 직전 baseline 5320 → 4015 목표)"
    )
