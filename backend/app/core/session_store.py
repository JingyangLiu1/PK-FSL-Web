from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.paths import RUNS_ROOT
from app.core.state import SessionState, load_state, save_state


class SessionStore:
    def __init__(self, runs_root: Path | None = None):
        self.runs_root = runs_root or RUNS_ROOT
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def create(self) -> SessionState:
        session_id = uuid.uuid4().hex
        session_dir = self.session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        (session_dir / "data").mkdir(parents=True, exist_ok=True)
        (session_dir / "logs").mkdir(parents=True, exist_ok=True)
        state = SessionState(session_id=session_id)
        save_state(self.state_path(session_id), state)
        return state

    def session_dir(self, session_id: str) -> Path:
        return self.runs_root / session_id

    def state_path(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "state.json"

    def get(self, session_id: str) -> SessionState:
        path = self.state_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"session not found: {session_id}")
        return load_state(path)

    def put(self, state: SessionState) -> None:
        state.touch()
        save_state(self.state_path(state.session_id), state)

    def write_df(self, session_id: str, name: str, df: pd.DataFrame) -> Path:
        path = self.session_dir(session_id) / "data" / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return path

    def read_df(self, session_id: str, name: str) -> pd.DataFrame:
        path = self.session_dir(session_id) / "data" / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"missing dataset: {name}")
        return pd.read_csv(path, encoding="utf-8-sig")

    def artifact_path(self, session_id: str, filename: str) -> Path:
        path = self.session_dir(session_id) / "artifacts" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def log_path(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "logs" / "run.log"

    def append_log(self, session_id: str, msg: str) -> None:
        p = self.log_path(session_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text((p.read_text(encoding="utf-8") if p.exists() else "") + msg + "\n", encoding="utf-8")

    def read_log_tail(self, session_id: str, n_lines: int = 200) -> str:
        p = self.log_path(session_id)
        if not p.exists():
            return ""
        lines = p.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[-n_lines:])

