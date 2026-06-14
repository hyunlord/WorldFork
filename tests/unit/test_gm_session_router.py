"""AI GM 슬라이스 — /api/gm 세션 라우터 테스트.

★ 코드 권위: 선택지=코드 정의(beat_choices), 비트 전환=코드 exit, 무기/HP/소지금=코드.
GM은 서술만(flags 지어내기 금지 → 빌드/rite 누적 버그 차단). 영구=관계만, PER-RUN=무기/인벤/
run_flags(런마다 리셋). LLM은 라우터 네임스페이스(gm_beat/interpret_command/resolve_round)를 patch.
"""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.api.gm_session_router import _PERSISTENT_WORLD, _SESSIONS, router
from service.api.schemas.freeform_action import IntentMatch
from service.sim.disposition import DispoAction
from service.sim.disposition_command import CommandReaction, CommandResponse
from service.sim.narrative_combat import RoundResult
from service.sim.narrative_gm import GMBeatResult, GMStateDelta


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _client() -> TestClient:
    _SESSIONS.clear()
    # 영구 세계(관계)만 격리 — PER-RUN(인벤/무기/run_flags)은 세션마다 fresh라 리셋 불필요.
    _PERSISTENT_WORLD.flags.clear()
    _PERSISTENT_WORLD.npc_memories.clear()
    _PERSISTENT_WORLD.relationships.clear()
    return TestClient(_app())


def _beat(narration: str = "「성인식이 시작됩니다.」 부족장이 나를 호명했다.",
          rel: dict[str, int] | None = None) -> GMBeatResult:
    # ★ GM은 서술만 — choices/flags/hp 없음. 관계 델타만 선택적.
    return GMBeatResult(
        narration=narration,
        state_delta=GMStateDelta(relationship_delta=rel or {}),
    )


def _reaction(action: DispoAction = DispoAction.CHARGE) -> CommandResponse:
    return CommandResponse(CommandReaction.ADAPT, action, "신중함은 사치", "내 도끼가 먼저다!")


def test_start_code_choices_no_gm_flags() -> None:
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        body = c.post("/api/gm/session/start").json()
    assert body["beat"] == "coming_of_age"
    # ★ 코드 정의 선택지(즉시·결정적) — 원작 무기군 3개, id=axe/hammer/greatsword
    ids = {ch["id"] for ch in body["choices"]}
    assert ids == {"axe", "hammer", "greatsword"}
    assert body["flags"] == {}  # ★ GM이 flag 안 만듦(오염 0)
    assert body["weapon"] == "" and body["stones"] == 0  # PER-RUN 초기값
    assert body["companion_reaction"] is None  # 성인식엔 카이라 미동행


def test_weapon_choice_commits_and_advances() -> None:
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    rel_beat = _beat(rel={"카이라": 5})
    with patch("service.api.gm_session_router.gm_beat", return_value=rel_beat), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        body = c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"}).json()
    assert body["weapon"] == "양손도끼"  # 결정적 확정(코드)
    assert body["beat"] == "dungeon_entry"  # 코드 전환
    assert body["flags"].get("rite_passed") == "true"  # 코드가 성인식 완료 기록
    assert body["relationships"]["카이라"] == 5  # GM 관계 델타(영구)
    # 무기 중복 금지 — 한 무기만
    assert "대검" not in body["weapon"] and "방패" not in str(body["items"])


def test_free_input_accumulates_to_encounter_and_spawns_foe() -> None:
    # ★ A3.2 — 단일 입력은 강제 전진 안 함(누적 끌개). 전진 반복으로 임계 도달 시 자연 전환.
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
        # 첫 전진 1회로는 전환 안 됨(임계 100 > advance 40 — 머무를 자유)
        b1 = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "북쪽으로 나아간다"}
        ).json()
        assert b1["beat"] == "dungeon_entry"
        # 전진 누적 → 임계 도달 시 자연 전환(최대 8회 — property 성격)
        body = b1
        for _ in range(8):
            if body["beat"] == "first_encounter":
                break
            body = c.post(
                "/api/gm/session/act",
                json={"session_id": sid, "free_text": "북쪽으로 더 나아간다"},
            ).json()
    assert body["beat"] == "first_encounter"
    assert body["foe"] is not None and body["foe"]["name"] == "고블린"


def test_combat_round_survive_stays() -> None:
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    survive = RoundResult(
        lines=["투르윈의 양손도끼가 고블린에게 16 피해"], player_hp=110, player_status=[],
        foe_hp=20, kaira_reaction=_reaction(), foe_defeated=False, drops=[],
        illustration="ui_combat_monster_goblin",
    )
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ), patch("service.api.gm_session_router.resolve_round", return_value=survive):
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
        for _ in range(5):  # 누적 끌개 — 전진 반복으로 첫 조우 진입(A3.2)
            r = c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "advance"})
            if r.json()["beat"] == "first_encounter":
                break
        body = c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "charge"}).json()
    assert body["beat"] == "first_encounter"  # 처치 전 → 그대로
    assert body["hp"] == 110  # 코드 판정 반영


def test_combat_kill_to_aftermath_with_drop() -> None:
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    killed = RoundResult(
        lines=["「고블린을 쓰러뜨렸다.」"], player_hp=120, player_status=[], foe_hp=0,
        kaira_reaction=_reaction(), foe_defeated=True,
        drops=["「9등급 마석 획득 — +20 스톤」"], illustration="ui_combat_vfx_axe_strike",
    )

    def _kill(**kw: object) -> RoundResult:
        inv = kw["inv"]
        inv.stones += 20  # type: ignore[union-attr,operator]
        return killed

    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ), patch("service.api.gm_session_router.resolve_round", side_effect=_kill):
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
        for _ in range(5):  # 누적 끌개 — 전진 반복으로 첫 조우 진입(A3.2)
            r = c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "advance"})
            if r.json()["beat"] == "first_encounter":
                break
        body = c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "charge"}).json()
    assert body["beat"] == "aftermath"  # ★ 처치 → 코드 전환(4비트 완결)
    assert body["foe"] is None and body["stones"] >= 20


def test_persistent_relationships_perrun_reset() -> None:
    # ★ 관계는 영구(이월), 무기·run_flags·소지금은 PER-RUN(리셋).
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid1 = c.post("/api/gm/session/start").json()["session_id"]
    rel_beat = _beat(rel={"카이라": 7})
    with patch("service.api.gm_session_router.gm_beat", return_value=rel_beat), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        c.post("/api/gm/session/act", json={"session_id": sid1, "choice_id": "axe"})
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        body2 = c.post("/api/gm/session/start").json()
    assert body2["relationships"].get("카이라") == 7  # 관계 이월(영구)
    assert body2["weapon"] == "" and body2["flags"] == {}  # PER-RUN 리셋(무기·진행 flag)
    assert body2["beat"] == "coming_of_age"


def test_free_input_unclassified_uses_classify_intent() -> None:
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    fake = IntentMatch(matched_action=None, confidence=0.3, reason="자유")
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.classify_intent", return_value=fake
    ) as ci:
        c.post(
            "/api/gm/session/act",
            json={"session_id": sid, "free_text": "부족장에게 농담을 던진다"},
        )
    ci.assert_called_once()


def test_free_explore_changes_state_and_feeds_confirmed() -> None:
    # ★ A3.1 — 비전환 자유 입력(둘러보기)도 상태를 바꾸고(progress), 코드 확정 효과를 GM에 전달.
    c = _client()
    gm = MagicMock(return_value=_beat())
    with patch("service.api.gm_session_router.gm_beat", gm):
        sid = c.post("/api/gm/session/start").json()["session_id"]
        with patch("service.api.gm_session_router.interpret_command", return_value=_reaction()):
            c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
            gm.reset_mock()
            body = c.post(
                "/api/gm/session/act",
                json={"session_id": sid, "free_text": "주변을 둘러본다"},
            ).json()
    assert body["beat"] == "dungeon_entry"  # explore는 전환 안 함(머무를 자유)
    assert int(body["flags"]["scene_progress"]) >= 1  # ★ 0 변화 아님(progress 누적)
    # ★ 코드 확정 효과(공개된 디테일 + 카이라 반응)가 confirmed로 GM에 전달
    _, kw = gm.call_args
    assert kw.get("confirmed")


def test_free_explore_dedups_no_repeat() -> None:
    # ★ 같은 둘러보기 반복 → 다른 디테일 공개(discovered 누적, 반복 방지 coherence).
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        sid = c.post("/api/gm/session/start").json()["session_id"]
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
        b1 = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "주변을 둘러본다"}
        ).json()
        b2 = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "다시 살펴본다"}
        ).json()
    # progress가 두 번째에 더 누적(단조)
    assert int(b2["flags"]["scene_progress"]) > int(b1["flags"]["scene_progress"])
    assert b2["beat"] == "dungeon_entry"  # 여전히 머무름(둘러보기는 캐논 진행에 모듈)


def _reach_encounter(c: TestClient, sid: str) -> None:
    """첫 조우까지 전진(누적 끌개) — 테스트 헬퍼. mechanical move만(9B 미의존)."""
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
        for _ in range(10):
            b = c.post(
                "/api/gm/session/act", json={"session_id": sid, "free_text": "북쪽으로 나아간다"}
            ).json()
            if b["beat"] == "first_encounter":
                return
    raise AssertionError("첫 조우 도달 실패")


def test_flee_avoids_combat_to_aftermath() -> None:
    # ★ A3.2 — 첫 조우에서 도주는 전투 대신 마무리로 전진(회피 대안 exit, 막다른 길 0).
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    _reach_encounter(c, sid)
    fake = IntentMatch(matched_action=None, confidence=0.3, reason="자유")
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ), patch("service.api.gm_session_router.classify_intent", return_value=fake):
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "뒤돌아 도망친다"}
        ).json()
    assert body["beat"] == "aftermath"  # 전투 회피 → 마무리로 전진
    assert body["foe"] is None


def test_soft_floor_no_stuck_pure_explore() -> None:
    # ★ A3.2 no-stuck — 디테일 소진 후 둘러보기만 반복해도 soft-floor가 끌어 자연 전환(막다른 길 0).
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    last = 0
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
        moved = False
        for _ in range(20):
            b = c.post(
                "/api/gm/session/act", json={"session_id": sid, "free_text": "주변을 둘러본다"}
            ).json()
            if b["beat"] == "dungeon_entry":  # 단조 progress 확인(감소 없음)
                cur = int(b["flags"]["scene_progress"])
                assert cur >= last
                last = cur
            else:
                moved = True
                break
    assert moved  # 둘러보기만으로도 끝내 전진(stuck 0)


def test_free_text_weapon_naming_commits() -> None:
    # ★ A3.2 — 성인식 무기 확정을 자유 텍스트 명명으로도 허용(choice_id 외).
    c = _client()
    fake = IntentMatch(matched_action=None, confidence=0.3, reason="자유")
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ), patch("service.api.gm_session_router.classify_intent", return_value=fake):
        sid = c.post("/api/gm/session/start").json()["session_id"]
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "대검을 집어 든다"}
        ).json()
    assert body["weapon"] == "대검"  # 자유 텍스트 무기 명명 → 코드 확정
    assert body["beat"] == "dungeon_entry"  # 무기 확정 = 성인식 완료(이벤트 게이트)


def test_take_code_grants_item_suppresses_gm_dup() -> None:
    # ★ A3.1 코드 권위 — 코드 take가 아이템을 준 턴엔 GM inventory_add 무시(이중 부여 0).
    c = _client()
    gm_with_item = GMBeatResult(
        narration="수정 파편을 집어 든다.",
        state_delta=GMStateDelta(inventory_add=["수정 파편"]),  # GM도 같은 물건 시도
    )
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        sid = c.post("/api/gm/session/start").json()["session_id"]
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
    with patch("service.api.gm_session_router.gm_beat", return_value=gm_with_item), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        body = c.post(
            "/api/gm/session/act",
            json={"session_id": sid, "free_text": "바닥의 수정 파편을 주워 챙긴다"},
        ).json()
    assert body["items"].count("수정 파편") == 1  # 코드 1회만(GM 중복 억제)


def test_routine_action_skips_kaira_llm() -> None:
    # ★ A3.3 지연 완화 — 루틴 자유행동(둘러보기)엔 interpret_command(Gemma) 호출 0(0토큰).
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ) as ic:
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "주변을 둘러본다"}
        ).json()
    ic.assert_not_called()  # 루틴 턴 → 카이라 LLM 생략
    assert body["companion_reaction"] is None


def test_directive_action_invokes_kaira_llm() -> None:
    # ★ 지시/분기 턴(카이라에게 말 걸기)엔 interpret_command 호출 — 성향 반응 노출.
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ) as ic:
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "카이라에게 말을 건다"}
        ).json()
    ic.assert_called_once()  # 지시 턴 → 카이라 성향 반응
    assert body["companion_reaction"] is not None


def test_coherence_discovered_injected_to_gm() -> None:
    # ★ A3.3 coherence — 이미 공개된 디테일이 GM 프롬프트(discovered)로 전달돼 반복을 막는다.
    c = _client()
    gm = MagicMock(return_value=_beat())
    with patch("service.api.gm_session_router.gm_beat", gm), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        sid = c.post("/api/gm/session/start").json()["session_id"]
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
        c.post("/api/gm/session/act", json={"session_id": sid, "free_text": "주변을 둘러본다"})
        gm.reset_mock()
        # 두 번째 둘러보기 — 첫 번째에 공개한 디테일이 discovered로 GM에 전달돼야
        c.post("/api/gm/session/act", json={"session_id": sid, "free_text": "다시 살펴본다"})
    _, kw = gm.call_args
    assert kw.get("discovered")  # 이미 공개된 디테일 주입(반복 방지)


def test_act_requires_input() -> None:
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    assert c.post("/api/gm/session/act", json={"session_id": sid}).status_code == 400


def test_unknown_session_404() -> None:
    c = _client()
    assert c.get("/api/gm/session/없는세션").status_code == 404
