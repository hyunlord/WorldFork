"""Phase E end-to-end integration tests.

시나리오 + 종족 작업 (commit 1-5) 통합 검증.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from service.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_e2e_bjorn_full_flow(client: TestClient) -> None:
    """BJORN 캐릭터 생성 → state 조회 통합 흐름."""
    resp = client.post("/api/v2/character/create", json={"scenario_mode": "bjorn"})
    assert resp.status_code == 200
    data = resp.json()
    sid = data["session_id"]

    assert data["race"] == "barbarian"
    assert data["scenario_mode"] == "bjorn"
    assert data["hp"] == 120
    assert "방패" in data["starting_narrative"]
    assert "라스카니아" in data["starting_narrative"]

    state = client.get(f"/api/v2/session/{sid}/state").json()
    assert state["race"] == "barbarian"
    assert state["scenario_mode"] == "bjorn"
    assert state["inventory"] == ["방패"]
    assert "라스카니아" in state["location"]
    assert state["player_level"] == 1
    assert state["max_essences"] == 1
    assert state["soul_power"] == 10


def test_e2e_new_explorer_each_race(client: TestClient) -> None:
    """NEW_EXPLORER 5종 캐릭터 생성 통합 검증."""
    cases = [
        ("barbarian", 120, ["도끼"], "도끼"),
        ("human", 100, ["검"], "검"),
        ("dwarf", 110, ["망치"], "망치"),
        ("beastkin", 105, [], "발톱"),
        ("fairy", 80, ["단검"], "단검"),
    ]

    for race_str, expected_hp, expected_inv, narrative_kw in cases:
        resp = client.post(
            "/api/v2/character/create",
            json={"scenario_mode": "new_explorer", "race": race_str},
        )
        assert resp.status_code == 200, f"race={race_str}: {resp.text}"
        data = resp.json()

        assert data["race"] == race_str, f"race mismatch for {race_str}"
        assert data["hp"] == expected_hp, f"hp mismatch for {race_str}"
        assert narrative_kw in data["starting_narrative"], (
            f"race={race_str}: '{narrative_kw}' not in narrative"
        )

        state = client.get(f"/api/v2/session/{data['session_id']}/state").json()
        assert state["inventory"] == expected_inv, f"inventory mismatch for {race_str}"


def test_e2e_fairy_max_essences_2(client: TestClient) -> None:
    """요정 max_essences=2 + soul_power=20 (commit 1 정합)."""
    resp = client.post(
        "/api/v2/character/create",
        json={"scenario_mode": "new_explorer", "race": "fairy"},
    )
    data = resp.json()
    assert data["max_essences"] == 2
    assert data["soul_power"] == 20


def test_e2e_bjorn_ignores_race(client: TestClient) -> None:
    """BJORN + race=fairy → 바바리안 강제 (commit 2 정합)."""
    resp = client.post(
        "/api/v2/character/create",
        json={"scenario_mode": "bjorn", "race": "fairy"},
    )
    data = resp.json()
    assert data["race"] == "barbarian"
    assert data["hp"] == 120
    assert "방패" in data["starting_narrative"]


def test_e2e_session_start_backward_compat(client: TestClient) -> None:
    """기존 /session/start → 200 + 세션 생성 (legacy endpoint 정합)."""
    resp = client.post("/api/v2/session/start", json={})
    assert resp.status_code == 200
    sid = resp.json()["session_id"]

    state = client.get(f"/api/v2/session/{sid}/state").json()
    # SessionState default race/scenario 정합
    assert state["scenario_mode"] == "bjorn"
    assert state["race"] == "barbarian"
    # legacy endpoint 기본값: hp=100, inventory=[] (BJORN 시나리오 default X)
    assert state["current_hp"] == 100


def test_e2e_invalid_inputs(client: TestClient) -> None:
    """invalid scenario_mode / race → 400."""
    resp = client.post(
        "/api/v2/character/create",
        json={"scenario_mode": "invalid_mode"},
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/v2/character/create",
        json={"scenario_mode": "new_explorer", "race": "용인족"},
    )
    assert resp.status_code == 400


def test_e2e_all_races_create_succeed(client: TestClient) -> None:
    """5종 × 2 mode = 10 시나리오 모두 200 응답."""
    for mode in ["bjorn", "new_explorer"]:
        for race in ["barbarian", "human", "dwarf", "beastkin", "fairy"]:
            payload: dict[str, str] = {"scenario_mode": mode}
            if mode == "new_explorer":
                payload["race"] = race
            resp = client.post("/api/v2/character/create", json=payload)
            assert resp.status_code == 200, f"{mode}+{race}: {resp.text}"
