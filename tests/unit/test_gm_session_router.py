"""AI GM 슬라이스 Phase 1·2 — /api/gm 세션 라우터 테스트.

start → 비트1 구조화 출력. act → ★ 혼합 입력(선택지/자유) + state_delta 실제 구동 +
★ 코드 구동 비트 전환(LLM 의존 폐기) + ★ 카이라 성향 반응 노출. LLM은 라우터 네임스페이스
(gm_beat/interpret_command/classify_intent)를 patch해 결정적으로.
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.api.gm_session_router import _SESSIONS, router
from service.api.schemas.freeform_action import IntentMatch
from service.sim.disposition import DispoAction
from service.sim.disposition_command import CommandReaction, CommandResponse
from service.sim.narrative_gm import GMBeatResult, GMChoice, GMStateDelta


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _client() -> TestClient:
    _SESSIONS.clear()
    return TestClient(_app())


def _beat(
    narration: str = "「성인식이 시작됩니다.」 부족장이 나를 호명했다.",
    flags: dict[str, str] | None = None,
    hp_change: int = 0,
    rel: dict[str, int] | None = None,
) -> GMBeatResult:
    return GMBeatResult(
        narration=narration,
        choices=[GMChoice("axe", "양손도끼를 든다"), GMChoice("sword", "대검을 든다")],
        state_delta=GMStateDelta(
            flags=flags or {}, hp_change=hp_change, relationship_delta=rel or {}
        ),
    )


def _reaction() -> CommandResponse:
    return CommandResponse(
        CommandReaction.ADAPT,
        DispoAction.CHARGE,
        "신중함은 사치다",
        "물러서다니, 내 도끼가 먼저 나선다!",
    )


def test_start_opens_beat1_no_companion_reaction() -> None:
    c = _client()
    started = _beat(flags={"성인식": "진행"})
    with patch("service.api.gm_session_router.gm_beat", return_value=started):
        body = c.post("/api/gm/session/start").json()
    assert body["beat"] == "coming_of_age"
    assert len(body["choices"]) == 2
    assert body["flags"]["성인식"] == "진행"  # state_delta 반영
    assert body["party"][0]["name"] == "카이라"  # 변환명(화면 unmask)
    assert body["companion_reaction"] is None  # 성인식엔 카이라 미동행


def test_weapon_choice_advances_and_reacts() -> None:
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    # 무기 선택 → 무기 확정 + 코드 전환(coming_of_age→dungeon_entry) + 카이라 반응(동행 시작)
    dungeon_beat = _beat(narration="수정이 빛나는 미궁 1층.", hp_change=-3, rel={"카이라": 5})
    with patch("service.api.gm_session_router.gm_beat", return_value=dungeon_beat), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"}
        ).json()
    assert body["weapon"] == "양손도끼"  # 결정적 확정
    assert body["beat"] == "dungeon_entry"  # ★ 코드 전환(무기 확정 = 성인식 완료)
    assert body["hp"] == 117  # state_delta hp_change -3 구동
    assert body["relationships"]["카이라"] == 5
    # ★ 카이라 성향 반응 노출(차별점)
    cr = body["companion_reaction"]
    assert cr is not None and cr["reaction"] == "adapt" and cr["action"] == "charge"
    assert "도끼" in cr["speech"]


def test_free_input_mechanical_advances_dungeon() -> None:
    # 미궁 진입 비트에서 자유 입력 "북쪽으로 간다" → mechanical move → entered → first_encounter
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})  # →dungeon
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "북쪽으로 간다"}
        ).json()
    assert _SESSIONS[sid].world.flags.get("entered_floor1") == "true"
    assert body["beat"] == "first_encounter"  # ★ 코드 전환(진입 의도)


def test_first_encounter_no_advance_without_kill() -> None:
    # 첫 조우 → 적 처치(first_foe_resolved) 전엔 코드 전환 안 함(Phase 3가 설정).
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
        c.post("/api/gm/session/act", json={"session_id": sid, "free_text": "북쪽으로 간다"})
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "도끼로 벤다"}
        ).json()
    assert body["beat"] == "first_encounter"  # 처치 전 → 그대로


def test_free_input_unclassified_uses_classify_intent() -> None:
    # mechanical 미분류 자유 입력 → classify_intent(LLM, patch) 호출됨(장면 내 해석).
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    fake_intent = IntentMatch(matched_action=None, confidence=0.3, reason="자유")
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.classify_intent", return_value=fake_intent
    ) as ci:
        c.post(
            "/api/gm/session/act",
            json={"session_id": sid, "free_text": "부족장에게 농담을 던진다"},
        )
    ci.assert_called_once()  # mechanical 미분류 → LLM 해석 fallback


def test_combat_round_then_aftermath() -> None:
    # 첫 조우 진입 → 전투 라운드(코드 판정) → 처치 → 마무리(AFTERMATH) 전환 + 드롭.
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()), patch(
        "service.api.gm_session_router.interpret_command", return_value=_reaction()
    ):
        c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})  # →dungeon
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "미궁으로 들어간다"}
        ).json()
    assert body["beat"] == "first_encounter"
    assert body["foe"] is not None and body["foe"]["name"] == "고블린"  # 적 등장
    # 전투 라운드 — resolve_round patch(처치 결과)로 결정적
    from service.sim.narrative_combat import RoundResult

    killed = RoundResult(
        lines=["투르윈의 양손도끼가 고블린에게 40 피해 (치명타!)", "「고블린을 쓰러뜨렸다.」"],
        player_hp=120,
        player_status=[],
        foe_hp=0,
        kaira_reaction=_reaction(),
        foe_defeated=True,
        drops=["「9등급 마석 획득 — +20 스톤」"],
        illustration="ui_combat_vfx_axe_strike",
    )

    def _kill(**kw: object) -> RoundResult:
        kw["inv"].stones += 20  # type: ignore[union-attr,operator]
        return killed

    with patch("service.api.gm_session_router.resolve_round", side_effect=_kill), patch(
        "service.api.gm_session_router.gm_beat", return_value=_beat(narration="고블린이 쓰러졌다.")
    ):
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "도끼로 벤다"}
        ).json()
    assert body["beat"] == "aftermath"  # ★ 처치 → 코드 전환(4비트 완결)
    assert body["foe"] is None
    assert body["stones"] >= 20  # 드롭 반영
    assert body["illustration"] == "ui_combat_vfx_axe_strike"


def test_act_requires_input() -> None:
    c = _client()
    with patch("service.api.gm_session_router.gm_beat", return_value=_beat()):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    assert c.post("/api/gm/session/act", json={"session_id": sid}).status_code == 400


def test_unknown_session_404() -> None:
    c = _client()
    assert c.get("/api/gm/session/없는세션").status_code == 404
