"""FastAPI app (★ Tier 2 D7 게이트 3 W1).

★ 단순 골격:
  - /game/start
  - /game/turn
  - /game/state
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from service.api.game_routes import router as game_router


def create_app() -> FastAPI:
    """FastAPI app 생성."""
    app = FastAPI(
        title="WorldFork API",
        description="한국어 텍스트 어드벤처 게임 API",
        version="0.1.0",
    )

    # CORS (★ 다음 단계 Next.js 위해)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Next.js dev
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(game_router, prefix="/game", tags=["game"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
