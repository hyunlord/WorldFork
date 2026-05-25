"""FastAPI app (★ Tier 2 D7 게이트 3 W1 + D8 W2 정적 HTML).

★ 단순 골격:
  - /game/start
  - /game/turn
  - /game/state
  - / + /static/* (★ D8 정적 chat UI)
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from service.api.admin_router import router as admin_router
from service.api.game_routes import router as game_router
from service.api.v2_freeform_router import router as v2_freeform_router
from service.api.v2_session_router import router as v2_session_router
from service.api.v2_state_router import router as v2_state_router
from service.canon.context import (
    clear_canon_facts,
    clear_entity_index,
    clear_item_registry,
    clear_spawn_table,
    set_canon_facts,
    set_entity_index,
    set_item_registry,
    set_spawn_table,
)
from service.canon.entity_index import EntityIndex
from service.canon.items import ItemRegistry
from service.canon.loader import load_canon_facts
from service.canon.spawn import SpawnTable
from service.sim.session_manager import get_session_manager


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    get_session_manager()  # startup: SQLite DB 초기화 (.local/worldfork.db)
    facts = load_canon_facts()
    set_canon_facts(facts)
    set_entity_index(EntityIndex(facts))
    set_spawn_table(SpawnTable(facts))
    item_registry = ItemRegistry(facts)
    set_item_registry(item_registry)
    print(f"[startup] ItemRegistry loaded: {item_registry.size()} items")
    yield
    clear_entity_index()
    clear_spawn_table()
    clear_item_registry()
    clear_canon_facts()


def _parse_cors_origins() -> list[str]:
    """CORS allowed origins (★ env var 우선, default = dev 포트들).

    환경변수 ALLOWED_ORIGINS (콤마 구분):
      ALLOWED_ORIGINS="http://localhost:4000,http://100.70.109.50:4000"

    기본값: localhost/127.0.0.1 의 3000 + 4000 (Next.js dev) +
    DGX Spark Tailscale IP 4000 (★ 본인 Mac 본격 manual playthrough access).
    """
    env_value = os.environ.get("ALLOWED_ORIGINS", "").strip()
    if env_value:
        return [origin.strip() for origin in env_value.split(",") if origin.strip()]
    return [
        "http://localhost:3000",
        "http://localhost:4000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4000",
        # ★ DGX Spark Tailscale IP — Mac browser 본격 dev access
        "http://100.70.109.50:3000",
        "http://100.70.109.50:4000",
    ]


def create_app() -> FastAPI:
    """FastAPI app 생성."""
    app = FastAPI(
        title="WorldFork API",
        description="한국어 텍스트 어드벤처 게임 API",
        version="0.1.0",
        lifespan=_lifespan,
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
    # ★ Phase 7a: Tier 2 state API (★ frontend 통합 enabler)
    app.include_router(v2_state_router)
    # ★ Phase D: 자연어 인터프리터 (★ intent + free-form fallback)
    app.include_router(v2_freeform_router)
    # ★ Phase D step 4: 세션 관리 endpoints
    app.include_router(v2_session_router)
    # ★ audit-step4-2: runtime canon reload
    app.include_router(admin_router)

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
