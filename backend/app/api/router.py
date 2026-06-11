from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import sessions, steps

router = APIRouter()
router.include_router(sessions.router, tags=["sessions"])
router.include_router(steps.router, tags=["steps"])

