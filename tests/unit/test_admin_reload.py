"""admin canon reload endpoint 검증 (I-B2)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from service.api.app import create_app


def test_admin_canon_reload_ok() -> None:
    """POST /api/admin/canon/reload → 200 + entity_counts."""
    client = TestClient(create_app())
    response = client.post("/api/admin/canon/reload")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "entity_counts" in data
    counts = data["entity_counts"]
    assert counts["characters"] > 0
    assert counts["locations"] > 0
    assert counts["essences"] > 0
    assert counts["races"] > 0
    assert counts["mechanisms"] > 0


def test_admin_canon_reload_total_nonzero() -> None:
    """reload 후 entity 총합 0 초과."""
    client = TestClient(create_app())
    response = client.post("/api/admin/canon/reload")
    counts = response.json()["entity_counts"]
    total = sum(counts.values())
    assert total >= 8000
