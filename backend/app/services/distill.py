from __future__ import annotations

from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, RandomizedSearchCV, cross_val_predict
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from app.core.session_store import SessionStore
from app.utils.plots import save_metric_panels
from app.services.modeling import adapt_param_space, model_spaces
from app.utils.metrics import regression_metrics
from app.utils.seed import set_global_seed


def _load_bundle(store: SessionStore, session_id: str, name: str):
    p = store.artifact_path(session_id, name)
    if not p.exists():
        raise FileNotFoundError(f"missing artifact: {name}")
    return joblib.load(p)

class TransferMLPRegressor:
    """
    Minimal, picklable transfer-learning regressor:
    - Standardize features (scaler fitted on prior+finetune train)
    - MLP pretrain on prior
    - MLP finetune on exp/aug
    """

    def __init__(self, seed: int):
        self.seed = int(seed)
        self.scaler = StandardScaler()
        self.mlp = MLPRegressor(
            hidden_layer_sizes=(64, 64),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            batch_size="auto",
            learning_rate_init=1e-3,
            max_iter=400,
            random_state=self.seed,
            early_stopping=True,
            warm_start=True,
        )

    def fit_transfer(self, prior_X: pd.DataFrame, prior_y: np.ndarray, finetune_X: pd.DataFrame, finetune_y: np.ndarray):
        self.scaler.fit(pd.concat([prior_X, finetune_X], ignore_index=True))
        Xp = self.scaler.transform(prior_X)
        Xt = self.scaler.transform(finetune_X)
        self.mlp.max_iter = 400
        self.mlp.fit(Xp, np.asarray(prior_y).ravel())
        self.mlp.max_iter = 800
        self.mlp.fit(Xt, np.asarray(finetune_y).ravel())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.mlp.predict(self.scaler.transform(X))


def _transfer_mlp_cv(
    prior_X: pd.DataFrame,
    prior_y: np.ndarray,
    exp_X: pd.DataFrame,
    exp_y: np.ndarray,
    seed: int,
    cv,
):
    y_pred = np.zeros(len(exp_X), dtype=float)
    exp_y = np.asarray(exp_y).ravel()

    for train_idx, val_idx in cv.split(exp_X):
        model = TransferMLPRegressor(seed=seed)
        model.fit_transfer(prior_X, prior_y, exp_X.iloc[train_idx], exp_y[train_idx])
        y_pred[val_idx[0]] = float(model.predict(exp_X.iloc[val_idx])[0])

    return y_pred, regression_metrics(exp_y, y_pred)


def train_final_model(
    session_id: str,
    store: SessionStore,
    prior_df: pd.DataFrame,
    exp_df: pd.DataFrame,
    aug_df: pd.DataFrame,
    features: list[str],
    target: str,
    seed: int,
    alpha: float,
    method: str,
    teacher_model_name: str | None,
    base_model_name: str | None,
) -> dict[str, Any]:
    set_global_seed(seed)
    teacher_bundle = _load_bundle(store, session_id, "teacher_model.joblib")
    teacher = teacher_bundle["model"]
    teacher_feats: list[str] = teacher_bundle["features"]
    cv = KFold(n_splits=max(2, min(5, len(exp_df))), shuffle=True, random_state=seed)

    # build training set: exp + (filtered GAN if provided)
    train_df = exp_df.copy()
    if len(aug_df) > 0:
        train_df = pd.concat([train_df, aug_df], ignore_index=True)

    missing_train = [c for c in features + [target] if c not in train_df.columns]
    if missing_train:
        raise ValueError(f"Exp/aug dataset missing columns: {missing_train}")
    X = train_df[features].copy()
    y = train_df[target].copy()

    # teacher predictions computed on aligned features (fallback to intersection)
    t_feats = [c for c in teacher_feats if c in train_df.columns]
    if len(t_feats) != len(teacher_feats):
        missing_teacher = [c for c in teacher_feats if c not in train_df.columns]
        raise ValueError(f"Teacher model requires missing columns in ExpData: {missing_teacher}")
    teacher_pred = teacher.predict(train_df[t_feats].values)

    # build features/labels for distillation (teacher -> student)
    if method == "teacher_as_feature":
        X2 = X.copy()
        X2["teacher_pred"] = teacher_pred
        X_used = X2
        y_used = y
    elif method == "soft_label":
        # soft-label: y' = (1-a)*y + a*t
        a = float(alpha)
        y_used = (1 - a) * y.values + a * teacher_pred
        X_used = X

    elif method == "both":
        X2 = X.copy()
        X2["teacher_pred"] = teacher_pred
        a = float(alpha)
        y_used = (1 - a) * y.values + a * teacher_pred
        X_used = X2
    else:
       raise ValueError(f"Unknown method: {method}")

    spaces = model_spaces(seed)
    # prefer previously selected base model if available
    order = [base_model_name] if base_model_name in spaces else []
    order += [k for k in spaces.keys() if k not in order]

    rows = []
    best = None
    best_est = None
    best_name = None
    best_params = None

    # transfer learning candidate: pretrain on prior, finetune on exp/aug (only if prior contains needed columns)
    transfer_cols = list(X_used.columns)
    can_transfer = all((c in prior_df.columns) for c in transfer_cols if c != "teacher_pred") and (target in prior_df.columns)
    if can_transfer:
        prior_X = prior_df[[c for c in transfer_cols if c != "teacher_pred"]].copy()
        if "teacher_pred" in transfer_cols:
            prior_teacher = teacher.predict(prior_df[t_feats].values)
            prior_X["teacher_pred"] = prior_teacher
        if method == "teacher_as_feature":
            prior_y = prior_df[target].values
        else:
            a = float(alpha)
            prior_y = (1 - a) * prior_df[target].values + a * teacher.predict(prior_df[t_feats].values)

        exp_X = X_used.reset_index(drop=True)
        exp_y = np.asarray(y_used).ravel()
        try:
            _, m_tl = _transfer_mlp_cv(prior_X, prior_y, exp_X, exp_y, seed, cv)
            row = {"model": "MLP_TL", **m_tl, "params": {"pretrain": "prior", "finetune": "exp_cv"}}
            rows.append(row)
            if best is None or row["r2"] > best["r2"]:
                best = row
                best_name = "MLP_TL"
                best_params = row["params"]
        except Exception:
            pass

    for name in order:
        model, space = spaces[name]
        if space:
            space = adapt_param_space(space, n_features=X_used.shape[1])
            search = RandomizedSearchCV(
                model,
                space,
                n_iter=min(8, 30),
                scoring="r2",
                cv=cv,
                random_state=seed,
                n_jobs=1,
            )
            search.fit(X_used, y_used)
            est = search.best_estimator_
            params = search.best_params_
        else:
            est = model
            est.fit(X_used, y_used)
            params = {}

        y_pred = cross_val_predict(est, X_used, y_used, cv=cv, n_jobs=1)
        m = regression_metrics(y_used, y_pred)
        row = {"model": name, **m, "params": params}
        rows.append(row)
        if best is None or m["r2"] > best["r2"]:
            best = row
            best_name = name
            best_params = params

    if best_name == "MLP_TL":
        if not can_transfer:
            raise ValueError("MLP_TL selected but prior dataset lacks required columns")
        # train final TL model on full data
        final_tl = TransferMLPRegressor(seed=seed).fit_transfer(prior_X, prior_y, X_used, np.asarray(y_used).ravel())
        best_est = final_tl
    else:
        # fit best classical model on full data
        best_est = spaces[best_name][0]
        space = spaces[best_name][1]
        if space:
            space = adapt_param_space(space, n_features=X_used.shape[1])
            search = RandomizedSearchCV(
                best_est,
                space,
                n_iter=min(8, 30),
                scoring="r2",
                cv=cv,
                random_state=seed,
                n_jobs=1,
            )
            search.fit(X_used, y_used)
            best_est = search.best_estimator_
            best_params = search.best_params_
        else:
            best_est.fit(X_used, y_used)

    model_path = store.artifact_path(session_id, "final_model.joblib")
    joblib.dump(
        {
            "model": best_est,
            "model_name": best_name,
            "features": list(X_used.columns),
            "target": target,
            "method": method,
            "alpha": float(alpha),
            "teacher_model_name": teacher_model_name,
            "base_model_name": base_model_name,
            "train_rows": int(len(train_df)),
            "best_params": best_params,
        },
        model_path,
    )

    table_df = pd.DataFrame(rows).sort_values(["r2", "rmse"], ascending=[False, True])
    table_csv = store.artifact_path(session_id, "step8_final_compare.csv")
    table_df.to_csv(table_csv, index=False, encoding="utf-8-sig")
    table_png = store.artifact_path(session_id, "step8_final_compare.png")
    save_metric_panels(
        table_png,
        table_df.assign(label=table_df["model"]),
        label_col="label",
        metric_cols=["r2", "rmse"],
        title="Final Model Comparison",
        top_n=min(12, len(table_df)),
        sort_by="r2",
    )

    store.append_log(session_id, f"[step8] final={best_name} r2={best['r2']:.4f} method={method} alpha={alpha}")
    return {
        "final_model": best_name,
        "best_model": best_name,
        "best_row": best,
        "final_model_artifact": model_path.name,
        "compare_csv_artifact": table_csv.name,
        "compare_png_artifact": table_png.name,
        "compare_table": table_df.to_dict(orient="records"),
        "best_metrics": {k: best[k] for k in ("r2", "rmse", "mae")} if best else None,
        "training_rows": int(len(train_df)),
        "used_features": list(X_used.columns),
    }
