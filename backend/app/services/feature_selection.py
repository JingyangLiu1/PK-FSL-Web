from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

from app.core.session_store import SessionStore
from app.utils.plots import save_horizontal_bar_chart
from app.utils.seed import set_global_seed


def select_aux_features(
    session_id: str,
    store: SessionStore,
    df: pd.DataFrame,
    target: str,
    candidate_features: list[str],
    seed: int,
    top_k: int = 5,
) -> dict[str, Any]:
    set_global_seed(seed)
    feats = [f for f in candidate_features if f != target]
    X = df[feats].copy()
    y = df[target].copy()
    model = RandomForestRegressor(n_estimators=500, random_state=seed)
    model.fit(X, y)
    imp = permutation_importance(model, X, y, n_repeats=10, random_state=seed, n_jobs=1)
    scores = imp.importances_mean
    order = np.argsort(scores)[::-1]
    rows = [{"feature": feats[i], "importance": float(scores[i])} for i in order]
    selected = [r["feature"] for r in rows[: max(1, int(top_k))]]

    out_csv = store.artifact_path(session_id, "step5_feature_importance.csv")
    pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8-sig")
    out_png = store.artifact_path(session_id, "step5_feature_importance.png")
    save_horizontal_bar_chart(
        out_png,
        labels=[r["feature"] for r in rows[: max(1, min(15, len(rows)))]],
        values=[r["importance"] for r in rows[: max(1, min(15, len(rows)))]],
        title="Aux Feature Importance",
        xlabel="Permutation Importance",
        ylabel="Feature",
    )
    store.append_log(session_id, f"[step5] selected={selected}")
    return {
        "selected_features": selected,
        "ranking": rows[:50],
        "csv_artifact": out_csv.name,
        "png_artifact": out_png.name,
    }
