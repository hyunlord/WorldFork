"""Phase 9.17-g — NPC 호감도 4 tier (★ 162화 '새로운 절친' 정합).

본 commit (★ B minimal):
- AffinityTier enum (★ STRANGER/ACQUAINTANCE/FRIEND/CLOSE_FRIEND)
- AFFINITY_TIER_THRESHOLD_FRIEND/CLOSE_FRIEND 상수
- AFFINITY_TIER_KOREAN_LABELS (★ 지인/동료/친구/절친)
- get_affinity_tier / get_affinity_label helpers
- gm_agent NPC display 본격 label 추가
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _format_city_context
from service.game.state_v2 import AffinityTier
from service.game.turn_handler_v2 import (
    AFFINITY_THRESHOLD_TIER1,
    AFFINITY_THRESHOLD_TIER2,
    AFFINITY_TIER_KOREAN_LABELS,
    AFFINITY_TIER_THRESHOLD_ACQUAINTANCE,
    AFFINITY_TIER_THRESHOLD_CLOSE_FRIEND,
    AFFINITY_TIER_THRESHOLD_FRIEND,
    get_affinity_label,
    get_affinity_tier,
)

# ─── AffinityTier enum ───


class TestAffinityTierEnum:
    def test_stranger_value(self) -> None:
        assert AffinityTier.STRANGER.value == "stranger"

    def test_acquaintance_value(self) -> None:
        assert AffinityTier.ACQUAINTANCE.value == "acquaintance"

    def test_friend_value(self) -> None:
        assert AffinityTier.FRIEND.value == "friend"

    def test_close_friend_value(self) -> None:
        assert AffinityTier.CLOSE_FRIEND.value == "close_friend"

    def test_total_count_4(self) -> None:
        assert len(list(AffinityTier)) == 4


# ─── Thresholds ───


class TestThresholds:
    def test_friend_50(self) -> None:
        assert AFFINITY_TIER_THRESHOLD_FRIEND == 50

    def test_close_friend_75(self) -> None:
        assert AFFINITY_TIER_THRESHOLD_CLOSE_FRIEND == 75

    def test_acquaintance_25(self) -> None:
        assert AFFINITY_TIER_THRESHOLD_ACQUAINTANCE == 25

    def test_acquaintance_aliases_9_13_tier1(self) -> None:
        """ACQUAINTANCE 임계값 본격 9.13 TIER1 alias (★ single source)."""
        assert AFFINITY_TIER_THRESHOLD_ACQUAINTANCE == AFFINITY_THRESHOLD_TIER1

    def test_friend_aliases_9_13_tier2(self) -> None:
        """FRIEND 임계값 본격 9.13 TIER2 alias (★ single source)."""
        assert AFFINITY_TIER_THRESHOLD_FRIEND == AFFINITY_THRESHOLD_TIER2


# ─── get_affinity_tier boundary ───


class TestGetAffinityTier:
    def test_negative_returns_stranger(self) -> None:
        """음수 본격 STRANGER (★ 9.12 floor 0 본격 본격 보장)."""
        assert get_affinity_tier(-5) == AffinityTier.STRANGER.value

    def test_zero_stranger(self) -> None:
        assert get_affinity_tier(0) == AffinityTier.STRANGER.value

    def test_24_stranger(self) -> None:
        """STRANGER 상한 경계."""
        assert get_affinity_tier(24) == AffinityTier.STRANGER.value

    def test_25_acquaintance(self) -> None:
        """ACQUAINTANCE 하한 경계 (★ 9.13 TIER1 정합)."""
        assert get_affinity_tier(25) == AffinityTier.ACQUAINTANCE.value

    def test_49_acquaintance(self) -> None:
        """ACQUAINTANCE 상한 경계."""
        assert get_affinity_tier(49) == AffinityTier.ACQUAINTANCE.value

    def test_50_friend(self) -> None:
        """FRIEND 하한 경계 (★ 9.13 TIER2 정합)."""
        assert get_affinity_tier(50) == AffinityTier.FRIEND.value

    def test_74_friend(self) -> None:
        """FRIEND 상한 경계."""
        assert get_affinity_tier(74) == AffinityTier.FRIEND.value

    def test_75_close_friend(self) -> None:
        """CLOSE_FRIEND 하한 경계 (★ 162화 절친 본격)."""
        assert get_affinity_tier(75) == AffinityTier.CLOSE_FRIEND.value

    def test_100_close_friend(self) -> None:
        """AFFINITY_MAX 본격 CLOSE_FRIEND (★ 643화 cap)."""
        assert get_affinity_tier(100) == AffinityTier.CLOSE_FRIEND.value

    def test_high_affinity_still_close_friend(self) -> None:
        """100 초과 본격 CLOSE_FRIEND 본격 본격 (★ defensive)."""
        assert get_affinity_tier(200) == AffinityTier.CLOSE_FRIEND.value


# ─── get_affinity_label (한국어) ───


class TestGetAffinityLabel:
    def test_stranger_label(self) -> None:
        assert get_affinity_label(0) == "지인"
        assert get_affinity_label(24) == "지인"

    def test_acquaintance_label(self) -> None:
        assert get_affinity_label(25) == "동료"
        assert get_affinity_label(49) == "동료"

    def test_friend_label(self) -> None:
        assert get_affinity_label(50) == "친구"
        assert get_affinity_label(74) == "친구"

    def test_close_friend_label(self) -> None:
        """162화 정합 본격 '절친'."""
        assert get_affinity_label(75) == "절친"
        assert get_affinity_label(100) == "절친"

    def test_negative_label(self) -> None:
        """음수 본격 STRANGER label."""
        assert get_affinity_label(-1) == "지인"


# ─── AFFINITY_TIER_KOREAN_LABELS ───


class TestKoreanLabels:
    def test_all_tiers_have_label(self) -> None:
        for tier in AffinityTier:
            assert tier.value in AFFINITY_TIER_KOREAN_LABELS

    def test_label_count_4(self) -> None:
        assert len(AFFINITY_TIER_KOREAN_LABELS) == 4

    def test_close_friend_uses_chinjin(self) -> None:
        """162화 본문 본격 '절친' 본격 정합."""
        assert (
            AFFINITY_TIER_KOREAN_LABELS[AffinityTier.CLOSE_FRIEND.value]
            == "절친"
        )

    def test_stranger_uses_jiin(self) -> None:
        assert (
            AFFINITY_TIER_KOREAN_LABELS[AffinityTier.STRANGER.value]
            == "지인"
        )

    def test_acquaintance_uses_dongnyo(self) -> None:
        assert (
            AFFINITY_TIER_KOREAN_LABELS[AffinityTier.ACQUAINTANCE.value]
            == "동료"
        )

    def test_friend_uses_chingu(self) -> None:
        assert (
            AFFINITY_TIER_KOREAN_LABELS[AffinityTier.FRIEND.value]
            == "친구"
        )


# ─── gm_agent prompt 본격 label 표시 ───


def _city_ctx_with_npc(npc_id: str, affinity: int) -> dict[str, Any]:
    """라비기온 7구역 광장 ctx — aenar/erwen/misha NPCs 본격 sub_area."""
    return {
        "v2_initial_location": {
            "realm": "도시",
            "city_id": "rapdonia",
            "sub_area": "district_7_plaza",
        },
        "v2_world_state": {
            "npc_affinities": {npc_id: affinity},
        },
    }


class TestPromptShowsAffinityLabel:
    def test_close_friend_label_shown(self) -> None:
        """호감도 100 NPC 본격 prompt 본격 '절친' label."""
        ctx = _city_ctx_with_npc("aenar", 100)
        prompt = _format_city_context(ctx)
        # 본격 host sub_area 본격 NPC display 본격 본격 label
        assert "절친" in prompt
        assert "호감도 100" in prompt

    def test_stranger_label_shown(self) -> None:
        ctx = _city_ctx_with_npc("aenar", 0)
        prompt = _format_city_context(ctx)
        assert "지인" in prompt
        assert "호감도 0" in prompt

    def test_friend_label_shown(self) -> None:
        ctx = _city_ctx_with_npc("aenar", 50)
        prompt = _format_city_context(ctx)
        assert "친구" in prompt
        assert "호감도 50" in prompt

    def test_acquaintance_label_shown(self) -> None:
        ctx = _city_ctx_with_npc("aenar", 25)
        prompt = _format_city_context(ctx)
        assert "동료" in prompt
        assert "호감도 25" in prompt
