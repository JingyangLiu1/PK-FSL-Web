from __future__ import annotations

from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.core.session_store import SessionStore
from app.utils.plots import save_histogram
from app.utils.seed import set_global_seed


def _load_teacher(store: SessionStore, session_id: str):
    p = store.artifact_path(session_id, "teacher_model.joblib")
    if not p.exists():
        raise FileNotFoundError("teacher model not found; run step3 first")
    bundle = joblib.load(p)
    return bundle


def screen_gan_data(
    session_id: str,
    store: SessionStore,
    exp_df: pd.DataFrame,
    gan_df: pd.DataFrame,
    features: list[str],
    target: str,
    seed: int,
    pred_abs_tol: float,
    max_keep: int,
) -> dict[str, Any]:
    set_global_seed(seed)
    bundle = _load_teacher(store, session_id)
    teacher = bundle["model"]
    teacher_feats = bundle["features"]

    # range plausibility: within exp min/max (expanded by small tolerance)
    exp_stats = exp_df[features].describe().T
    mins = exp_stats["min"]
    maxs = exp_stats["max"]
    span = (maxs - mins).replace(0, 1.0)
    low = mins - 0.05 * span
    high = maxs + 0.05 * span

    gan = gan_df.copy()
    # ensure columns present
    missing_cols = [c for c in features + [target] if c not in gan.columns]
    if missing_cols:
        raise ValueError(f"GAN data missing columns: {missing_cols}")

    mask = np.ones(len(gan), dtype=bool)
    for c in features:
        mask &= gan[c].between(low[c], high[c], inclusive="both").values

    gan_ranged = gan.loc[mask].copy()
    store.append_log(session_id, f"[step7] ranged_keep={len(gan_ranged)}/{len(gan)}")
    if len(gan_ranged) == 0:
        raise ValueError("no GAN rows survived range screening; relax tolerance or re-train GAN")

    # prediction plausibility: generated target close to teacher prediction
    # (teacher may be trained on base features only; align)
    X_teacher = gan_ranged[teacher_feats].values
    y_hat = teacher.predict(X_teacher)
    abs_err = np.abs(gan_ranged[target].values - y_hat)
    keep2 = abs_err <= float(pred_abs_tol)
    gan_final = gan_ranged.loc[keep2].copy()
    gan_final["teacher_pred"] = y_hat[keep2]
    gan_final["abs_err_to_teacher"] = abs_err[keep2]

    if len(gan_final) == 0:
        raise ValueError("no GAN rows survived prediction screening; increase pred_abs_tol")

    # downsample to max_keep
    if len(gan_final) > int(max_keep):
        gan_final = gan_final.sample(n=int(max_keep), random_state=seed).reset_index(drop=True)

    store.write_df(session_id, "gan_filtered", gan_final)
    out_csv = store.artifact_path(session_id, "gan_filtered.csv")
    gan_final.to_csv(out_csv, index=False, encoding="utf-8-sig")

    hist_png = store.artifact_path(session_id, "step7_abs_err_hist.png")
    save_histogram(
        hist_png,
        gan_final["abs_err_to_teacher"].values,
        title="Filtered GAN Absolute Error Distribution",
        xlabel="Abs error to teacher",
    )

    store.append_log(session_id, f"[step7] keep={len(gan_final)} tol={pred_abs_tol}")
    return {
        "rows_kept": int(len(gan_final)),
        "kept_rows": int(len(gan_final)),
        "csv_artifact": out_csv.name,
        "png_artifact": hist_png.name,
        "preview": gan_final.head(20).to_dict(orient="records"),
        "stats": {
            "abs_err_mean": float(np.mean(gan_final["abs_err_to_teacher"].values)),
            "abs_err_p95": float(np.quantile(gan_final["abs_err_to_teacher"].values, 0.95)),
        },
    }
