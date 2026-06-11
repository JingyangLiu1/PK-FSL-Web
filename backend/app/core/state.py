from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


@dataclass
class DatasetSpec:
    file_name: str | None = None
    sheet_name: str | None = None
    header_row: int = 0
    index_col: int | None = None
    na_strategy: Literal["keep", "drop", "mean", "median"] = "keep"
    outlier_strategy: Literal["keep", "clip_iqr", "drop_iqr"] = "keep"


@dataclass
class FeatureSpec:
    target: str | None = None
    base_features: list[str] = field(default_factory=list)
    aux_features: list[str] = field(default_factory=list)


@dataclass
class ModelSpec:
    best_teacher: str | None = None
    best_base_model: str | None = None
    best_feature_set: list[str] = field(default_factory=list)
    random_seed: int = 42


@dataclass
class GanSpec:
    enabled: bool = True
    epochs: int = 500
    latent_dim: int = 32
    batch_size: int = 32
    n_generate: int = 200


@dataclass
class ScreeningSpec:
    enabled: bool = True
    range_tol: float = 0.05
    pred_abs_tol: float = 0.05
    max_keep: int = 200


@dataclass
class DistillSpec:
    alpha: float = 0.3
    method: Literal["soft_label", "teacher_as_feature"] = "soft_label"


@dataclass
class OptimizeSpec:
    n_samples: int = 3000
    objective_mode: Literal["maximize_target_minimize_l2", "maximize_target_minimize_cost"] = (
        "maximize_target_minimize_l2"
    )


@dataclass
class SessionState:
    session_id: str
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    iteration: int = 1

    prior: DatasetSpec = field(default_factory=DatasetSpec)
    exp: DatasetSpec = field(default_factory=DatasetSpec)

    features: FeatureSpec = field(default_factory=FeatureSpec)
    models: ModelSpec = field(default_factory=ModelSpec)

    gan: GanSpec = field(default_factory=GanSpec)
    screening: ScreeningSpec = field(default_factory=ScreeningSpec)
    distill: DistillSpec = field(default_factory=DistillSpec)
    optimize: OptimizeSpec = field(default_factory=OptimizeSpec)

    notes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self, default=lambda o: o.__dict__, ensure_ascii=False))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SessionState":
        state = cls(session_id=d["session_id"])
        for k, v in d.items():
            if k in ("prior", "exp", "features", "models", "gan", "screening", "distill", "optimize"):
                obj = getattr(state, k)
                for kk, vv in v.items():
                    setattr(obj, kk, vv)
            else:
                setattr(state, k, v)
        return state

    def touch(self) -> None:
        self.updated_at = _now_iso()


def load_state(path: Path) -> SessionState:
    d = json.loads(path.read_text(encoding="utf-8"))
    return SessionState.from_dict(d)


def save_state(path: Path, state: SessionState) -> None:
    path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
