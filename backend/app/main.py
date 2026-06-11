from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import router as api_router
from app.core.paths import REPO_ROOT


def create_app() -> FastAPI:
    app = FastAPI(
        title="Prior-Knowledge Driven Few-Shot Workflow",
        version="0.1.0",
    )

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"ok": True}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    frontend_dir = REPO_ROOT / "frontend"
    static_dir = frontend_dir / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

    else:

        @app.get("/", include_in_schema=False)
        def root():
            return {"ok": True, "hint": "frontend/static not found"}

    return app


app = create_app()
