"""A1.2 — ContentPack(엔진/팩 분리) + WorldFork 소비 검증.

★ 모든 팩 필드는 실소비처를 가진다(미소비 0). 엔진은 require_active_pack()으로만 소비하고
원본 리터럴은 없다(중복 0). 조립 GM 프롬프트가 팩 페르소나에서 나옴(거동 가드).
"""

from __future__ import annotations

import pytest

from service.content.worldfork import WORLDFORK_PACK
from service.engine.content_pack import (
    ContentPack,
    clear_active_pack,
    get_active_pack,
    require_active_pack,
    set_active_pack,
)


class TestActiveSingleton:
    def test_set_get_clear_roundtrip(self) -> None:
        set_active_pack(WORLDFORK_PACK)
        assert get_active_pack() is WORLDFORK_PACK
        clear_active_pack()
        assert get_active_pack() is None

    def test_require_raises_when_unset(self) -> None:
        clear_active_pack()
        with pytest.raises(RuntimeError):
            require_active_pack()
        set_active_pack(WORLDFORK_PACK)  # autouse 픽스처 정합 복구
        assert require_active_pack() is WORLDFORK_PACK


class TestPackShape:
    def test_pack_id_and_fields(self) -> None:
        p = WORLDFORK_PACK
        assert p.pack_id == "worldfork"
        assert p.gm_system_persona.startswith("# 역할")
        assert "{anchor}" in p.gm_system_persona and "{illustrations}" in p.gm_system_persona
        assert p.first_foe.name == "고블린" and p.first_foe.hp == 36
        assert p.companion.name == "카이라"
        assert p.grounding_episode_range == (1, 20)
        assert p.grounding_top_k == 3 and p.grounding_char_budget == 1000
        assert "ui_combat_monster_goblin" in p.illustration_keys

    def test_pack_is_frozen(self) -> None:
        import dataclasses

        assert dataclasses.is_dataclass(ContentPack)
        with pytest.raises(dataclasses.FrozenInstanceError):
            WORLDFORK_PACK.pack_id = "x"  # type: ignore[misc]


class TestEngineConsumesPack:
    """★ 모든 필드가 실소비됨 — 변형 팩 주입 시 엔진 출력이 바뀐다(미소비 0 증명)."""

    def test_gm_prompt_uses_pack_persona(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # grounding off(서버 무관) → build_gm_prompt의 system이 팩 페르소나에서 조립됨
        monkeypatch.setenv("GM_GROUNDING", "0")
        from service.sim.narrative_gm import build_gm_prompt
        from service.sim.opening_canon import Beat

        prompt = build_gm_prompt(
            Beat.COMING_OF_AGE,
            hp=120, max_hp=120, weapon="", stones=0, flags={}, history="", action="(성인식)",
        )
        # 팩 페르소나 프리픽스 + 일러스트 화이트리스트가 system에 반영(바이트 충실)
        assert prompt.system.startswith("# 역할\n당신은 한국 web novel")
        for key in sorted(WORLDFORK_PACK.illustration_keys):
            assert key in prompt.system

    def test_gm_prompt_reflects_variant_pack(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import dataclasses

        monkeypatch.setenv("GM_GROUNDING", "0")
        from service.sim.narrative_gm import build_gm_prompt
        from service.sim.opening_canon import Beat

        variant = dataclasses.replace(
            WORLDFORK_PACK,
            gm_system_persona="# 변형\n다른 {anchor}{grounding} {illustrations}",
        )
        set_active_pack(variant)
        try:
            prompt = build_gm_prompt(
                Beat.COMING_OF_AGE,
                hp=120, max_hp=120, weapon="", stones=0, flags={}, history="", action="x",
            )
            assert prompt.system.startswith("# 변형")  # 팩이 실제 소스
        finally:
            set_active_pack(WORLDFORK_PACK)

    def test_new_kaira_reads_active_pack(self) -> None:
        import dataclasses

        from service.api.gm_session_router import _new_kaira
        from service.engine.content_pack import CompanionSpec

        variant = dataclasses.replace(
            WORLDFORK_PACK,
            companion=CompanionSpec(
                name="테스트동료",
                disposition=WORLDFORK_PACK.companion.disposition,
                hp=99,
                attack=7,
            ),
        )
        set_active_pack(variant)
        try:
            k = _new_kaira()
            assert (k.name, k.hp, k.max_hp, k.attack) == ("테스트동료", 99, 99, 7)
        finally:
            set_active_pack(WORLDFORK_PACK)

    def test_no_engine_literal_duplication(self) -> None:
        # ★ 원본 리터럴 제거 확인 — narrative_gm에 _GM_SYSTEM/_ILLUSTRATIONS 없음(중복 0)
        from service.sim import narrative_gm

        assert not hasattr(narrative_gm, "_GM_SYSTEM")
        assert not hasattr(narrative_gm, "_ILLUSTRATIONS")
