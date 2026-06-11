from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, LeaveOneOut, RandomizedSearchCV, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR

from app.core.session_store import SessionStore
from app.utils.plots import save_metric_panels
from app.utils.metrics import regression_metrics
from app.utils.seed import set_global_seed


def _maybe_xgb():
    try:
        from xgboost import XGBRegressor  # type: ignore
        try:
            from sklearn.utils._tags import get_tags  # type: ignore

            get_tags(XGBRegressor())
        except Exception:
            return None
        return XGBRegressor
    except Exception:
        return None


def model_spaces(seed: int) -> dict[str, tuple[BaseEstimator, dict[str, Any]]]:
    xgb_cls = _maybe_xgb()

    spaces: dict[str, tuple[BaseEstimator, dict[str, Any]]] = {}

    # Poly (degree fixed 2 by reference doc; keep as deterministic baseline)
    poly_model = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("lr", LinearRegression()),
        ]
    )
    spaces["Poly"] = (poly_model, {})

    spaces["SVR"] = (
        Pipeline(steps=[("scale", StandardScaler()), ("svr", SVR())]),
        {
            "svr__C": np.array([0.1, 1.0, 10.0]),
            "svr__gamma": np.array([0.001, 0.01, 0.1, 1.0]),
            "svr__epsilon": np.array([0.01, 0.05, 0.1, 0.2]),
        },
    )

    spaces["RF"] = (
        RandomForestRegressor(random_state=seed),
        {
            "n_estimators": np.array([50, 100, 200, 300]),
            "min_samples_split": np.array([2, 4, 6, 8]),
            "max_features": np.array([1, 2, 3]),
            "max_depth": np.array([2, 3, 4, 5]),
            "max_leaf_nodes": np.array([4, 8, 12, 16]),
        },
    )

    spaces["GBDT"] = (
        GradientBoostingRegressor(random_state=seed),
        {
            "learning_rate": np.array([0.01, 0.05, 0.1, 0.2]),
            "n_estimators": np.array([50, 100, 200, 300]),
            "min_samples_split": np.array([2, 4, 6, 8]),
            "max_features": np.array([1, 2, 3]),
            "max_depth": np.array([2, 3, 4, 5]),
            "max_leaf_nodes": np.array([4, 8, 12, 16]),
        },
    )

    if xgb_cls is not None:
        spaces["XGB"] = (
            xgb_cls(
                random_state=seed,
                tree_method="hist",
                n_jobs=0,
            ),
            {
                "n_estimators": np.array([50, 100, 200]),
                "max_depth": np.array([2, 3, 4, 5]),
                "learning_rate": np.array([0.01, 0.05, 0.1, 0.2]),
                "gamma": np.array([0.0, 0.1, 0.3]),
                "reg_alpha": np.array([0.0, 0.01, 0.1]),
                "reg_lambda": np.array([0.1, 1.0, 10.0]),
                "min_child_weight": np.array([1, 3, 5]),
                "subsample": np.array([0.7, 0.85, 1.0]),
                "colsample_bytree": np.array([0.7, 0.85, 1.0]),
            },
        )

    return spaces


def _prepare_xy(df: pd.DataFrame, features: list[str], target: str):
    missing_x = [c for c in features if c not in df.columns]
    if missing_x:
        raise ValueError(f"missing features in dataset: {missing_x}")
    if target not in df.columns:
        raise ValueError(f"missing target in dataset: {target}")
    X = df[features].copy()
    y = df[target].copy()
    return X, y


def _fit_search(
    model: BaseEstimator,
    space: dict[str, Any],
    X: pd.DataFrame,
    y: pd.Series,
    seed: int,
    n_iter: int,
    cv,
):
    if not space:
        model.fit(X, y)
        return model, {}
    space = adapt_param_space(space, n_features=X.shape[1])
    search = RandomizedSearchCV(
        estimator=model,
        param_distributions=space,
        n_iter=min(int(n_iter), 50),
        scoring="r2",
        cv=cv,
        random_state=seed,
        n_jobs=1,
    )
    search.fit(X, y)
    return search.best_estimator_, search.best_params_


def evaluate_cv(model: BaseEstimator, X: pd.DataFrame, y: pd.Series, cv) -> dict[str, Any]:
    y_pred = cross_val_predict(model, X, y, cv=cv, n_jobs=1)
    m = regression_metrics(y, y_pred)
    return {"metrics": m, "y_pred": y_pred.tolist()}


def compare_base_models(
    session_id: str,
    store: SessionStore,
    df: pd.DataFrame,
    target: str,
    base_features: list[str],
    aux_features: list[str],
    seed: int,
    n_iter: int,
) -> dict[str, Any]:
    set_global_seed(seed)
    spaces = model_spaces(seed)
    bundle_dir = store.session_dir(session_id) / "artifacts" / "step4_models"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    cv = KFold(n_splits=max(2, min(5, len(df))), shuffle=True, random_state=seed)

    candidates: list[tuple[str, list[str]]] = [("Base", base_features)]
    if aux_features:
        candidates.append(("Base+Aux(All)", base_features + aux_features))
        for a in aux_features:
            candidates.append((f"Base+{a}", base_features + [a]))

    rows: list[dict[str, Any]] = []
    best = None
    best_key = None
    best_features: list[str] = base_features

    for feat_name, feats in candidates:
        X, y = _prepare_xy(df, feats, target)
        for model_name, (model, space) in spaces.items():
            fitted, params = _fit_search(model, space, X, y, seed, n_iter=n_iter, cv=cv)
            ev = evaluate_cv(fitted, X, y, cv=cv)
            safe_feat = re.sub(r"[^A-Za-z0-9_.-]+", "_", feat_name).strip("_") or "features"
            safe_model = re.sub(r"[^A-Za-z0-9_.-]+", "_", model_name).strip("_") or "model"
            bundle_name = f"{safe_feat}__{safe_model}.joblib"
            bundle_path = bundle_dir / bundle_name
            joblib.dump(
                {
                    "model": fitted,
                    "model_name": model_name,
                    "feature_set": feat_name,
                    "features": feats,
                    "target": target,
                    "best_params": params,
                },
                bundle_path,
            )
            row = {
                "feature_set": feat_name,
                "features": feats,
                "model": model_name,
                "best_params": params,
                "bundle_artifact": f"step4_models/{bundle_name}",
                **ev["metrics"],
            }
            rows.append(row)
            if best is None or row["r2"] > best["r2"]:
                best = row
                best_key = (feat_name, model_name)
                best_features = feats

    result_df = pd.DataFrame(rows).sort_values(["r2", "rmse"], ascending=[False, True])
    out_csv = store.artifact_path(session_id, "step4_model_compare.csv")
    result_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    out_png = store.artifact_path(session_id, "step4_model_compare.png")
    save_metric_panels(
        out_png,
        result_df.assign(label=result_df["feature_set"] + " / " + result_df["model"]),
        label_col="label",
        metric_cols=["r2", "rmse"],
        title="Base Model Comparison",
        top_n=min(12, len(result_df)),
        sort_by="r2",
    )

    store.append_log(
        session_id,
        f"[step4] best={best_key} r2={best['r2']:.4f} rmse={best['rmse']:.4f} mae={best['mae']:.4f}",
    )

    return {
        "table": result_df.head(50).to_dict(orient="records"),
        "csv_artifact": out_csv.name,
        "png_artifact": out_png.name,
        "best_model": best["model"] if best else None,
        "best_features": best_features,
        "best_row": best,
        "models_available": list(spaces.keys()),
    }


def adapt_param_space(space: dict[str, Any], n_features: int) -> dict[str, Any]:
    """
    Prevent invalid hyperparameter choices (e.g., max_features > n_features).
    Works for both plain estimators and Pipeline params like 'gbdt__max_features'.
    """
    out: dict[str, Any] = {}
    for k, v in space.items():
        if "max_features" in k:
            try:
                arr = np.array(list(v), dtype=int)
                arr = arr[(arr >= 1) & (arr <= max(1, int(n_features)))]
                out[k] = arr if len(arr) > 0 else np.array([max(1, int(n_features))], dtype=int)
                continue
            except Exception:
                pass
        out[k] = v
    return out
