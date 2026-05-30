"""mechanism rules 추출 로직 단위 테스트 (★ generalize: extract_mechanism_rules)."""

from __future__ import annotations

from scripts.extract_mechanism_rules import (
    _MIN_DESC,
    get_extract_system,
    has_rules,
    strip_thinking_tags,
)
from service.pipeline.ip_masking import mask_text


def test_has_rules() -> None:
    assert has_rules({"rules": ["효과"]}) is True
    assert has_rules({"rules": []}) is False
    assert has_rules({"name": "X"}) is False
    assert has_rules({"rules": "not a list"}) is False


def test_strip_thinking_tags() -> None:
    assert strip_thinking_tags("<think>고민</think>응답") == "응답"
    assert strip_thinking_tags("그냥 응답") == "그냥 응답"


def test_min_desc_constant() -> None:
    assert _MIN_DESC == 20


def test_category_dispatch() -> None:
    """★ generalize — category별 prompt 분기 (combat/magic/skill 상이)."""
    combat = get_extract_system("combat")
    magic = get_extract_system("magic")
    skill = get_extract_system("skill")
    assert combat != magic != skill
    assert "전투" in combat
    assert "마법" in magic and "element" in magic
    assert "스킬" in skill


def test_unknown_category_fallback() -> None:
    """미지원 category → combat fallback."""
    assert get_extract_system("unknown") == get_extract_system("combat")


def test_ip_masking_applied_to_rule() -> None:
    """★ IP 보호 — rule 문자열에 라프도니아→라스카니아 변환."""
    result = mask_text("라프도니아 전역에서 발동")
    assert "라프도니아" not in result.masked
    assert "라스카니아" in result.masked


def test_ip_masking_noop_clean_rule() -> None:
    """IP 키워드 없는 rule은 변경 X."""
    result = mask_text("신체 결손 시 발동, 2분간 재생")
    assert result.masked == "신체 결손 시 발동, 2분간 재생"
    assert result.masking_applied is False
