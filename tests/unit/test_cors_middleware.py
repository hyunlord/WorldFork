"""CORS middleware tests — frontend → API access (★ Tailscale + localhost).

본 commit (★ manual playthrough 차단 해소):
- Tailscale IP (100.70.109.50:4000) → API CORS allow
- localhost:4000 + 127.0.0.1:4000 → API CORS allow
- preflight OPTIONS 200/204 + access-control-allow-origin header
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from service.api.app import _parse_cors_origins, app

# ─── _parse_cors_origins default 본격 검증 ───


class TestParseCorsOriginsDefault:
    def test_default_includes_localhost_4000(self) -> None:
        origins = _parse_cors_origins()
        assert "http://localhost:4000" in origins

    def test_default_includes_127_4000(self) -> None:
        origins = _parse_cors_origins()
        assert "http://127.0.0.1:4000" in origins

    def test_default_includes_tailscale_4000(self) -> None:
        """본인 Mac browser 본격 manual playthrough access."""
        origins = _parse_cors_origins()
        assert "http://100.70.109.50:4000" in origins

    def test_default_includes_tailscale_3000(self) -> None:
        origins = _parse_cors_origins()
        assert "http://100.70.109.50:3000" in origins

    def test_default_includes_localhost_3000(self) -> None:
        origins = _parse_cors_origins()
        assert "http://localhost:3000" in origins


# ─── CORS response header 본격 ───


class TestCORSHeaders:
    def test_tailscale_origin_allowed_on_state(self) -> None:
        """Tailscale IP origin 본격 access-control-allow-origin 본격."""
        client = TestClient(app)
        response = client.get(
            "/api/v2/state",
            headers={"Origin": "http://100.70.109.50:4000"},
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://100.70.109.50:4000"
        )

    def test_localhost_4000_allowed_on_state(self) -> None:
        client = TestClient(app)
        response = client.get(
            "/api/v2/state",
            headers={"Origin": "http://localhost:4000"},
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:4000"
        )

    def test_127_0_0_1_4000_allowed_on_state(self) -> None:
        client = TestClient(app)
        response = client.get(
            "/api/v2/state",
            headers={"Origin": "http://127.0.0.1:4000"},
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://127.0.0.1:4000"
        )

    def test_unknown_origin_not_allowed(self) -> None:
        """unlisted origin 본격 access-control-allow-origin header X."""
        client = TestClient(app)
        response = client.get(
            "/api/v2/state",
            headers={"Origin": "http://evil.example.com"},
        )
        # 본격 응답 본격 200 (★ 본격 server-side 차단 X)
        # 본격 header 본격 echo X (★ browser side 본격 차단)
        assert response.headers.get("access-control-allow-origin") != (
            "http://evil.example.com"
        )


# ─── preflight OPTIONS 본격 ───


class TestCORSPreflight:
    def test_preflight_options_tailscale(self) -> None:
        client = TestClient(app)
        response = client.options(
            "/api/v2/state",
            headers={
                "Origin": "http://100.70.109.50:4000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204)
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://100.70.109.50:4000"
        )

    def test_preflight_options_localhost(self) -> None:
        client = TestClient(app)
        response = client.options(
            "/api/v2/state",
            headers={
                "Origin": "http://localhost:4000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code in (200, 204)
        assert "access-control-allow-origin" in response.headers

    def test_preflight_returns_allow_methods(self) -> None:
        client = TestClient(app)
        response = client.options(
            "/api/v2/state",
            headers={
                "Origin": "http://100.70.109.50:4000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # allow_methods=["*"] 본격 본격 본격 본격 actual methods 본격 echo
        assert "access-control-allow-methods" in response.headers


# ─── env var override 본격 ───


class TestParseCorsOriginsEnvOverride:
    def test_env_var_overrides_default(self, monkeypatch: object) -> None:
        """ALLOWED_ORIGINS env 본격 default 본격 override."""
        import os

        # monkeypatch 본격 fixture 본격 X 본격 setenv 본격 본격 본격
        os.environ["ALLOWED_ORIGINS"] = "http://only-this.com"
        try:
            origins = _parse_cors_origins()
            assert origins == ["http://only-this.com"]
        finally:
            del os.environ["ALLOWED_ORIGINS"]

    def test_env_var_comma_separated(self) -> None:
        import os

        os.environ["ALLOWED_ORIGINS"] = (
            "http://a.com,http://b.com,http://c.com"
        )
        try:
            origins = _parse_cors_origins()
            assert origins == [
                "http://a.com",
                "http://b.com",
                "http://c.com",
            ]
        finally:
            del os.environ["ALLOWED_ORIGINS"]

    def test_env_var_empty_uses_default(self) -> None:
        import os

        # 본격 env 본격 본격 본격 default 본격 본격
        if "ALLOWED_ORIGINS" in os.environ:
            del os.environ["ALLOWED_ORIGINS"]
        origins = _parse_cors_origins()
        assert "http://100.70.109.50:4000" in origins
