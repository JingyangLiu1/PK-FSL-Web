from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.session_store import SessionStore

router = APIRouter()
store = SessionStore()


@router.post("/sessions")
def create_session():
    state = store.create()
    return {"session_id": state.session_id, "state": state.to_dict()}


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    try:
        state = store.get(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "state": state.to_dict()}


@router.get("/sessions/{session_id}/logs")
def get_logs(session_id: str, n_lines: int = 200):
    return {"text": store.read_log_tail(session_id, n_lines=n_lines)}

