"""EntityIndex role lookup 단위 테스트 (★ I-E2 runtime 활용)."""

from __future__ import annotations

from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Character


def _make_facts() -> CanonFacts:
    return CanonFacts(
        essences=[],
        characters=[
            Character(name="비요른", role="주인공", background="바바리안 주인공"),
            Character(name="투르윈", role="주인공", background="바바리안 IP 변환 이름"),
            Character(name="에르웬", role="동료", background="요정족 파티원"),
            Character(name="아이나르", role="동료", background="검사 파티원"),
            Character(name="셰인", role="동료", background="기사 파티원"),
            Character(name="사서 할매", role="주요 NPC",
                      background="라비기온 도서관 사서"),
            Character(name="대장장이 한스", role="주민",
                      background="라스카니아 대장장이"),
            Character(name="DC 유저 김씨", role="메타",
                      background="커뮤니티 게시판 작성자"),
            Character(name="군중1", role="엑스트라"),
            Character(name="role 없음", role=None),
        ],
        locations=[],
        races=[],
        mechanisms=[],
    )


def test_get_characters_by_role_protagonist() -> None:
    idx = EntityIndex(_make_facts())
    chars = idx.get_characters_by_role("주인공")
    names = {str(c["name"]) for c in chars}
    assert names == {"비요른", "투르윈"}


def test_get_characters_by_role_companion() -> None:
    idx = EntityIndex(_make_facts())
    chars = idx.get_characters_by_role("동료")
    assert len(chars) == 3
    assert {str(c["name"]) for c in chars} == {"에르웬", "아이나르", "셰인"}


def test_get_characters_by_role_all_categories() -> None:
    idx = EntityIndex(_make_facts())
    for role in ["주인공", "동료", "주요 NPC", "주민", "엑스트라", "메타"]:
        chars = idx.get_characters_by_role(role)
        assert isinstance(chars, list)
        assert len(chars) >= 1, f"{role} 정합 character 0개"


def test_get_characters_by_role_unknown_returns_empty() -> None:
    idx = EntityIndex(_make_facts())
    assert idx.get_characters_by_role("알수없는역할XYZ") == []
    assert idx.get_characters_by_role("") == []


def test_get_characters_by_role_excludes_none() -> None:
    """role None character는 role_map에 등록 X."""
    idx = EntityIndex(_make_facts())
    all_role_chars: list[dict[str, object]] = []
    for role in ["주인공", "동료", "주요 NPC", "주민", "엑스트라", "메타"]:
        all_role_chars.extend(idx.get_characters_by_role(role))
    names = {str(c["name"]) for c in all_role_chars}
    assert "role 없음" not in names


def test_get_role_for_character_exact() -> None:
    idx = EntityIndex(_make_facts())
    assert idx.get_role_for_character("비요른") == "주인공"
    assert idx.get_role_for_character("에르웬") == "동료"
    assert idx.get_role_for_character("DC 유저 김씨") == "메타"


def test_get_role_for_character_unknown_returns_none() -> None:
    idx = EntityIndex(_make_facts())
    assert idx.get_role_for_character("존재하지않는캐릭XYZ") is None
    assert idx.get_role_for_character("") is None


def test_get_role_for_character_none_role_returns_none() -> None:
    """role=None character lookup → None 반환."""
    idx = EntityIndex(_make_facts())
    assert idx.get_role_for_character("role 없음") is None
