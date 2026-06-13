"""AI GM 오프닝 슬라이스 Phase 1 — /api/gm 세션 라우터 테스트.

start → 비트1 구조화 출력(narration/choices). act → ★ state_delta가 실제 세션 상태를
구동(flags·HP·관계·비트 전환 — 장식 아님). 이름은 변환명(화면 unmask는 프론트). LLM은 mock.
"""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.api.gm_session_router import _SESSIONS, router


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _client() -> TestClient:
    _SESSIONS.clear()
    return TestClient(_app())


def _gm(parsed: dict[str, object]) -> MagicMock:
    fake = MagicMock()
    fake.generate_json.return_value = MagicMock(parsed=parsed)
    return fake


_BEAT1 = {
    "narration": "「성인식이 시작됩니다.」 부족장이 나를 호명했다.",
    "choices": [{"id": "axe", "label": "양손도끼를 든다"}, {"id": "sword", "label": "대검을 든다"}],
    "state_delta": {"flags": {"성인식": "진행"}},
}


def test_start_opens_beat1() -> None:
    c = _client()
    with patch("service.sim.narrative_gm.pivotal_gm_client", return_value=_gm(_BEAT1)):
        body = c.post("/api/gm/session/start").json()
    assert body["beat"] == "coming_of_age"
    assert body["narration"].startswith("「성인식")
    assert len(body["choices"]) == 2
    assert body["flags"]["성인식"] == "진행"  # state_delta 반영
    # 동료는 변환명(카이라) — 화면 unmask는 프론트
    assert body["party"][0]["name"] == "카이라"


def test_act_choice_drives_state() -> None:
    c = _client()
    with patch("service.sim.narrative_gm.pivotal_gm_client", return_value=_gm(_BEAT1)):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    # 무기 선택 → state_delta가 flags(무기)·HP·관계·비트 전환을 실제로 구동
    act_delta = {
        "narration": "나는 양손도끼를 잡았다. 묵직한 무게가 손에 익는다.",
        "choices": [{"id": "go", "label": "미궁으로"}, {"id": "wait", "label": "더 살핀다"}],
        "state_delta": {
            "flags": {"무기": "양손도끼", "성인식": "완료"},
            "hp_change": -3,
            "relationship_delta": {"카이라": 5},
            "scene_transition": "dungeon_entry",
        },
    }
    with patch("service.sim.narrative_gm.pivotal_gm_client", return_value=_gm(act_delta)):
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"}
        ).json()
    assert body["weapon"] == "양손도끼"  # 무기 확정(빌드)
    assert body["flags"]["성인식"] == "완료"
    assert body["hp"] == 117  # 120 - 3 (실제 HP 구동)
    assert body["relationships"]["카이라"] == 5  # 관계 구동
    assert body["beat"] == "dungeon_entry"  # 비트 전환(다음 비트로만)


def test_scene_transition_forward_only() -> None:
    # 끌개 순서 보존 — 비트 건너뛰기(coming_of_age → first_encounter)는 무시.
    c = _client()
    with patch("service.sim.narrative_gm.pivotal_gm_client", return_value=_gm(_BEAT1)):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    skip = {
        "narration": "건너뛰기 시도.",
        "choices": [{"id": "a", "label": "ㄱ"}, {"id": "b", "label": "ㄴ"}],
        "state_delta": {"scene_transition": "first_encounter"},  # 2칸 건너뜀
    }
    with patch("service.sim.narrative_gm.pivotal_gm_client", return_value=_gm(skip)):
        body = c.post(
            "/api/gm/session/act", json={"session_id": sid, "free_text": "서두른다"}
        ).json()
    assert body["beat"] == "coming_of_age"  # 건너뛰기 차단 — 그대로


def test_act_requires_input() -> None:
    c = _client()
    with patch("service.sim.narrative_gm.pivotal_gm_client", return_value=_gm(_BEAT1)):
        sid = c.post("/api/gm/session/start").json()["session_id"]
    r = c.post("/api/gm/session/act", json={"session_id": sid})
    assert r.status_code == 400  # choice_id/free_text 없음


def test_unknown_session_404() -> None:
    c = _client()
    assert c.get("/api/gm/session/없는세션").status_code == 404
