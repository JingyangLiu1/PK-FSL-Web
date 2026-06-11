from __future__ import annotations

from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.core.session_store import SessionStore
from app.utils.plots import save_simple_scatter
from app.utils.seed import set_global_seed


def _pareto_front(points: np.ndarray) -> np.ndarray:
    """
    points: shape (n, m) for minimization objectives.
    return boolean mask of non-dominated points.
    """
    n = points.shape[0]
    is_efficient = np.ones(n, dtype=bool)
    for i in range(n):
        if not is_efficient[i]:
            continue
        i_dominates_j = np.all(points[i] <= points, axis=1) & np.any(points[i] < points, axis=1)
        is_efficient[i_dominates_j] = False
    return is_efficient


def _load_final(store: SessionStore, session_id: str):
    p = store.artifact_path(session_id, "final_model.joblib")
    if not p.exists():
        raise FileNotFoundError("final model not found; run step8 first")
    return joblib.load(p)

import numpy as np
def safe_calculate_cost(df_features: pd.DataFrame, formula: str) -> np.ndarray:
    """安全执行用户自定义成本公式"""
    if not formula.strip():
        return np.sum(np.abs(df_features.values), axis=1)
    
    local_dict = {}
    local_dict.update(np.__dict__)
    for col in df_features.columns:
        local_dict[col] = df_features[col].values
    
    try:
        cost = eval(formula, {"__builtins__": None}, local_dict)
        return np.array(cost, dtype=np.float32)
    except Exception as e:
        print(f"成本公式错误: {e}，使用默认L1成本")
        return np.sum(np.abs(df_features.values), axis=1)

def run_multiobjective_optimization(
    session_id: str,
    store: SessionStore,
    features: list[str],
    target: str,
    seed: int,
    n_samples: int,
    objective_mode: str,
    cost_formula: str = "",
) -> dict[str, Any]:
    set_global_seed(seed)
    final_bundle = _load_final(store, session_id)
    model = final_bundle["model"]
    model_feats = final_bundle["features"]
    needs_teacher_pred = "teacher_pred" in model_feats

    teacher = None
    teacher_feats = None
    if needs_teacher_pred:
        tpath = store.artifact_path(session_id, "teacher_model.joblib")
        if not tpath.exists():
            raise FileNotFoundError("teacher_model.joblib not found (required for teacher_pred inference)")
        tb = joblib.load(tpath)
        teacher = tb["model"]
        teacher_feats = tb["features"]

    # bounds inferred from ExpData (or Prior if missing)
    try:
        exp = store.read_df(session_id, "exp")
        ref = exp
    except Exception:
        ref = store.read_df(session_id, "prior")
    ref_feats = [c for c in model_feats if c != "teacher_pred" and c in ref.columns]
    stats = ref[ref_feats].describe().T
    low = stats["min"].values
    high = stats["max"].values
    span = np.where(high - low == 0, 1.0, high - low)
    low = low - 0.05 * span
    high = high + 0.05 * span

    # random sampling
    rng = np.random.default_rng(seed)
    X = rng.uniform(low=low, high=high, size=(int(n_samples), len(ref_feats)))
    X_raw = pd.DataFrame(X, columns=ref_feats)

    if needs_teacher_pred:
        assert teacher is not None and teacher_feats is not None
        missing = [c for c in teacher_feats if c not in X_raw.columns]
        if missing:
            raise ValueError(f"Cannot compute teacher_pred: missing teacher features in decision vars: {missing}")
        X_model = X_raw.copy()
        X_model["teacher_pred"] = teacher.predict(X_model[teacher_feats].values)
        X_model = X_model[model_feats]
    else:
        X_model = X_raw[model_feats]

    y_pred = model.predict(X_model)

    # objective definitions (minimization)
    if objective_mode == "maximize_target_minimize_cost":
        # placeholder cost: L1 norm of decision vars (user can later replace with domain cost function)
        cost = safe_calculate_cost(X_raw, cost_formula)
        obj = np.column_stack([-y_pred, cost])
        obj_labels = ["-pred(target)", "custom_cost"]
    else:
        # maximize target, minimize squared distance to center (safer)
        center = (low + high) / 2.0
        l2 = np.sum((X - center) ** 2, axis=1)
        obj = np.column_stack([-y_pred, l2])
        obj_labels = ["-pred(target)", "dist2(center)"]

    mask = _pareto_front(obj)
    pareto_X = X[mask]
    pareto_y = y_pred[mask]
    pareto_obj = obj[mask]

    df_all = pd.DataFrame(X, columns=ref_feats)
    df_all["pred"] = y_pred
    df_all[obj_labels[1]] = obj[:, 1]
    df_all["is_pareto"] = mask

    df_p = pd.DataFrame(pareto_X, columns=ref_feats)
    df_p["pred"] = pareto_y
    df_p[obj_labels[1]] = pareto_obj[:, 1]

    all_csv = store.artifact_path(session_id, "step9_opt_all.csv")
    pareto_csv = store.artifact_path(session_id, "step9_opt_pareto.csv")
    df_all.to_csv(all_csv, index=False, encoding="utf-8-sig")
    df_p.to_csv(pareto_csv, index=False, encoding="utf-8-sig")

    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.scatter(df_all[obj_labels[1]], df_all["pred"], 
               c="lightgray", alpha=0.6, s=20, label="All Samples")

    pareto_df = df_all[df_all["is_pareto"] == True].sort_values(by=obj_labels[1])
    ax.scatter(pareto_df[obj_labels[1]], pareto_df["pred"], 
           c="red", s=50, edgecolor="darkred", label="Pareto Front")

    ax.plot(pareto_df[obj_labels[1]], pareto_df["pred"], 
        "r--", linewidth=2, alpha=0.8)

    ax.set_title("Pareto Front Optimization", fontsize=14, fontweight='bold')
    ax.set_xlabel(obj_labels[1], fontsize=12)
    ax.set_ylabel(f"Predicted {target}", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    fig_path = store.artifact_path(session_id, "step9_pareto.png")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close()

    store.append_log(session_id, f"[step9] samples={n_samples} pareto={len(df_p)} mode={objective_mode}")
    return {
        "n_samples": int(n_samples),
        "pareto_rows": int(len(df_p)),
        "pareto_preview": df_p.sort_values(obj_labels[1]).head(30).to_dict(orient="records"),
        "all_csv_artifact": all_csv.name,
        "pareto_csv_artifact": pareto_csv.name,
        "pareto_png_artifact": fig_path.name,
        "decision_features": ref_feats,
        "objectives": obj_labels,
    }
