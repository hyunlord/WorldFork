"""A3.1 — 자유 입력 효과 매퍼(scene_effect) 단위 테스트.

★ 효과=코드 파생·결정적·LLM 무관. 단조 progress 불변식·explore 디테일 공개·줍기 아이템·
대화 관계·불확실 보수적 기본을 검증. (전환 자체는 A3.2 — 여기선 효과만.)
"""

from __future__ import annotations

from service.api.schemas.freeform_action import IntentMatch
from service.sim.opening_canon import Beat, scene_details
from service.sim.scene_effect import (
    _POLICY,
    BEAT_THRESHOLD,
    map_effect,
    pull_flavor,
)


def _intent(action: str | None, conf: float = 0.95) -> IntentMatch:
    return IntentMatch(matched_action=action, confidence=conf, reason="t")


class TestMonotonicInvariant:
    def test_all_effects_advance_progress(self) -> None:
        # ★ no-stuck 토대 — 어떤 입력이든 progress_delta ≥ 1(진행도 감소 없음).
        cases = [
            _intent("explore"),
            _intent("move"),
            _intent("dialogue"),
            _intent(None),  # 불확실
            None,  # intent 분류 자체 실패
        ]
        for it in cases:
            eff = map_effect(it, "무언가 한다", Beat.DUNGEON_ENTRY, [])
            assert eff.progress_delta >= 1


class TestExplore:
    def test_reveals_next_detail_and_dedups(self) -> None:
        seen: list[str] = []
        eff1 = map_effect(_intent("explore"), "살핀다", Beat.DUNGEON_ENTRY, seen)
        assert eff1.kind == "explore"
        assert eff1.newly_discovered  # 디테일 공개
        assert eff1.confirmed_lines  # GM에 넘길 서술 재료
        seen.extend(eff1.newly_discovered)
        # 다음 explore는 다른 디테일(반복 금지)
        eff2 = map_effect(_intent("explore"), "더 살핀다", Beat.DUNGEON_ENTRY, seen)
        assert eff2.newly_discovered and eff2.newly_discovered != eff1.newly_discovered

    def test_exhausted_details_soft_line(self) -> None:
        all_keys = [d.key for d in scene_details(Beat.DUNGEON_ENTRY)]
        eff = map_effect(_intent("explore"), "또 살핀다", Beat.DUNGEON_ENTRY, all_keys)
        assert eff.newly_discovered == []  # 더 공개할 것 없음
        assert eff.confirmed_lines  # 그래도 빈 손 아님(소프트 라인)
        assert eff.progress_delta >= 1


class TestTake:
    def test_take_grants_code_owned_item_only(self) -> None:
        # ★ 줍기는 코드 소유 SceneDetail.item만(임의 날조 0).
        eff = map_effect(_intent("explore"), "수정 파편을 집어 챙긴다", Beat.DUNGEON_ENTRY, [])
        assert eff.kind == "take"
        assert eff.inventory_add == ["수정 파편"]
        assert eff.newly_discovered  # 줍힌 디테일은 공개 처리(반복 방지)

    def test_take_without_item_is_conservative(self) -> None:
        # 줍을 코드 아이템이 없는 비트 → 아이템 0(과잉 부여 금지), progress만.
        eff = map_effect(_intent(None), "바닥을 뒤져 챙긴다", Beat.COMING_OF_AGE, [])
        assert eff.kind == "take"
        assert eff.inventory_add == []
        assert eff.progress_delta >= 1


class TestDialogueAndDefault:
    def test_dialogue_nudges_relationship_when_companion(self) -> None:
        eff = map_effect(
            _intent("dialogue"), "말을 건다", Beat.DUNGEON_ENTRY, [], kaira_name="카이라"
        )
        assert eff.relationship_delta == {"카이라": 1}
        # 대화는 캐논 진행엔 모듈(전진보다 작다)
        assert eff.progress_delta < _POLICY.advance

    def test_dialogue_no_companion_no_relationship(self) -> None:
        eff = map_effect(_intent("dialogue"), "혼잣말한다", Beat.COMING_OF_AGE, [], kaira_name="")
        assert eff.relationship_delta == {}

    def test_uncertain_is_pure_narration(self) -> None:
        # 불확실 → 최소 progress + confirmed 없음(GM 순수 서술, 과잉 부여 0).
        eff = map_effect(_intent(None, conf=0.2), "춤을 춘다", Beat.DUNGEON_ENTRY, [])
        assert eff.kind == "default"
        assert eff.confirmed_lines == []
        assert eff.inventory_add == [] and eff.relationship_delta == {}
        assert eff.progress_delta >= 1

    def test_advance_is_main_driver(self) -> None:
        eff = map_effect(_intent("move"), "더 깊이 간다", Beat.DUNGEON_ENTRY, [])
        assert eff.kind == "advance"
        assert eff.progress_delta == _POLICY.advance


class TestPullFlavor:
    def test_progress_gated_beat_strengthens_with_progress(self) -> None:
        thr = BEAT_THRESHOLD[Beat.DUNGEON_ENTRY]
        low = pull_flavor(Beat.DUNGEON_ENTRY, 0)
        mid = pull_flavor(Beat.DUNGEON_ENTRY, int(thr * 0.5))
        high = pull_flavor(Beat.DUNGEON_ENTRY, thr)
        assert low and mid and high
        assert low != mid != high  # 진행도별로 견인 강도가 다른 서술
        # ★ 수치 노출 금지(메타 차단) — 힌트에 진행도 숫자가 들어가지 않는다
        for txt in (low, mid, high):
            assert not any(ch.isdigit() for ch in txt)

    def test_non_gated_beat_no_pull(self) -> None:
        # 임계 없는 비트(성인식)는 견인 힌트 없음
        assert pull_flavor(Beat.COMING_OF_AGE, 50) is None
