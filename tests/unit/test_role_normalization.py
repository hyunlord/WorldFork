"""I-E2 character role 정규화 로직 단위 테스트."""

from scripts.normalize_character_role import (
    ALL_ROLES,
    ROLE_COMPANION,
    ROLE_EXTRA,
    ROLE_MAJOR_NPC,
    ROLE_META,
    ROLE_PROTAGONIST,
    ROLE_RESIDENT,
    classify_direct,
)


def test_direct_protagonist() -> None:
    assert classify_direct("주인공") == ROLE_PROTAGONIST
    assert classify_direct("플레이어") == ROLE_PROTAGONIST
    assert classify_direct("바바리안, 플레이어") == ROLE_PROTAGONIST


def test_direct_companion() -> None:
    assert classify_direct("동료") == ROLE_COMPANION
    assert classify_direct("원정대장") == ROLE_COMPANION
    assert classify_direct("파티원") == ROLE_COMPANION
    assert classify_direct("팀원") == ROLE_COMPANION


def test_direct_major_npc() -> None:
    assert classify_direct("귀족") == ROLE_MAJOR_NPC
    assert classify_direct("신") == ROLE_MAJOR_NPC
    assert classify_direct("길드장") == ROLE_MAJOR_NPC


def test_direct_resident() -> None:
    assert classify_direct("탐험가") == ROLE_RESIDENT
    assert classify_direct("마법사") == ROLE_RESIDENT
    assert classify_direct("전사") == ROLE_RESIDENT
    assert classify_direct("기사") == ROLE_RESIDENT


def test_direct_meta() -> None:
    assert classify_direct("커뮤니티 유저") == ROLE_META
    assert classify_direct("커뮤니티 사용자") == ROLE_META
    assert classify_direct("유저") == ROLE_META
    assert classify_direct("DC 유저") == ROLE_META


def test_keyword_compound_roles() -> None:
    """compound role — keyword 패턴 매칭."""
    assert classify_direct("귀족, 협력자") == ROLE_MAJOR_NPC
    assert classify_direct("5등급 탐험가") == ROLE_RESIDENT
    assert classify_direct("탐험가 길드장") == ROLE_MAJOR_NPC  # 길드장 우선
    assert classify_direct("커뮤니티 회원") == ROLE_META


def test_llm_reclassify_needed() -> None:
    """캐릭터 / 등장인물 → LLM 재분류 (None 반환)."""
    assert classify_direct("캐릭터") is None
    assert classify_direct("등장인물") is None


def test_unknown_role_llm_reclassify() -> None:
    """미매핑 기존 role → LLM 재분류."""
    assert classify_direct("클랜") is None
    assert classify_direct("미정") == ROLE_EXTRA


def test_empty_or_none() -> None:
    assert classify_direct(None) is None
    assert classify_direct("") is None
    assert classify_direct("   ") is None


def test_all_roles_count() -> None:
    """ALL_ROLES 6개 정확."""
    assert len(ALL_ROLES) == 6
    assert ROLE_PROTAGONIST in ALL_ROLES
    assert ROLE_COMPANION in ALL_ROLES
    assert ROLE_MAJOR_NPC in ALL_ROLES
    assert ROLE_RESIDENT in ALL_ROLES
    assert ROLE_EXTRA in ALL_ROLES
    assert ROLE_META in ALL_ROLES
