"""FastAPI app (★ Tier 2 D7 게이트 3 W1 + D8 W2 정적 HTML).

★ 단순 골격:
  - /game/start
  - /game/turn
  - /game/state
  - / + /static/* (★ D8 정적 chat UI)
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from service.api.game_routes import router as game_router


def _parse_cors_origins() -> list[str]:
    """CORS allowed origins (★ env var 우선, default = dev 포트들).

    환경변수 ALLOWED_ORIGINS (콤마 구분):
      ALLOWED_ORIGINS="http://localhost:4000,http://100.70.109.50:4000"

    기본값: localhost/127.0.0.1 의 3000 + 4000 (Next.js dev).
    """
    env_value = os.environ.get("ALLOWED_ORIGINS", "").strip()
    if env_value:
        return [origin.strip() for origin in env_value.split(",") if origin.strip()]
    return [
        "http://localhost:3000",
        "http://localhost:4000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4000",
    ]


def create_app() -> FastAPI:
    """FastAPI app 생성."""
    app = FastAPI(
        title="WorldFork API",
        description="한국어 텍스트 어드벤처 게임 API",
        version="0.1.0",
    )

    # CORS (★ env var ALLOWED_ORIGINS 우선, default Next.js dev 포트)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(game_router, prefix="/game", tags=["game"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    # ★ Static files (★ Tier 2 D8 W2)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(static_dir)),
            name="static",
        )

        @app.get("/")
        async def root() -> FileResponse:
            return FileResponse(str(static_dir / "index.html"))

    return app


app = create_app()
