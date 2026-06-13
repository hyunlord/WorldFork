"""V3 게임 통합 MVP — RTwP 세션 API 테스트.

start → tick(자율, 코드) → command(지시, LLM mock) → event(영구) 흐름. 분기점 노출,
ASCII 렌더, 영구 반영(재방문 막힘/관계)이 HTTP로 작동하는가.
"""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.api.v3_session_router import _SESSIONS, router


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _client() -> TestClient:
    _SESSIONS.clear()
    return TestClient(_app())


def test_start_returns_party() -> None:
    c = _client()
    r = c.post("/api/v3/session/start")
    assert r.status_code == 200
    body = r.json()
    assert len(body["party"]) == 3
    assert {m["name"] for m in body["party"]} == {"투르윈", "셰인", "가론"}
    # 탑다운 픽셀 렌더 데이터(ASCII 폐기) — 타일맵 크기만큼 rows.
    dungeon = body["dungeon"]
    assert len(dungeon["rows"]) == 8  # 수정 동굴 세로 8
    assert all(len(r) == 12 for r in dungeon["rows"])  # 가로 12
    types = {t["type"] for row in dungeon["rows"] for t in row}
    assert "player" in types and "wall" in types and "floor" in types


def test_tick_advances_autonomously() -> None:
    c = _client()
    sid = c.post("/api/v3/session/start").json()["session_id"]
    r = c.post("/api/v3/session/tick", json={"session_id": sid, "steps": 3})
    assert r.status_code == 200
    assert r.json()["tick"] == 3  # 3틱 진행(코드 자율)


def test_spawn_triggers_branch() -> None:
    c = _client()
    sid = c.post("/api/v3/session/start").json()["session_id"]
    body = c.post(
        "/api/v3/session/tick", json={"session_id": sid, "spawn_enemy": True}
    ).json()
    assert len(body["enemies"]) >= 1  # 고블린 다수 스폰(멜레 도달 위해)
    assert "new_enemy" in body["branch"] or "conflict" in body["branch"]


def test_command_member_interprets() -> None:
    c = _client()
    sid = c.post("/api/v3/session/start").json()["session_id"]
    fake = MagicMock()
    fake.generate_json.return_value = MagicMock(
        parsed={"reaction": "comply", "action": "scout", "reason": "근거", "speech": "살피겠소."}
    )
    with patch("service.sim.disposition_command.pivotal_gm_client", return_value=fake):
        r = c.post(
            "/api/v3/session/command",
            json={"session_id": sid, "target": "셰인", "text": "정찰해"},
        )
    assert r.status_code == 200
    shane = next(m for m in r.json()["party"] if m["name"] == "셰인")
    assert shane["order"] == "scout"  # 지시 반영


def test_command_unknown_member_404() -> None:
    c = _client()
    sid = c.post("/api/v3/session/start").json()["session_id"]
    fake = MagicMock()
    fake.generate_json.return_value = MagicMock(
        parsed={"reaction": "comply", "action": "follow", "reason": "x", "speech": "y"}
    )
    with patch("service.sim.disposition_command.pivotal_gm_client", return_value=fake):
        r = c.post(
            "/api/v3/session/command",
            json={"session_id": sid, "target": "없는이", "text": "x"},
        )
    assert r.status_code == 404


def test_event_permanence_reflected() -> None:
    c = _client()
    sid = c.post("/api/v3/session/start").json()["session_id"]
    fake = MagicMock()
    fake.generate_json.return_value = MagicMock(
        parsed={
            "permanent": True, "kind": "flag", "subject": "x",
            "content": "무너짐", "relationship_delta": 0,
        }
    )
    with patch("service.sim.world_memory.pivotal_gm_client", return_value=fake):
        r = c.post(
            "/api/v3/session/event",
            json={
                "session_id": sid, "action": "천장을 무너뜨렸다",
                "outcome": "붕괴", "subject": "북쪽통로",
            },
        )
    assert r.status_code == 200
    assert r.json()["flags"]["북쪽통로"] == "무너짐"  # 영구 반영


def test_kill_awards_mana_and_essence() -> None:
    # 처치 → 마석(소지금)·정수가 인벤에 쌓이고 RenderState에 노출되는가.
    c = _client()
    sid = c.post("/api/v3/session/start").json()["session_id"]
    c.post("/api/v3/session/tick", json={"session_id": sid, "spawn_enemy": True})
    # 결정적 처치 — 적 HP를 1로 낮춰 다음 틱에 파티가 정리.
    for e in _SESSIONS[sid].world.enemies:
        e.hp = 1
    body = c.post("/api/v3/session/tick", json={"session_id": sid, "steps": 1}).json()
    assert body["stones"] >= 20  # 9등급 마석 ≈ 20스톤
    assert body["mana_stones"]  # 마석 등급 기록
    assert "고블린 정수" in body["essences"]  # 정수 수집(표시만)


def test_unknown_session_404() -> None:
    c = _client()
    assert c.get("/api/v3/session/없는세션").status_code == 404
