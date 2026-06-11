from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.inspection import PartialDependenceDisplay
import os

from app.core.paths import get_mplconfig_dir

os.environ.setdefault("MPLCONFIGDIR", str(get_mplconfig_dir()))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.core.session_store import SessionStore
from app.services.modeling import adapt_param_space, model_spaces
from app.utils.plots import save_metric_panels
from app.utils.seed import set_global_seed
from app.utils.metrics import regression_metrics

from sklearn.model_selection import KFold, cross_val_predict

import joblib


def train_teacher_and_pdp(
    session_id: str,
    store: SessionStore,
    df: pd.DataFrame,
    target: str,
    features: list[str],
    seed: int,
    cv_folds: int,
    n_iter: int,
) -> dict[str, Any]:
    seed = seed % 2147483647
    set_global_seed(seed)
    spaces = model_spaces(seed)
    missing_x = [c for c in features if c not in df.columns]
    if missing_x:
        raise ValueError(f"Prior dataset missing features: {missing_x}")
    if target not in df.columns:
        raise ValueError(f"Prior dataset missing target: {target}")
    X = df[features].copy()
    # avoid sklearn PDP integer warnings in newer versions
    for c in X.columns:
        if pd.api.types.is_numeric_dtype(X[c]):
            X[c] = X[c].astype(float)
    y = df[target].copy()

    # choose best teacher by KFold CV (more stable than LOOCV on large prior set)
    cv = KFold(n_splits=max(2, int(cv_folds)), shuffle=True, random_state=seed)
    best = None
    best_est = None
    best_name = None
    best_params = None

    from sklearn.model_selection import RandomizedSearchCV

    rows = []
    for name, (model, space) in spaces.items():
        if space:
            space = adapt_param_space(space, n_features=X.shape[1])
            search = RandomizedSearchCV(
                model,
                space,
                n_iter=min(int(n_iter), 40),
                scoring="r2",
                cv=cv,
                random_state=seed,
                n_jobs=1,
            )
            search.fit(X, y)
            est = search.best_estimator_
            params = search.best_params_
        else:
            est = model
            est.fit(X, y)
            params = {}
        y_pred = cross_val_predict(est, X, y, cv=cv, n_jobs=1)
        m = regression_metrics(y, y_pred)
        row = {"model": name, "best_params": params, **m}
        rows.append(row)
        if best is None or m["r2"] > best["r2"]:
            best = row
            best_est = est
            best_name = name
            best_params = params

    # fit best on full data
    best_est.fit(X, y)
    model_path = store.artifact_path(session_id, "teacher_model.joblib")
    joblib.dump(
        {"model_name": best_name, "model": best_est, "features": features, "target": target, "params": best_params},
        model_path,
    )

    # partial dependence plots (top 3 features by absolute correlation with target)
    numeric_X = X.select_dtypes(include="number")
    corr = numeric_X.apply(lambda c: c.corr(y), axis=0).abs().sort_values(ascending=False)
    top_feats = [f for f in corr.index.tolist() if f in features][: min(3, len(features))]
    pdp_path = store.artifact_path(session_id, "teacher_pdp.png")
    plt.figure(figsize=(9, 3), dpi=160)
    try:
        PartialDependenceDisplay.from_estimator(best_est, X, top_feats)
        plt.tight_layout()
        plt.savefig(pdp_path, bbox_inches="tight")
    finally:
        plt.close()

    table_df = pd.DataFrame(rows).sort_values(["r2", "rmse"], ascending=[False, True])
    table_csv = store.artifact_path(session_id, "step3_teacher_compare.csv")
    table_df.to_csv(table_csv, index=False, encoding="utf-8-sig")
    table_png = store.artifact_path(session_id, "step3_teacher_compare.png")
    save_metric_panels(
        table_png,
        table_df.assign(label=table_df["model"]),
        label_col="label",
        metric_cols=["r2", "rmse"],
        title="Teacher Model Comparison",
        top_n=min(10, len(table_df)),
        sort_by="r2",
    )

    store.append_log(session_id, f"[step3] teacher={best_name} r2={best['r2']:.4f}")
    return {
        "best_model": best_name,
        "best_row": {"model": best_name, **({k: best[k] for k in ("r2", "rmse", "mae")} if best else {})},
        "best_params": best_params,
        "metrics": {k: best[k] for k in ("r2", "rmse", "mae")} if best else None,
        "compare_table": table_df.to_dict(orient="records"),
        "compare_csv_artifact": table_csv.name,
        "compare_png_artifact": table_png.name,
        "teacher_model_artifact": model_path.name,
        "pdp_png_artifact": pdp_path.name,
        "pdp_features": top_feats,
        "models_available": list(spaces.keys()),
    }
