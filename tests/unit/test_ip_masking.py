"""W2 D1 작업 8: IP Masking 테스트."""

from service.pipeline.ip_masking import (
    GENERIC_REPLACEMENTS,
    KOREAN_IP_KEYWORDS,
    apply_ip_masking,
    detect_ip_keywords,
    mask_text,
)
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


class TestDetectIPKeywords:
    def test_clean_text(self) -> None:
        assert detect_ip_keywords("일반 모험 텍스트") == []

    def test_one_keyword(self) -> None:
        result = detect_ip_keywords("비요른의 모험")
        assert "비요른" in result

    def test_multiple_keywords(self) -> None:
        result = detect_ip_keywords("비요른이 라프도니아에서 회귀했다")
        assert "비요른" in result
        assert "라프도니아" in result
        assert "회귀" in result

    def test_no_partial_match_in_safe_text(self) -> None:
        assert detect_ip_keywords("전혀 관계없는 텍스트") == []


class TestMaskText:
    def test_clean_passes_unchanged(self) -> None:
        result = mask_text("일반 텍스트")
        assert result.original == "일반 텍스트"
        assert result.masked == "일반 텍스트"
        assert not result.masking_applied

    def test_masking_applied(self) -> None:
        result = mask_text("비요른이 모험을 한다")
        assert result.masking_applied
        assert "비요른" not in result.masked
        assert "비요른" in result.keywords_detected

    def test_custom_replacement(self) -> None:
        result = mask_text("비요른이 모험", keyword_replacements={"비요른": "영웅"})
        assert "영웅" in result.masked
        assert "비요른" not in result.masked

    def test_default_replacement_is_generic(self) -> None:
        result = mask_text("비요른")
        assert result.masked in GENERIC_REPLACEMENTS["character"]


class TestApplyIPMasking:
    def test_clean_plan_no_keyword_change(self) -> None:
        mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
        plan = Plan(work_name="novice_dungeon_run", work_genre="판타지", main_character=mc)
        masked = apply_ip_masking(plan)
        assert masked.work_name == "novice_dungeon_run"
        assert masked.main_character.name == "투르윈"
        assert masked.ip_masking_applied is True

    def test_dirty_plan_name_masked(self) -> None:
        mc = CharacterPlan(name="비요른", role="주인공", description="바바리안")
        plan = Plan(work_name="바바리안", work_genre="판타지", main_character=mc)
        masked = apply_ip_masking(plan)
        assert "비요른" not in masked.main_character.name
        assert masked.main_character.canonical_name == "비요른"
        assert masked.ip_masking_applied is True

    def test_supporting_characters_masked(self) -> None:
        mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
        sc = CharacterPlan(name="비요른", role="조력자", description="멘토")
        plan = Plan(
            work_name="test", work_genre="판타지",
            main_character=mc, supporting_characters=[sc],
        )
        masked = apply_ip_masking(plan)
        assert "비요른" not in masked.supporting_characters[0].name

    def test_world_setting_masked(self) -> None:
        mc = CharacterPlan(name="투르윈", role="주인공", description="d")
        plan = Plan(
            work_name="test", work_genre="판타지",
            main_character=mc,
            world=WorldSetting(setting_name="라프도니아 왕국", genre="판타지", tone="진지"),
        )
        masked = apply_ip_masking(plan)
        assert "라프도니아" not in masked.world.setting_name
        assert masked.world.canonical_name == "라프도니아 왕국"

    def test_immutable_original(self) -> None:
        mc = CharacterPlan(name="비요른", role="주인공", description="d")
        plan = Plan(work_name="test", work_genre="g", main_character=mc)
        masked = apply_ip_masking(plan)
        assert plan.main_character.name == "비요른"
        assert masked.main_character.name != "비요른"

    def test_ip_masking_applied_always_true(self) -> None:
        mc = CharacterPlan(name="투르윈", role="주인공", description="d")
        plan = Plan(work_name="clean", work_genre="g", main_character=mc)
        masked = apply_ip_masking(plan)
        assert masked.ip_masking_applied is True


class TestKeywordConfig:
    def test_keywords_list_not_empty(self) -> None:
        assert len(KOREAN_IP_KEYWORDS) > 0
        assert "비요른" in KOREAN_IP_KEYWORDS
        assert "라프도니아" in KOREAN_IP_KEYWORDS

    def test_generic_replacements_have_categories(self) -> None:
        assert "character" in GENERIC_REPLACEMENTS
        assert "place" in GENERIC_REPLACEMENTS
        assert "world" in GENERIC_REPLACEMENTS
        assert len(GENERIC_REPLACEMENTS["character"]) >= 1
