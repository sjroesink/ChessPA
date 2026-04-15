from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analysis.engine_pool import build_default_pool, configure_pool
from app.api.router import router as api_router
from app.api.ws import router as ws_router
from app.auth.router import router as auth_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = build_default_pool()
    try:
        await pool.start()
        configure_pool(pool)
        yield
    finally:
        await pool.stop()
        configure_pool(None)


def create_app() -> FastAPI:
    app = FastAPI(title="ChessPA", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(api_router)
    app.include_router(ws_router)

    return app


app = create_app()
