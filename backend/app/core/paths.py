from __future__ import annotations

import os
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]  # .../backend
REPO_ROOT = BACKEND_ROOT.parent
RUNS_ROOT = BACKEND_ROOT / "runs"


def get_mplconfig_dir() -> Path:
    path = Path(tempfile.gettempdir()) / f"codex-mplconfig-{os.getpid()}"
    path.mkdir(parents=True, exist_ok=True)
    return path
